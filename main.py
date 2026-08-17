"""
Post Maker Bot — Entry point.

Boots the bot, initialises the database, registers middlewares and routers,
and starts long-polling.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database import init_database
from bot.database.connection import close_db
from bot.handlers import get_main_router
from bot.middlewares import UserMiddleware


def configure_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # Quieten noisy third-party loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    # ── Database ───────────────────────────────────────────────
    logger.info("Initialising database…")
    await init_database()

    # ── Bot & Dispatcher ───────────────────────────────────────
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Middleware ─────────────────────────────────────────────
    dp.update.middleware(UserMiddleware())

    # ── Routers ────────────────────────────────────────────────
    dp.include_router(get_main_router())

    # ── Start ──────────────────────────────────────────────────
    bot_info = await bot.get_me()
    logger.info(
        "Starting bot @%s (id=%d) — polling…",
        bot_info.username,
        bot_info.id,
    )

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Shutting down — closing database connection…")
        await close_db()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
