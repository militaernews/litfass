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

__all__ = ["Ad", "AdText", "FrequencyCap", "PLACEMENTS", "ad_markup", "ad_html", "load_feed", "parse_feed", "pick_ad", "send_ad"]

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
    rng: Callable[[], float] = _random.random,
) -> Ad | None:
    """A weighted random advert for the placement; excluded ones only when nothing else runs."""
    now = now or datetime.now(timezone.utc)
    active = [ad for ad in ads if ad.runs(placement, now)]
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
