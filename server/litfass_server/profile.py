"""Applies the bot's name, descriptions and profile photo once: `python -m litfass_server.profile`."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from telegram import Bot, InputProfilePhotoStatic

LOGO = Path(__file__).resolve().parents[2] / "brand" / "logo.png"

PROFILE = {
    "en": (
        "Litfass",
        "House adverts, no tracking",
        "Litfass shows house adverts in websites, Mini Apps, bots and channels.\n\n"
        "/register your placement, pick the content you publish and get a feed with adverts that fit. "
        "No ad network, no tracking: only daily totals are counted.",
    ),
    "de": (
        "Litfass",
        "Eigenwerbung ohne Tracking",
        "Litfass zeigt Eigenwerbung auf Websites, in Mini Apps, Bots und Kanälen.\n\n"
        "Mit /register meldest du deinen Werbeplatz an, wählst deine Inhalte und bekommst einen Feed mit passender Werbung. "
        "Kein Werbenetzwerk, kein Tracking: gezählt werden nur Tagessummen.",
    ),
}


async def main() -> None:
    bot = Bot(os.environ["LITFASS_TOKEN"])
    async with bot:
        for lang, (name, short, description) in PROFILE.items():
            code = None if lang == "en" else lang
            await bot.set_my_name(name, language_code=code)
            await bot.set_my_short_description(short, language_code=code)
            await bot.set_my_description(description, language_code=code)
        with LOGO.open("rb") as file:
            await bot.set_my_profile_photo(InputProfilePhotoStatic(file))
    print("profile applied")


if __name__ == "__main__":
    asyncio.run(main())
