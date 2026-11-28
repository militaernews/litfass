"""The Telegram-authenticated management API: signature, roles and adverts."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from litfass_server.api import handle, verify_init_data
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
    assert result.status == 403


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
