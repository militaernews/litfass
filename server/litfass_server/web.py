"""The HTTP side: feeds for publishers and advert images. No access log and no IP addresses stored."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from aiohttp import web
from telegram.error import TelegramError
from telegram import Bot

from litfass_server.api import handle as handle_ui, verify_init_data
from litfass_server.feed import build_feed
from litfass_server.pricing import CLICK_STARS
from litfass_server.video import serve as serve_video
import hmac

from litfass_server.stats import network_report, publisher_report
from litfass_server.store import EVENTS, Store

logger = logging.getLogger(__name__)

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
# Events one feed key may report per minute; more are dropped, which keeps inflated numbers in check
EVENTS_PER_MINUTE = 600
MAX_BATCH = 50
# Served both at the root and under this prefix, whichever way the reverse proxy forwards
PREFIXES = ("", "/litfass")


def make_app(
    store: Store,
    bot: Bot | None,
    public_url: str,
    stats_token: str = "",
    token: str = "",
    admins: set[int] | None = None,
) -> web.Application:
    images: dict[tuple[str, int], bytes] = {}
    budget: dict[str, list] = defaultdict(lambda: [0.0, 0])

    def allow(key: str, amount: int) -> bool:
        window = budget[key]
        now = time.monotonic()
        if now - window[0] >= 60:
            window[0], window[1] = now, 0
        if window[1] + amount > EVENTS_PER_MINUTE:
            return False
        window[1] += amount
        return True

    async def event(request: web.Request) -> web.Response:
        """`{ ad, event }` or `{ events: [{ ad, event }] }`; sent as text/plain by sendBeacon, so no preflight."""
        publisher = store.publisher_by_key(request.match_info["key"])
        if not publisher or publisher["blocked"]:
            return web.json_response({"error": "unknown feed"}, status=404, headers=CORS)
        try:
            data = json.loads(await request.text())
            items = data["events"] if isinstance(data, dict) and "events" in data else [data]
            items = [(str(item["ad"]), str(item["event"])) for item in items[:MAX_BATCH]]
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": "invalid body"}, status=400, headers=CORS)
        items = [(ad_id, name) for ad_id, name in items if name in EVENTS]
        if not allow(publisher["key"], len(items)):
            return web.json_response({"error": "too many events"}, status=429, headers=CORS)
        day = datetime.now(timezone.utc).date().isoformat()
        known: dict[str, bool] = {}
        counted = 0
        for ad_id, name in items:
            if ad_id not in known:
                known[ad_id] = store.get_ad(ad_id) is not None
            if not known[ad_id]:
                continue
            if name == "click" and not store.charge_click(ad_id, publisher["id"], CLICK_STARS):
                continue
            store.count(day, ad_id, publisher["id"], name)
            counted += 1
        return web.json_response({"counted": counted}, headers=CORS)

    async def feed(request: web.Request) -> web.Response:
        publisher = store.publisher_by_key(request.match_info["key"])
        if not publisher or publisher["blocked"]:
            return web.json_response({"error": "unknown feed"}, status=404, headers=CORS)
        return web.json_response(
            build_feed(store, publisher, public_url),
            headers={**CORS, "Cache-Control": "public, max-age=300"},
            dumps=lambda data: json.dumps(data, ensure_ascii=False),
        )

    async def stats(request: web.Request) -> web.Response:
        """The placement's own statistics; the feed key is the credential."""
        publisher = store.publisher_by_key(request.match_info["key"])
        if not publisher:
            return web.json_response({"error": "unknown feed"}, status=404, headers=CORS)
        return web.json_response(
            publisher_report(store, publisher), headers={**CORS, "Cache-Control": "private, max-age=60"}, dumps=lambda d: json.dumps(d, ensure_ascii=False)
        )

    async def network(request: web.Request) -> web.Response:
        """Network-wide statistics for admin dashboards: `Authorization: Bearer <LITFASS_STATS_TOKEN>`."""
        given = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not stats_token or not hmac.compare_digest(given, stats_token):
            return web.json_response({"error": "unauthorized"}, status=401)
        return web.json_response(network_report(store), headers={"Cache-Control": "no-store"}, dumps=lambda d: json.dumps(d, ensure_ascii=False))

    async def ui(request: web.Request) -> web.Response:
        return await handle_ui(store, admins or set(), token, request)

    async def verify_task(request: web.Request) -> web.Response:
        """Checks a join task with getChatMember before counting the reward."""
        init = verify_init_data(request.headers.get("x-telegram-init-data"), token)
        if init is None:
            return web.json_response({"error": "unauthorized"}, status=401, headers=CORS)
        try:
            data = await request.json()
        except (ValueError, UnicodeDecodeError):
            data = {}
        if not isinstance(data, dict):
            return web.json_response({"error": "invalid body"}, status=400, headers=CORS)
        ad_id = str(data.get("ad", ""))
        publisher = store.publisher_by_key(str(data.get("key", "")))
        ad = store.get_ad(ad_id)
        if not publisher or publisher["blocked"] or not ad or not ad.get("task_chat"):
            return web.json_response({"error": "unknown task"}, status=404, headers=CORS)
        if bot is None:
            return web.json_response({"error": "bot unavailable"}, status=503, headers=CORS)
        try:
            member = await bot.get_chat_member(ad["task_chat"], init["user"]["id"])
        except TelegramError:
            return web.json_response({"error": "bot_not_in_chat"}, status=409, headers=CORS)
        if member.status not in ("member", "administrator", "creator"):
            return web.json_response({"ok": True, "joined": False}, headers=CORS)
        day = datetime.now(timezone.utc).date().isoformat()
        counted = store.mark_task(day, ad_id, init["user"]["id"])
        if counted:
            store.count(day, ad_id, publisher["id"], "reward")
        return web.json_response({"ok": True, "joined": True, "counted": counted}, headers=CORS)

    async def media(request: web.Request) -> web.Response:
        ad = store.get_ad(request.match_info["ad_id"])
        if not ad or not ad["image_file_id"] or bot is None:
            return web.Response(status=404, headers=CORS)
        cache_key = (ad["id"], ad["image_rev"])
        if cache_key not in images:
            file = await bot.get_file(ad["image_file_id"])
            images[cache_key] = bytes(await file.download_as_bytearray())
        return web.Response(
            body=images[cache_key],
            content_type="image/jpeg",
            headers={**CORS, "Cache-Control": "public, max-age=86400"},
        )

    async def options(_: web.Request) -> web.Response:
        return web.Response(status=204, headers=CORS)

    async def health(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    for prefix in PREFIXES:
        app.router.add_get(f"{prefix}/v1/feed/{{key}}", feed)
        app.router.add_get(f"{prefix}/v1/media/{{ad_id}}", media)
        app.router.add_post(f"{prefix}/v1/event/{{key}}", event)
        app.router.add_get(f"{prefix}/v1/stats/{{key}}", stats)
        app.router.add_post(f"{prefix}/v1/task/verify", verify_task)
        app.router.add_get(f"{prefix}/v1/video", serve_video)
        app.router.add_get(f"{prefix}/v1/admin/stats", network)
        app.router.add_post(f"{prefix}/v1/admin/ui", ui)
        app.router.add_route("OPTIONS", f"{prefix}/v1/{{tail:.*}}", options)
        app.router.add_get(f"{prefix}/healthz", health)
    return app
