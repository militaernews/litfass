"""Text overviews of the daily totals, for advertisers (per advert) and publishers (per placement)."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from litfass_server.store import Store
from litfass_server.texts import t

BARS = "▁▂▃▄▅▆▇█"


def since(days: int, today: date | None = None) -> str:
    return ((today or date.today()) - timedelta(days=days - 1)).isoformat()


def rate(clicks: int, views: int) -> str:
    return f"{clicks / views * 100:.1f}%" if views else "–"


def summary(events: dict | None, lang: str = "en") -> str:
    events = events or {"view": 0, "click": 0, "reward": 0}
    return (
        f"👁 {events['view']:,} {t(lang, 's_views')} · 👆 {events['click']:,} {t(lang, 's_clicks')}"
        f" ({rate(events['click'], events['view'])}) · 🎁 {events['reward']:,} {t(lang, 's_rewarded')}"
    )


def sparkline(store: Store, days: int, today: date, **scope) -> str:
    per_day = store.totals(since(days, today), by="day", **scope)
    values = [per_day.get((today - timedelta(days=offset)).isoformat(), {}).get("view", 0) for offset in range(days - 1, -1, -1)]
    top = max(values) or 1
    return "".join(BARS[min(len(BARS) - 1, round(value / top * (len(BARS) - 1)))] if value else "·" for value in values)


def publisher_report(store: Store, publisher: dict, today: date | None = None) -> dict:
    """A placement's own numbers as data: totals for 7 and 30 days, every day of the last 30 and the
    adverts it showed. The feed key is the credential, so it only ever covers that placement."""
    today = today or date.today()
    scope = {"publisher_id": publisher["id"]}
    empty = {"view": 0, "click": 0, "reward": 0}
    per_day = store.totals(since(30, today), by="day", **scope)
    per_ad = store.totals(since(30, today), by="ad_id", **scope)
    titles = {}
    for ad_id in per_ad:
        ad = store.get_ad(ad_id)
        text = (ad or {}).get("text", {}).get("en")
        titles[ad_id] = text["title"] if text else None
    return {
        "placement": publisher["name"],
        "totals": {
            "7": store.totals(since(7, today), **scope).get(None, empty),
            "30": store.totals(since(30, today), **scope).get(None, empty),
        },
        "days": [
            {"day": day, **per_day.get(day, empty)}
            for day in ((today - timedelta(days=offset)).isoformat() for offset in range(29, -1, -1))
        ],
        "ads": sorted(
            ({"id": ad_id, "title": titles[ad_id], **events} for ad_id, events in per_ad.items()),
            key=lambda item: item["view"],
            reverse=True,
        ),
    }


def network_report(store: Store, today: date | None = None) -> dict:
    """Every advert and placement with their 30-day totals, and the network's days; for admins."""
    today = today or date.today()
    empty = {"view": 0, "click": 0, "reward": 0}
    start = since(30, today)
    per_day = store.totals(start, by="day")
    per_ad = store.totals(start, by="ad_id")
    per_publisher = store.totals(start, by="publisher_id")
    ads = store.list_ads()
    publishers = store.publishers()
    return {
        "totals": {"7": store.totals(since(7, today)).get(None, empty), "30": store.totals(start).get(None, empty)},
        "days": [
            {"day": day, **per_day.get(day, empty)}
            for day in ((today - timedelta(days=offset)).isoformat() for offset in range(29, -1, -1))
        ],
        "ads": [
            {
                "id": ad["id"],
                "title": (ad["text"].get("en") or {}).get("title"),
                "live": not ad["paused"],
                "categories": ad["categories"],
                **per_ad.get(ad["id"], empty),
            }
            for ad in ads
        ],
        "placements": [
            {"id": p["id"], "name": p["name"], "kind": p["kind"], "categories": p["categories"], "blocked": bool(p["blocked"]), **per_publisher.get(p["id"], empty)}
            for p in publishers
        ],
    }


def deep_report(store: Store, days: int = 30, owner_id: int | None = None, today: date | None = None) -> dict:
    """Totals, previous-period comparison, daily series, per-ad and per-placement breakdowns."""
    today = today or date.today()
    empty = {"view": 0, "click": 0, "reward": 0}
    start = since(days, today)
    previous_start = since(days * 2, today)
    previous_end = (today - timedelta(days=days)).isoformat()
    scope_ads = [ad for ad in store.list_ads() if owner_id is None or ad.get("created_by") == owner_id]
    ads = {ad["id"]: ad for ad in scope_ads}
    placements = store.publishers(None if owner_id is None else owner_id)

    ad_ids = [ad["id"] for ad in scope_ads]
    publisher_ids = [p["id"] for p in placements]

    def totals(begin: str, end: str | None = None) -> dict:
        where, params = ["day >= ?"], [begin]
        if end:
            where.append("day < ?")
            params.append(end)
        if owner_id is not None:
            where.append("ad_id IN (%s)" % ",".join("?" for _ in ad_ids) if ad_ids else "1=0")
            params.extend(ad_ids)
            where.append("publisher_id IN (%s)" % ",".join("?" for _ in publisher_ids) if publisher_ids else "1=0")
            params.extend(publisher_ids)
        rows = store.db.execute(
            f"SELECT event, SUM(count) AS n FROM stats WHERE {' AND '.join(where)} GROUP BY event", params
        )
        result = dict(empty)
        for row in rows:
            result[row["event"]] = row["n"]
        return result

    current = totals(start)
    previous = totals(previous_start, previous_end)

    scope = {} if owner_id is None else {"ad_ids": ad_ids, "publisher_ids": publisher_ids}
    per_day = store.totals(start, by="day", **scope)
    series = [
        {"day": (today - timedelta(days=offset)).isoformat(), **per_day.get((today - timedelta(days=offset)).isoformat(), empty)}
        for offset in range(days - 1, -1, -1)
    ]

    per_ad = store.totals(start, by="ad_id", **scope)
    ad_rows = []
    for ad_id, events in sorted(per_ad.items(), key=lambda item: item[1]["view"], reverse=True):
        ad = ads.get(ad_id)
        if ad is None and owner_id is not None:
            continue
        title = (ad or {}).get("text", {}).get("en", {}).get("title") or ad_id
        ad_rows.append(
            {
                "id": ad_id,
                "title": title,
                "views": events["view"],
                "clicks": events["click"],
                "rewards": events["reward"],
                "ctr": round(events["click"] / events["view"] * 100, 1) if events["view"] else 0.0,
            }
        )

    per_publisher = store.totals(start, by="publisher_id", **scope)
    placement_rows = []
    for publisher in placements:
        events = per_publisher.get(publisher["id"], empty)
        placement_rows.append(
            {
                "id": publisher["id"],
                "name": publisher["name"],
                "views": events["view"],
                "clicks": events["click"],
                "rewards": events["reward"],
                "ctr": round(events["click"] / events["view"] * 100, 1) if events["view"] else 0.0,
            }
        )

    def ctr(value: dict) -> float:
        return round(value["click"] / value["view"] * 100, 1) if value["view"] else 0.0

    return {
        "days": days,
        "totals": current,
        "previous": previous,
        "ctr": ctr(current),
        "previousCtr": ctr(previous),
        "series": series,
        "ads": ad_rows,
        "placements": placement_rows,
    }


def overview(store: Store, title: str, names: dict, *, by: str, today: date | None = None, lang: str = "en", **scope) -> str:
    """The last 7 and 30 days for one scope (an advert, a publisher or everything), broken down by `by`."""
    today = today or date.today()
    week = store.totals(since(7, today), **scope).get(None)
    month = store.totals(since(30, today), **scope).get(None)
    lines = [
        f"📊 <b>{escape(title)}</b>",
        "",
        f"<b>{t(lang, 's_7')}</b>\n{summary(week, lang)}",
        f"<b>{t(lang, 's_30')}</b>\n{summary(month, lang)}",
        f"{t(lang, 's_spark')}: <code>{sparkline(store, 14, today, **scope)}</code>",
    ]
    groups = store.totals(since(30, today), by=by, **scope)
    if groups:
        lines += ["", f"<b>{t(lang, 's_by_advert' if by == 'ad_id' else 's_by_placement')}</b>"]
        ranked = sorted(groups.items(), key=lambda item: item[1]["view"], reverse=True)[:10]
        for key, events in ranked:
            name = names.get(key, t(lang, "s_deleted", id=key))
            lines.append(
                f"• {escape(str(name))[:40]}: {events['view']:,} 👁 · {events['click']:,} 👆 ({rate(events['click'], events['view'])})"
                f" · {events['reward']:,} 🎁"
            )
    else:
        lines += ["", t(lang, "s_none")]
    return "\n".join(lines)
