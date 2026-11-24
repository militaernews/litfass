from datetime import datetime, timezone

import pytest

from litfass_server.bot import apply_ad_input
from litfass_server.feed import build_feed
from litfass_server.store import Store
from litfass_server.web import make_app

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)
URL = "https://ads.example"


@pytest.fixture
def store():
    return Store()


def live_ad(store: Store, categories=(), **fields) -> str:
    ad_id = store.create_ad("https://t.me/x")
    store.set_text(ad_id, "en", "Title", "Body", "Go")
    store.update_ad(ad_id, **{"paused": 0, "categories": list(categories), **fields})
    return ad_id


def test_feed_matches_categories(store):
    news = live_ad(store, ["news"])
    gaming = live_ad(store, ["gaming"])
    anywhere = live_ad(store)
    publisher = store.create_publisher(1, "Game", "web", ["gaming", "military"])
    ids = [ad["id"] for ad in build_feed(store, publisher, URL, NOW)["ads"]]
    assert ids == [gaming, anywhere]
    everything = store.create_publisher(1, "All", "bot", [])
    assert len(build_feed(store, everything, URL, NOW)["ads"]) == 3
    assert news


def test_feed_skips_paused_untexted_and_scheduled(store):
    live_ad(store, paused=1)
    store.create_ad("https://t.me/no-text")
    live_ad(store, end="2026-05-01")
    live_ad(store, start="2026-07-01")
    keep = live_ad(store, start="2026-05-01", end="2026-06-02", style={"background": "#000000", "variant": "poster"}, emoji="📰")
    store.update_ad(keep, image_file_id="file", image_rev=3)
    ads = build_feed(store, store.create_publisher(1, "P", "web", []), URL, NOW)["ads"]
    assert [ad["id"] for ad in ads] == [keep]
    assert ads[0]["image"] == f"{URL}/v1/media/{keep}?v=3"
    assert ads[0]["style"]["variant"] == "poster"
    assert "placements" not in ads[0]


def test_publisher_key_rotation(store):
    publisher = store.create_publisher(7, "P", "channel", ["news"])
    old = publisher["key"]
    new = store.rotate_key(publisher["id"])
    assert store.publisher_by_key(old) is None
    assert store.publisher_by_key(new)["owner_id"] == 7
    assert store.publishers(7)[0]["categories"] == ["news"]


def test_admin_inputs(store):
    ad_id = store.create_ad("https://t.me/x")
    ad = store.get_ad(ad_id)
    assert apply_ad_input(store, ad, "texts", "de\nTitel\nText\nLos") is None
    assert apply_ad_input(store, ad, "texts", "too\nfew") is not None
    assert apply_ad_input(store, ad, "colors", "#000000 #ffffff #ff0000") is None
    assert apply_ad_input(store, ad, "colors", "red white blue") is not None
    assert apply_ad_input(store, ad, "sched", "2026-12-01 2027-01-07") is None
    assert apply_ad_input(store, ad, "sched", "2027-01-07 2026-12-01") is not None
    assert apply_ad_input(store, ad, "url", "http://insecure") is not None
    ad = store.get_ad(ad_id)
    assert ad["text"]["de"]["cta"] == "Los"
    assert ad["style"] == {"background": "#000000", "color": "#ffffff", "accent": "#ff0000"}
    assert (ad["start"], ad["end"]) == ("2026-12-01", "2027-01-07")
    assert apply_ad_input(store, ad, "texts", "de -") is None
    assert "de" not in store.get_ad(ad_id)["text"]


async def test_http_feed(aiohttp_client, store):
    live_ad(store)
    publisher = store.create_publisher(1, "P", "web", [])
    client = await aiohttp_client(make_app(store, None, URL))
    for prefix in ("", "/litfass"):
        response = await client.get(f"{prefix}/v1/feed/{publisher['key']}")
        assert response.status == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert len((await response.json())["ads"]) == 1
    assert (await client.get("/v1/feed/nope")).status == 404
    store.update_publisher(publisher["id"], blocked=1)
    assert (await client.get(f"/v1/feed/{publisher['key']}")).status == 404


async def test_http_events_count_daily_totals(aiohttp_client, store):
    ad_id = live_ad(store)
    publisher = store.create_publisher(1, "P", "web", [])
    client = await aiohttp_client(make_app(store, None, URL))
    url = f"/v1/event/{publisher['key']}"
    assert (await client.post(url, data='{"ad": "%s", "event": "view"}' % ad_id, headers={"Content-Type": "text/plain"})).status == 200
    body = {"events": [{"ad": ad_id, "event": "view"}, {"ad": ad_id, "event": "click"}, {"ad": "gone", "event": "view"}, {"ad": ad_id, "event": "bogus"}]}
    assert (await (await client.post(url, json=body)).json())["counted"] == 2
    assert (await client.post(url, data="not json")).status == 400
    assert (await client.post("/v1/event/nope", json={"ad": ad_id, "event": "view"})).status == 404
    totals = store.totals("2000-01-01", publisher_id=publisher["id"])[None]
    assert totals == {"view": 2, "click": 1, "reward": 0}


def test_overview_text(store):
    from datetime import date

    from litfass_server.stats import overview

    ad_id = live_ad(store)
    publisher = store.create_publisher(1, "Game", "web", [])
    store.count("2026-06-01", ad_id, publisher["id"], "view", 200)
    store.count("2026-06-01", ad_id, publisher["id"], "click", 10)
    store.count("2026-05-01", ad_id, publisher["id"], "view", 5)
    text = overview(store, "Title", {publisher["id"]: "Game"}, by="publisher_id", ad_id=ad_id, today=date(2026, 6, 1))
    assert "200 views · 👆 10 clicks (5.0%)" in text
    assert "• Game: 200 👁 · 10 👆 (5.0%) · 0 🎁" in text
    assert text.count("█") == 1


async def test_http_stats_cover_only_the_placement(aiohttp_client, store):
    from datetime import date

    ad_id = live_ad(store)
    mine = store.create_publisher(1, "Mine", "web", [])
    other = store.create_publisher(2, "Other", "web", [])
    today = date.today().isoformat()
    store.count(today, ad_id, mine["id"], "view", 4)
    store.count(today, ad_id, mine["id"], "click", 1)
    store.count(today, ad_id, other["id"], "view", 100)
    client = await aiohttp_client(make_app(store, None, URL))
    report = await (await client.get(f"/litfass/v1/stats/{mine['key']}")).json()
    assert report["placement"] == "Mine"
    assert report["totals"]["7"] == {"view": 4, "click": 1, "reward": 0}
    assert len(report["days"]) == 30 and report["days"][-1] == {"day": today, "view": 4, "click": 1, "reward": 0}
    assert report["ads"] == [{"id": ad_id, "title": "Title", "view": 4, "click": 1, "reward": 0}]
    assert (await client.get("/v1/stats/nope")).status == 404


async def test_http_network_stats_need_the_token(aiohttp_client, store):
    live_ad(store)
    store.create_publisher(1, "P", "web", ["news"])
    client = await aiohttp_client(make_app(store, None, URL, "secret"))
    assert (await client.get("/v1/admin/stats")).status == 401
    assert (await client.get("/v1/admin/stats", headers={"Authorization": "Bearer wrong"})).status == 401
    report = await (await client.get("/v1/admin/stats", headers={"Authorization": "Bearer secret"})).json()
    assert report["ads"][0]["live"] is True and report["placements"][0]["categories"] == ["news"]
    open_client = await aiohttp_client(make_app(store, None, URL))
    assert (await open_client.get("/v1/admin/stats", headers={"Authorization": "Bearer "})).status == 401


def test_translations_are_complete():
    from pathlib import Path

    from ptbkit.check import assert_complete

    from litfass_server.feed import CATEGORIES
    from litfass_server.texts import STRINGS, labels

    assert_complete(STRINGS, Path(__file__).resolve().parents[1] / "litfass_server", dynamic=("command.", "label.", "p_", "f_", "s_by_"))
    assert labels(CATEGORIES, "de")["news"] == "📰 Nachrichten"
    assert labels(CATEGORIES, "en")["news"] == "📰 News"


def test_overview_in_german(store):
    from litfass_server.stats import overview

    assert "Noch keine Aufrufe" in overview(store, "Titel", {}, by="ad_id", lang="de")
