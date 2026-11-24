"""Runs the management bot and the feed server in one process.

Environment: LITFASS_TOKEN (the bot token), LITFASS_ADMIN_IDS (comma-separated Telegram user ids),
LITFASS_PUBLIC_URL (where the feed server is reachable from outside, without a trailing slash),
LITFASS_DB (SQLite file, default data/litfass.db), LITFASS_PORT (default 3792) and LITFASS_STATS_TOKEN
(a secret that unlocks GET /v1/admin/stats for admin dashboards; unset disables it).
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from telegram import BotCommand, Update
from telegram.ext import Application

from litfass_server.bot import Ctx, register_handlers
from litfass_server.store import Store
from litfass_server.web import make_app

logging.basicConfig(format="%(asctime)s %(levelname)-5s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("litfass")

COMMANDS = [
    BotCommand("register", "Show adverts in your site, bot or channel"),
    BotCommand("mine", "Your placements and feed URLs"),
    BotCommand("stats", "How your adverts are doing"),
    BotCommand("cancel", "Stop the current input"),
]


async def main() -> None:
    token = os.environ["LITFASS_TOKEN"]
    admins = {int(part) for part in os.getenv("LITFASS_ADMIN_IDS", "").split(",") if part.strip()}
    public_url = os.environ["LITFASS_PUBLIC_URL"].rstrip("/")
    store = Store(os.getenv("LITFASS_DB", "data/litfass.db"))

    app = Application.builder().token(token).build()
    app.bot_data["litfass"] = Ctx(store, admins, public_url)
    register_handlers(app)

    runner = web.AppRunner(make_app(store, app.bot, public_url, os.getenv("LITFASS_STATS_TOKEN", "")), access_log=None)
    async with app:
        await app.bot.set_my_commands(COMMANDS)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", int(os.getenv("LITFASS_PORT", "3792"))).start()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("litfass running with %d admin(s)", len(admins))
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
