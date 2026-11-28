"""litfass for Telegram bots: the same house-advert feed as the web package, rendered as bot messages.

Nothing here talks to an ad network or tracks anyone. Load a feed, pick an advert for a placement and
send it; `FrequencyCap` keeps chats from seeing adverts too often. python-telegram-bot is only needed
for `send_ad` and `ad_markup`.
"""

from __future__ import annotations

import random as _random
import time as _time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from typing import Any, Callable, Iterable

__all__ = [
    "Ad", "AdText", "FrequencyCap", "PLACEMENTS", "ad_markup", "ad_html", "event_url", "fetch_feed", "load_feed",
    "parse_feed", "pick_ad", "report_events", "send_ad",
]

PLACEMENTS = ("rewarded", "banner", "chat")


@dataclass(frozen=True)
class AdText:
    title: str
    body: str
    cta: str


@dataclass(frozen=True)
class Ad:
    id: str
    url: str
    text: dict[str, AdText]
    placements: tuple[str, ...] | None = None
    weight: float = 1
    start: datetime | None = None
    end: datetime | None = None
    emoji: str | None = None
    image: str | None = None
    video: str | None = None
    video_kind: str | None = None
    task: tuple[str, str] | None = None
    categories: tuple[str, ...] = ()
    style: dict[str, str] = field(default_factory=dict)

    def fits(self, categories: Iterable[str] | None) -> bool:
        """No categories on either side fits everything; otherwise they must share one."""
        wanted = set(categories or ())
        return not self.categories or not wanted or bool(wanted & set(self.categories))

    def localize(self, lang: str | None) -> AdText:
        """Texts in a language such as `de` or `pt-BR`, falling back to the base language and English."""
        if lang:
            base = lang.lower().replace("_", "-").split("-")[0]
            return self.text.get(lang) or self.text.get(base) or self.text["en"]
        return self.text["en"]

    def runs(self, placement: str, now: datetime) -> bool:
        return (
            self.weight > 0
            and (self.placements is None or placement in self.placements)
            and (self.start is None or self.start <= now)
            and (self.end is None or now < self.end)
        )


def _date(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ad(raw: Any) -> Ad | None:
    try:
        if not isinstance(raw, dict) or not raw.get("id") or not str(raw.get("url", "")).startswith("https://"):
            return None
        text = {
            lang: AdText(entry["title"], entry["body"], entry["cta"])
            for lang, entry in (raw.get("text") or {}).items()
            if isinstance(entry, dict) and all(isinstance(entry.get(k), str) and entry[k] for k in ("title", "body", "cta"))
        }
        if "en" not in text:
            return None
        placements = raw.get("placements")
        if placements is not None and (not isinstance(placements, list) or any(p not in PLACEMENTS for p in placements)):
            return None
        weight = raw.get("weight", 1)
        if not isinstance(weight, (int, float)) or weight < 0:
            return None
        return Ad(
            id=str(raw["id"]),
            url=raw["url"],
            text=text,
            placements=tuple(placements) if placements is not None else None,
            weight=weight,
            start=_date(raw.get("start")),
            end=_date(raw.get("end")),
            emoji=raw.get("emoji"),
            image=raw.get("image"),
            video=raw.get("video") if str(raw.get("video", "")).startswith("https://") else None,
            video_kind=raw.get("videoKind") if raw.get("videoKind") in ("video", "gif") else None,
            task=(raw["task"]["type"], raw["task"]["chat"])
            if isinstance(raw.get("task"), dict)
            and raw["task"].get("type") == "join"
            and isinstance(raw["task"].get("chat"), str)
            else None,
            categories=tuple(str(c) for c in raw.get("categories") or ()),
            style={k: v for k, v in (raw.get("style") or {}).items() if isinstance(v, str)},
        )
    except (KeyError, TypeError, ValueError):
        return None


def parse_feed(data: Any) -> list[Ad]:
    """The valid adverts of a feed document; invalid ones are dropped instead of failing as a whole."""
    ads = data.get("ads") if isinstance(data, dict) else None
    return [ad for ad in (_ad(raw) for raw in ads or []) if ad]


def load_feed(path: str) -> list[Ad]:
    import json

    with open(path, encoding="utf-8") as file:
        return parse_feed(json.load(file))


def pick_ad(
    ads: Iterable[Ad],
    placement: str,
    *,
    now: datetime | None = None,
    exclude: Iterable[str] = (),
    categories: Iterable[str] | None = None,
    rng: Callable[[], float] = _random.random,
) -> Ad | None:
    """A weighted random advert for the placement; excluded ones only when nothing else runs.
    `categories` matches bundled feeds to your content; server feeds are matched already."""
    now = now or datetime.now(timezone.utc)
    wanted = list(categories or ())
    active = [ad for ad in ads if ad.runs(placement, now) and ad.fits(wanted)]
    skip = set(exclude)
    pool = [ad for ad in active if ad.id not in skip] or active
    total = sum(ad.weight for ad in pool)
    if not total:
        return None
    roll = rng() * total
    for ad in pool:
        roll -= ad.weight
        if roll < 0:
            return ad
    return pool[-1]


def ad_html(ad: Ad, lang: str | None, label: str = "Anzeige") -> str:
    """The advert as Telegram HTML, marked as an advert (required in Germany, § 6 DDG)."""
    text = ad.localize(lang)
    emoji = f"{ad.emoji} " if ad.emoji else ""
    return f"<i>{escape(label)}</i>\n{emoji}<b>{escape(text.title)}</b>\n{escape(text.body)}"


def ad_markup(ad: Ad, lang: str | None):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup([[InlineKeyboardButton(ad.localize(lang).cta, url=ad.url)]])


async def send_ad(bot, chat_id: int, ad: Ad, lang: str | None = None, label: str = "Anzeige", **kwargs):
    """Sends the advert as a message (with its image as a photo when it has one)."""
    caption = ad_html(ad, lang, label)
    markup = ad_markup(ad, lang)
    if ad.video:
        if ad.video_kind == "video":
            return await bot.send_video(chat_id, ad.video, caption=caption, parse_mode="HTML", reply_markup=markup, **kwargs)
        return await bot.send_animation(chat_id, ad.video, caption=caption, parse_mode="HTML", reply_markup=markup, **kwargs)
    if ad.image:
        return await bot.send_photo(chat_id, ad.image, caption=caption, parse_mode="HTML", reply_markup=markup, **kwargs)
    return await bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True, **kwargs)


@dataclass
class FrequencyCap:
    """At most `max_views` adverts per key (chat or user) within `window` seconds, kept in memory."""

    max_views: int
    window: float
    clock: Callable[[], float] = _time.monotonic
    _views: dict[Any, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def _fresh(self, key: Any) -> deque[float]:
        views = self._views[key]
        now = self.clock()
        while views and now - views[0] >= self.window:
            views.popleft()
        return views

    def remaining(self, key: Any) -> int:
        return max(0, self.max_views - len(self._fresh(key)))

    def record(self, key: Any) -> bool:
        views = self._fresh(key)
        if len(views) >= self.max_views:
            return False
        views.append(self.clock())
        return True


def event_url(feed_url: str) -> str:
    """The event endpoint of a feed URL (`…/v1/feed/<key>` → `…/v1/event/<key>`)."""
    import re

    return re.sub(r"/v1/feed/([^/?#]+).*$", r"/v1/event/\1", feed_url)


def _post(url: str, body: bytes, timeout: float) -> None:
    from urllib.request import Request, urlopen

    with urlopen(Request(url, data=body, headers={"Content-Type": "text/plain"}, method="POST"), timeout=timeout):
        pass


async def report_events(feed_url: str, events: Iterable[tuple[str, str]], timeout: float = 5) -> bool:
    """Reports `(ad_id, "view" | "click" | "reward")` pairs; the server keeps daily totals only.
    Returns False instead of raising when the server cannot be reached."""
    import asyncio
    import json

    batch = [{"ad": ad_id, "event": event} for ad_id, event in events][:50]
    if not batch:
        return True
    try:
        await asyncio.to_thread(_post, event_url(feed_url), json.dumps({"events": batch}).encode(), timeout)
        return True
    except OSError:
        return False


async def fetch_feed(feed_url: str, fallback: list[Ad] | None = None, timeout: float = 5) -> list[Ad]:
    """Loads a feed from a litfass server, or returns `fallback` when that fails."""
    import asyncio
    import json
    from urllib.request import urlopen

    def get() -> bytes:
        with urlopen(feed_url, timeout=timeout) as response:
            return response.read()

    try:
        return parse_feed(json.loads(await asyncio.to_thread(get)))
    except (OSError, ValueError):
        return list(fallback or [])
