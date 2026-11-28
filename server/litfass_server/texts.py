"""The bot's wording: one JSON file per language in server/res/strings/ (en.json has every key, de.json
the German translation), loaded with ptbkit. The language comes from the user's Telegram client."""

from __future__ import annotations

from pathlib import Path

from ptbkit import Strings

STRINGS = Strings(Path(__file__).resolve().parents[1] / "res" / "strings")
COMMANDS = ("menu", "register", "mine", "campaigns", "stats", "post", "stars", "support", "cancel")


def lang_of(user: object | None) -> str:
    return STRINGS.lang_of(user)


def t(lang: str, key: str, **values: object) -> str:
    return STRINGS.get(lang, key, **values)


def labels(options: dict[str, str], lang: str) -> dict[str, str]:
    """A feed.py option table (categories, kinds …) with the language's `label.<key>` texts."""
    return {key: STRINGS.get(lang, f"label.{key}") if STRINGS.has(f"label.{key}") else label for key, label in options.items()}
