"""SQLite storage for adverts and the publishers that show them."""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    emoji TEXT,
    image_file_id TEXT,
    image_rev INTEGER NOT NULL DEFAULT 0,
    video TEXT,
    task_chat TEXT,
    weight INTEGER NOT NULL DEFAULT 1,
    start TEXT,
    "end" TEXT,
    paused INTEGER NOT NULL DEFAULT 1,
    paid INTEGER NOT NULL DEFAULT 0,
    placements TEXT NOT NULL DEFAULT '[]',
    categories TEXT NOT NULL DEFAULT '[]',
    style TEXT NOT NULL DEFAULT '{}',
    created_by INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ad_texts (
    ad_id TEXT NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    lang TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT NOT NULL,
    PRIMARY KEY (ad_id, lang)
);
-- Daily totals only: no IP address, no user id, nothing that singles out a viewer
CREATE TABLE IF NOT EXISTS stats (
    day TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    publisher_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, ad_id, publisher_id, event)
);
CREATE TABLE IF NOT EXISTS publishers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    categories TEXT NOT NULL DEFAULT '[]',
    blocked INTEGER NOT NULL DEFAULT 0,
    allow_free INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);
-- Stars paid by advertisers, tracked internally; payouts are handled by the operator
CREATE TABLE IF NOT EXISTS stars_balances (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS publisher_earnings (
    publisher_id INTEGER PRIMARY KEY REFERENCES publishers(id) ON DELETE CASCADE,
    stars INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    charge_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
-- One completed join-task per advert, user and day
CREATE TABLE IF NOT EXISTS task_rewards (
    day TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (day, ad_id, user_id)
);
"""

EVENTS = ("view", "click", "reward")
JSON_FIELDS = ("placements", "categories", "style")
AD_FIELDS = ("url", "emoji", "image_file_id", "image_rev", "video", "task_chat", "weight", "start", "end", "paused", "paid", *JSON_FIELDS)
PUBLISHER_FIELDS = ("name", "kind", "categories", "blocked", "allow_free")


def new_key() -> str:
    return secrets.token_urlsafe(16)


def _decode(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    item = dict(row)
    for field in JSON_FIELDS:
        if field in item:
            item[field] = json.loads(item[field])
    return item


def _encode(field: str, value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if field in JSON_FIELDS else value


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        # Older databases gain the paid / opt-in columns without losing data
        for table, column, definition in (
            ("ads", "paid", "INTEGER NOT NULL DEFAULT 0"),
            ("ads", "video", "TEXT"),
            ("ads", "task_chat", "TEXT"),
            ("publishers", "allow_free", "INTEGER NOT NULL DEFAULT 1"),
        ):
            columns = {row["name"] for row in self.db.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    # Adverts ------------------------------------------------------------------------------------

    def create_ad(self, url: str, created_by: int | None = None) -> str:
        now = int(time.time())
        while True:
            ad_id = secrets.token_hex(4)
            if not self.db.execute("SELECT 1 FROM ads WHERE id = ?", (ad_id,)).fetchone():
                break
        with self.db:
            self.db.execute(
                "INSERT INTO ads (id, url, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (ad_id, url, created_by, now, now),
            )
        return ad_id

    def update_ad(self, ad_id: str, **fields: Any) -> None:
        unknown = set(fields) - set(AD_FIELDS)
        if unknown:
            raise ValueError(f"unknown ad fields: {unknown}")
        if not fields:
            return
        columns = ", ".join(f'"{field}" = ?' for field in fields)
        values = [_encode(field, value) for field, value in fields.items()]
        with self.db:
            self.db.execute(f"UPDATE ads SET {columns}, updated_at = ? WHERE id = ?", (*values, int(time.time()), ad_id))

    def set_text(self, ad_id: str, lang: str, title: str, body: str, cta: str) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO ad_texts (ad_id, lang, title, body, cta) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (ad_id, lang) DO UPDATE SET title = excluded.title, body = excluded.body, cta = excluded.cta",
                (ad_id, lang, title, body, cta),
            )

    def delete_text(self, ad_id: str, lang: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM ad_texts WHERE ad_id = ? AND lang = ?", (ad_id, lang))

    def get_ad(self, ad_id: str) -> dict | None:
        ad = _decode(self.db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)).fetchone())
        if ad:
            ad["text"] = {
                row["lang"]: {"title": row["title"], "body": row["body"], "cta": row["cta"]}
                for row in self.db.execute("SELECT * FROM ad_texts WHERE ad_id = ? ORDER BY lang", (ad_id,))
            }
        return ad

    def list_ads(self) -> list[dict]:
        ids = [row["id"] for row in self.db.execute("SELECT id FROM ads ORDER BY created_at")]
        return [ad for ad in (self.get_ad(ad_id) for ad_id in ids) if ad]

    def delete_ad(self, ad_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))

    # Publishers ---------------------------------------------------------------------------------

    def create_publisher(self, owner_id: int, name: str, kind: str, categories: list[str]) -> dict:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO publishers (key, owner_id, name, kind, categories, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (new_key(), owner_id, name, kind, json.dumps(categories), int(time.time())),
            )
        return self.get_publisher(cursor.lastrowid)

    def get_publisher(self, publisher_id: int) -> dict | None:
        return _decode(self.db.execute("SELECT * FROM publishers WHERE id = ?", (publisher_id,)).fetchone())

    def publisher_by_key(self, key: str) -> dict | None:
        return _decode(self.db.execute("SELECT * FROM publishers WHERE key = ?", (key,)).fetchone())

    def publishers(self, owner_id: int | None = None) -> list[dict]:
        if owner_id is None:
            rows = self.db.execute("SELECT * FROM publishers ORDER BY id")
        else:
            rows = self.db.execute("SELECT * FROM publishers WHERE owner_id = ? ORDER BY id", (owner_id,))
        return [_decode(row) for row in rows]

    def update_publisher(self, publisher_id: int, **fields: Any) -> None:
        unknown = set(fields) - set(PUBLISHER_FIELDS)
        if unknown:
            raise ValueError(f"unknown publisher fields: {unknown}")
        if not fields:
            return
        columns = ", ".join(f"{field} = ?" for field in fields)
        values = [_encode(field, value) for field, value in fields.items()]
        with self.db:
            self.db.execute(f"UPDATE publishers SET {columns} WHERE id = ?", (*values, publisher_id))

    def rotate_key(self, publisher_id: int) -> str:
        key = new_key()
        with self.db:
            self.db.execute("UPDATE publishers SET key = ? WHERE id = ?", (key, publisher_id))
        return key

    def delete_publisher(self, publisher_id: int) -> None:
        with self.db:
            self.db.execute("DELETE FROM publishers WHERE id = ?", (publisher_id,))

    # Stats --------------------------------------------------------------------------------------

    def count(self, day: str, ad_id: str, publisher_id: int, event: str, amount: int = 1) -> None:
        if event not in EVENTS:
            raise ValueError(f"unknown event {event}")
        with self.db:
            self.db.execute(
                "INSERT INTO stats (day, ad_id, publisher_id, event, count) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (day, ad_id, publisher_id, event) DO UPDATE SET count = count + excluded.count",
                (day, ad_id, publisher_id, event, amount),
            )

    # Join tasks -----------------------------------------------------------------------------------

    def task_done(self, day: str, ad_id: str, user_id: int) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM task_rewards WHERE day = ? AND ad_id = ? AND user_id = ?", (day, ad_id, user_id)
            ).fetchone()
            is not None
        )

    def mark_task(self, day: str, ad_id: str, user_id: int) -> bool:
        """Records one reward per user and day; False when it was already recorded."""
        with self.db:
            try:
                self.db.execute(
                    "INSERT INTO task_rewards (day, ad_id, user_id) VALUES (?, ?, ?)", (day, ad_id, user_id)
                )
            except sqlite3.IntegrityError:
                return False
        return True

    # Stars ---------------------------------------------------------------------------------------

    def stars(self, user_id: int) -> int:
        row = self.db.execute("SELECT balance FROM stars_balances WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["balance"]) if row else 0

    def credit_stars(self, user_id: int, stars: int, charge_id: str) -> bool:
        """Records a paid invoice once and credits the advertiser's balance. False on a repeated charge."""
        with self.db:
            try:
                self.db.execute(
                    "INSERT INTO payments (charge_id, user_id, stars, created_at) VALUES (?, ?, ?, ?)",
                    (charge_id, user_id, stars, int(time.time())),
                )
            except sqlite3.IntegrityError:
                return False
            self.db.execute(
                "INSERT INTO stars_balances (user_id, balance, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id) DO UPDATE SET balance = balance + excluded.balance, updated_at = excluded.updated_at",
                (user_id, stars, int(time.time())),
            )
        return True

    def spend_stars(self, user_id: int, stars: int) -> bool:
        with self.db:
            cursor = self.db.execute(
                "UPDATE stars_balances SET balance = balance - ?, updated_at = ? WHERE user_id = ? AND balance >= ?",
                (stars, int(time.time()), user_id, stars),
            )
            return cursor.rowcount == 1

    def earnings(self, publisher_id: int) -> int:
        row = self.db.execute("SELECT stars FROM publisher_earnings WHERE publisher_id = ?", (publisher_id,)).fetchone()
        return int(row["stars"]) if row else 0

    def charge_click(self, ad_id: str, publisher_id: int, stars: int) -> bool:
        """Bill a click on a paid advert to its owner and credit the publisher; free ads cost nothing."""
        ad = self.get_ad(ad_id)
        if not ad or not ad["paid"]:
            return True
        owner = ad.get("created_by")
        if owner is None or not self.spend_stars(owner, stars):
            return False
        with self.db:
            self.db.execute(
                "INSERT INTO publisher_earnings (publisher_id, stars, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (publisher_id) DO UPDATE SET stars = stars + excluded.stars, updated_at = excluded.updated_at",
                (publisher_id, stars, int(time.time())),
            )
        return True

    def totals(
        self,
        since: str,
        *,
        ad_id: str | None = None,
        publisher_id: int | None = None,
        ad_ids: list[str] | None = None,
        publisher_ids: list[int] | None = None,
        by: str | None = None,
    ) -> dict:
        """Event totals since a day (inclusive), optionally for one ad or publisher, optionally grouped
        by `ad_id`, `publisher_id` or `day`: {group: {event: count}} (group None when ungrouped)."""
        if by not in (None, "ad_id", "publisher_id", "day"):
            raise ValueError(by)
        where, params = ["day >= ?"], [since]
        if ad_id is not None:
            where.append("ad_id = ?")
            params.append(ad_id)
        if publisher_id is not None:
            where.append("publisher_id = ?")
            params.append(publisher_id)
        if ad_ids is not None:
            where.append("ad_id IN (%s)" % ",".join("?" for _ in ad_ids) if ad_ids else "1=0")
            params.extend(ad_ids)
        if publisher_ids is not None:
            where.append("publisher_id IN (%s)" % ",".join("?" for _ in publisher_ids) if publisher_ids else "1=0")
            params.extend(publisher_ids)
        group = by or "NULL"
        rows = self.db.execute(
            f"SELECT {group} AS grp, event, SUM(count) AS n FROM stats WHERE {' AND '.join(where)} GROUP BY grp, event",
            params,
        )
        result: dict = {}
        for row in rows:
            result.setdefault(row["grp"], {e: 0 for e in EVENTS})[row["event"]] = row["n"]
        return result
