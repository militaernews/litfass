"""The Telegram-authenticated management API: signature, roles and adverts."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from litfass_server.api import handle, verify_init_data
from litfass_server.feed import build_feed
from litfass_server.pricing import ACTIVATION_STARS, CLICK_STARS
from litfass_server.store import Store

TOKEN = "test-token"


def signed(uid: int = 42, when: int | None = None) -> str:
    fields = {"user": json.dumps({"id": uid, "first_name": "Ada"}), "auth_date": str(when or int(time.time()))}
    check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


class Request:
    def __init__(self, body: dict, init_data: str = "") -> None:
        self.headers = {"x-telegram-init-data": init_data}
        self.body = body

    async def json(self) -> dict:
        return self.body


async def call(store: Store, body: dict, init_data: str = signed(), admins: set[int] = {42}):
    return await handle(store, admins, TOKEN, Request(body, init_data))


def test_init_data_signature_and_age() -> None:
    assert verify_init_data(signed(), TOKEN) is not None
    assert verify_init_data(signed(), "other-token") is None
    assert verify_init_data(signed(when=int(time.time()) - 25 * 3600), TOKEN) is None
    assert verify_init_data("", TOKEN) is None


async def test_roles() -> None:
    store = Store(":memory:")
    assert (await call(store, {"action": "me"})).status == 200
    assert (await call(store, {"action": "me"}, "")).status == 401
    assert (await call(store, {"action": "list_ads"}, signed(7))).status == 200
    result = await call(store, {"action": "create_ad", "url": "https://t.me/x", "text": {"en": {"title": "T", "body": "B", "cta": "Go"}}}, signed(7))
    assert result.status == 200
    ad_id = json.loads(result.text)["id"]
    assert (await call(store, {"action": "delete_ad", "id": ad_id}, signed(8))).status == 403


async def test_ad_crud_and_validation() -> None:
    store = Store(":memory:")
    body = {"action": "create_ad", "url": "https://t.me/x", "text": {"en": {"title": "T", "body": "B", "cta": "Go"}}}
    response = await call(store, body)
    assert response.status == 200
    ad_id = json.loads(response.text)["id"]

    response = await call(store, {"action": "list_ads"})
    assert json.loads(response.text)["ads"][0]["text"]["en"]["title"] == "T"

    response = await call(
        store,
        {"action": "update_ad", "id": ad_id, "paused": False, "categories": ["news"], "weight": 3},
    )
    assert response.status == 200
    ads = json.loads((await call(store, {"action": "list_ads"})).text)["ads"]
    assert not ads[0]["paused"] and ads[0]["weight"] == 3

    response = await call(store, dict(body, url="http://x"))
    assert response.status == 400
    response = await call(store, {"action": "update_ad", "id": ad_id, "style": {"background": "red"}})
    assert response.status == 400

    assert (await call(store, {"action": "delete_ad", "id": ad_id})).status == 200
    assert json.loads((await call(store, {"action": "list_ads"})).text)["ads"] == []


async def test_stars_and_free_opt_in() -> None:
    store = Store(":memory:")
    publisher = store.create_publisher(7, "Chat", "channel", [])
    body = {
        "action": "create_ad",
        "url": "https://t.me/x",
        "paid": True,
        "text": {"en": {"title": "Paid", "body": "B", "cta": "Go"}},
    }
    assert (await call(store, body)).status == 402
    assert store.credit_stars(42, 100, "charge-1") is True
    assert store.credit_stars(42, 100, "charge-1") is False
    assert (await call(store, body)).status == 200
    assert store.stars(42) == 100 - ACTIVATION_STARS

    ad_id = next(ad["id"] for ad in store.list_ads() if ad["paid"])
    store.update_ad(ad_id, paused=False)
    free_id = store.create_ad("https://t.me/free")
    store.update_ad(free_id, paused=False)
    store.set_text(free_id, "en", "Free", "B", "Go")
    assert len(build_feed(store, publisher, "https://ads.example")["ads"]) == 2
    store.update_publisher(publisher["id"], allow_free=False)
    publisher = store.get_publisher(publisher["id"])
    assert [ad["id"] for ad in build_feed(store, publisher, "https://ads.example")["ads"]] == [ad_id]

    assert store.charge_click(ad_id, publisher["id"], CLICK_STARS) is True
    assert store.stars(42) == 100 - ACTIVATION_STARS - CLICK_STARS
    assert store.earnings(publisher["id"]) == CLICK_STARS
    assert store.charge_click(free_id, publisher["id"], CLICK_STARS) is True
    assert store.earnings(publisher["id"]) == CLICK_STARS


async def test_campaign_report() -> None:
    store = Store(":memory:")
    store.credit_stars(42, 20, "charge")
    result = await call(
        store,
        {"action": "create_ad", "url": "https://t.me/x", "paid": True, "text": {"en": {"title": "Campaign", "body": "B", "cta": "Go"}}},
    )
    ad_id = json.loads(result.text)["id"]
    store.count("2026-11-28", ad_id, 1, "view", 10)
    store.count("2026-11-28", ad_id, 1, "click", 2)
    stats = json.loads((await call(store, {"action": "stats"})).text)
    campaign = stats["campaigns"][0]
    assert campaign["views"] == 10 and campaign["clicks"] == 2 and campaign["ctr"] == 20.0
    me = json.loads((await call(store, {"action": "me"})).text)
    assert me["stars"] == 20 - ACTIVATION_STARS
