"""Telegram-authenticated JSON API for the management UI.

Mini App calls carry the raw initData in the X-Telegram-Init-Data header. It is checked
against the bot token (HMAC, as Telegram documents for Mini Apps) and never stored or
logged; only the verified user id reaches the handlers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from datetime import date
from urllib.parse import parse_qsl

from aiohttp import web

from litfass_server.feed import CATEGORIES, PLACEMENTS, VARIANTS
from litfass_server.stats import network_report, publisher_report
from litfass_server.store import Store

# Launch data older than this is refused, so a leaked initData stops working
MAX_AGE = 24 * 3600
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
LANG = re.compile(r"^[a-z]{2}(-[A-Za-z]{2})?$")
MAX_TEXT = {"title": 60, "body": 200, "cta": 30}
EDITABLE = ("url", "emoji", "weight", "start", "end", "paused", "placements", "categories", "style")


def verify_init_data(raw: str | None, token: str, now: int | None = None) -> dict | None:
    """The verified initData (with `user` parsed), or None for a bad or stale signature."""
    if not raw or not token or not isinstance(raw, str):
        return None
    fields = dict(parse_qsl(raw, keep_blank_values=True))
    received = fields.pop("hash", "")
    if len(received) != 64 or any(c not in "0123456789abcdef" for c in received):
        return None
    check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        auth_date = int(fields.get("auth_date", ""))
    except ValueError:
        return None
    if (now if now is not None else int(time.time())) - auth_date > MAX_AGE:
        return None
    try:
        user = json.loads(fields.get("user") or "null")
    except ValueError:
        return None
    if not isinstance(user, dict) or not isinstance(user.get("id"), int) or isinstance(user.get("id"), bool):
        return None
    fields["user"] = user
    return fields


def _error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"ok": False, "error": message}, status=status)


def _parse(data: dict, current: dict | None) -> tuple[dict, dict, str | None]:
    """Validate the editable fields and texts; returns (fields, texts, error)."""
    fields: dict = {}
    for key in EDITABLE:
        if key not in data:
            continue
        value = data[key]
        if key == "url":
            if not isinstance(value, str) or not value.startswith("https://") or " " in value:
                return {}, {}, "url must be an https link"
        elif key == "emoji":
            if value is not None and (not isinstance(value, str) or len(value) > 8):
                return {}, {}, "emoji is too long"
        elif key == "weight":
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                return {}, {}, "weight must be an integer between 0 and 1000"
        elif key in ("start", "end"):
            if value is not None:
                try:
                    value = date.fromisoformat(value).isoformat()
                except (TypeError, ValueError):
                    return {}, {}, f"{key} must be an ISO date"
        elif key == "paused":
            if not isinstance(value, bool):
                return {}, {}, "paused must be a boolean"
        elif key in ("placements", "categories"):
            allowed = PLACEMENTS if key == "placements" else CATEGORIES
            if not isinstance(value, list) or any(item not in allowed for item in value):
                return {}, {}, f"unknown {key}"
        elif key == "style":
            if not isinstance(value, dict):
                return {}, {}, "style must be an object"
            style = {}
            for name, colour in value.items():
                if name == "variant":
                    if colour not in VARIANTS:
                        return {}, {}, "unknown variant"
                elif name in ("background", "color", "accent"):
                    if not isinstance(colour, str) or not HEX.match(colour):
                        return {}, {}, f"{name} must be a #rrggbb colour"
                else:
                    return {}, {}, f"unknown style field: {name}"
                style[name] = colour
            value = {**(current or {}).get("style", {}), **style}
        fields[key] = value

    texts: dict = {}
    if "text" in data:
        if not isinstance(data["text"], dict):
            return {}, {}, "text must be an object"
        for lang, text in data["text"].items():
            if not LANG.match(lang) or not isinstance(text, dict):
                return {}, {}, f"invalid language: {lang}"
            for field in ("title", "body", "cta"):
                value = text.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT[field]:
                    return {}, {}, f"{lang}.{field} is empty or too long"
            texts[lang] = {field: text[field] for field in ("title", "body", "cta")}
    return fields, texts, None


async def handle(store: Store, admins: set[int], token: str, request: web.Request) -> web.Response:
    init = verify_init_data(request.headers.get("x-telegram-init-data"), token)
    if init is None:
        return _error("unauthorized", 401)
    uid = init["user"]["id"]
    admin = uid in admins
    try:
        data = await request.json()
    except (ValueError, UnicodeDecodeError):
        data = {}
    if not isinstance(data, dict):
        return _error("invalid body")

    action = data.get("action")
    if action == "me":
        return web.json_response(
            {
                "ok": True,
                "user": {key: init["user"].get(key) for key in ("id", "first_name", "username")},
                "admin": admin,
            }
        )
    if action == "list_ads":
        ads = store.list_ads() if admin else [ad for ad in store.list_ads() if ad.get("created_by") == uid]
        return web.json_response({"ok": True, "ads": ads})
    if action == "publishers":
        return web.json_response({"ok": True, "publishers": store.publishers(None if admin else uid)})
    if action == "stats":
        if admin:
            return web.json_response({"ok": True, "stats": network_report(store)})
        return web.json_response({"ok": True, "stats": [publisher_report(store, p) for p in store.publishers(uid)]})
    if not admin:
        return _error("forbidden", 403)

    if action == "create_ad":
        fields, texts, error = _parse(data, None)
        if error:
            return _error(error)
        if "url" not in fields or not texts:
            return _error("url and an en text are required")
        ad_id = store.create_ad(fields.pop("url"), uid)
        if fields:
            store.update_ad(ad_id, **fields)
        for lang, text in texts.items():
            store.set_text(ad_id, lang, **text)
        return web.json_response({"ok": True, "id": ad_id})

    ad_id = str(data.get("id", ""))
    ad = store.get_ad(ad_id)
    if not ad:
        return _error("not found", 404)

    if action == "update_ad":
        fields, texts, error = _parse(data, ad)
        if error:
            return _error(error)
        if fields:
            store.update_ad(ad_id, **fields)
        if "text" in data:
            for lang in list(ad["text"]):
                store.delete_text(ad_id, lang)
            for lang, text in texts.items():
                store.set_text(ad_id, lang, **text)
        return web.json_response({"ok": True})
    if action == "delete_ad":
        store.delete_ad(ad_id)
        return web.json_response({"ok": True})
    return _error("unknown action")
