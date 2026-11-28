"""Builds a publisher's feed: the live adverts whose categories fit the publisher's content."""

from __future__ import annotations

from datetime import date, datetime, timezone

from litfass_server.store import Store

CATEGORIES: dict[str, str] = {
    "news": "📰 News",
    "military": "🎖 Military",
    "politics": "🏛 Politics",
    "gaming": "🎮 Gaming",
    "tech": "💻 Tech",
    "humor": "😂 Humor",
    "community": "💬 Community",
    "education": "📚 Education",
}

KINDS: dict[str, str] = {
    "web": "🌐 Website / Mini App",
    "bot": "🤖 Telegram bot",
    "channel": "📢 Channel / group",
}

PLACEMENTS: dict[str, str] = {
    "rewarded": "🎁 Rewarded",
    "banner": "🪧 Banner",
    "chat": "💬 Chat message",
}

VARIANTS: dict[str, str] = {"card": "Card", "banner": "Banner", "poster": "Poster"}

STYLE_PRESETS: dict[str, dict[str, str]] = {
    "radar": {"background": "#0c3a6b", "color": "#e6f6ff", "accent": "#2ec5ff"},
    "olive": {"background": "#4b5320", "color": "#f4ecd8", "accent": "#e8c547"},
    "night": {"background": "#14161a", "color": "#f5f5f5", "accent": "#e5484d"},
    "paper": {"background": "#f4ecd8", "color": "#1d1d1b", "accent": "#9c2f2f"},
    "alert": {"background": "#ffd60a", "color": "#111111", "accent": "#d00000"},
    "sky": {"background": "#229ed9", "color": "#ffffff", "accent": "#ffffff"},
}


def fits(ad: dict, publisher: dict) -> bool:
    """An advert without categories runs everywhere; a publisher without categories takes every advert."""
    return not ad["categories"] or not publisher["categories"] or bool(set(ad["categories"]) & set(publisher["categories"]))


def is_live(ad: dict, today: date) -> bool:
    return (
        not ad["paused"]
        and ad["weight"] > 0
        and "en" in ad["text"]
        and (not ad["start"] or date.fromisoformat(ad["start"]) <= today)
        and (not ad["end"] or today < date.fromisoformat(ad["end"]))
    )


def public_ad(ad: dict, public_url: str) -> dict:
    """The advert in the litfass feed format (the same one the web and Python packages read)."""
    item: dict = {"id": ad["id"], "url": ad["url"], "weight": ad["weight"], "text": ad["text"]}
    for field in ("emoji", "start", "end"):
        if ad[field]:
            item[field] = ad[field]
    if ad["image_file_id"]:
        item["image"] = f"{public_url}/v1/media/{ad['id']}?v={ad['image_rev']}"
    if ad["placements"]:
        item["placements"] = ad["placements"]
    if ad["categories"]:
        item["categories"] = ad["categories"]
    if ad["style"]:
        item["style"] = ad["style"]
    return item


def build_feed(store: Store, publisher: dict, public_url: str, now: datetime | None = None) -> dict:
    today = (now or datetime.now(timezone.utc)).date()
    ads = [
        public_ad(ad, public_url)
        for ad in store.list_ads()
        if is_live(ad, today)
        and fits(ad, publisher)
        and (ad["paid"] or publisher["allow_free"])
    ]
    return {"version": 1, "ads": ads}
