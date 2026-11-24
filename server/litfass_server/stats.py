"""Text overviews of the daily totals, for advertisers (per advert) and publishers (per placement)."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from litfass_server.store import Store

BARS = "▁▂▃▄▅▆▇█"


def since(days: int, today: date | None = None) -> str:
    return ((today or date.today()) - timedelta(days=days - 1)).isoformat()


def rate(clicks: int, views: int) -> str:
    return f"{clicks / views * 100:.1f}%" if views else "–"


def summary(events: dict | None) -> str:
    events = events or {"view": 0, "click": 0, "reward": 0}
    return (
        f"👁 {events['view']:,} views · 👆 {events['click']:,} clicks ({rate(events['click'], events['view'])})"
        f" · 🎁 {events['reward']:,} rewarded"
    )


def sparkline(store: Store, days: int, today: date, **scope) -> str:
    per_day = store.totals(since(days, today), by="day", **scope)
    values = [per_day.get((today - timedelta(days=offset)).isoformat(), {}).get("view", 0) for offset in range(days - 1, -1, -1)]
    top = max(values) or 1
    return "".join(BARS[min(len(BARS) - 1, round(value / top * (len(BARS) - 1)))] if value else "·" for value in values)


def overview(store: Store, title: str, names: dict, *, by: str, today: date | None = None, **scope) -> str:
    """The last 7 and 30 days for one scope (an advert, a publisher or everything), broken down by `by`."""
    today = today or date.today()
    week = store.totals(since(7, today), **scope).get(None)
    month = store.totals(since(30, today), **scope).get(None)
    lines = [
        f"📊 <b>{escape(title)}</b>",
        "",
        f"<b>7 days</b>\n{summary(week)}",
        f"<b>30 days</b>\n{summary(month)}",
        f"Views per day, last 14 days: <code>{sparkline(store, 14, today, **scope)}</code>",
    ]
    groups = store.totals(since(30, today), by=by, **scope)
    if groups:
        label = "advert" if by == "ad_id" else "placement"
        lines += ["", f"<b>By {label}, 30 days</b>"]
        ranked = sorted(groups.items(), key=lambda item: item[1]["view"], reverse=True)[:10]
        for key, events in ranked:
            name = names.get(key, f"#{key} (deleted)")
            lines.append(
                f"• {escape(str(name))[:40]}: {events['view']:,} 👁 · {events['click']:,} 👆 ({rate(events['click'], events['view'])})"
                f" · {events['reward']:,} 🎁"
            )
    else:
        lines += ["", "<i>No views yet.</i>"]
    return "\n".join(lines)
