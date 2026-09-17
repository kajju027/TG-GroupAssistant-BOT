"""
bot/main.py — the real bot runtime.

This module is downloaded fresh from GitHub every time index.py starts
(see index.py at the repo root of your PANEL project, not this repo).
It builds the aiogram Dispatcher, registers every feature router in
the correct order, and starts polling.
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramUnauthorizedError, TelegramConflictError

from bot.core.config import BOT_TOKEN, validate
from bot.core.logger import get_logger, quiet_third_party_loggers
from bot.database import init_db
from bot.handlers import start, settings, antilink, antiword, antispam, antifake
from bot.handlers import welcome, warn, mute, tag, filters as filter_handler
from bot.middlewares.admin_check import AdminCheckMiddleware

log = get_logger("BOT")


def _build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AdminCheckMiddleware())

    # NOTE: Order matters in aiogram. Routers/handlers that match
    # commands (e.g. /warn, /mute, /settings) MUST be registered
    # before the generic "catch every text message" handlers used
    # by antilink/antiword/antispam/filters. Otherwise those
    # catch-all handlers intercept the update first and no command
    # ever reaches its intended handler.
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(warn.router)
    dp.include_router(mute.router)
    dp.include_router(tag.router)
    dp.include_router(welcome.router)
    dp.include_router(antifake.router)

    # Command sub-handlers inside these routers are registered above
    # their catch-all counterparts *inside the same router* (see
    # handlers/antilink.py, antiword.py, antispam.py, filters.py), and
    # the catch-all handlers explicitly ignore text starting with "/"
    # so they never swallow commands meant for other routers.
    dp.include_router(antilink.router)
    dp.include_router(antiword.router)
    dp.include_router(antispam.router)
    dp.include_router(filter_handler.router)

    return dp


async def run():
    quiet_third_party_loggers()
    validate()

    log.section("DATABASE")
    await init_db()
    log.success("Database ready.")

    log.section("STARTING BOT")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = _build_dispatcher()

    try:
        me = await bot.get_me()
        log.success(f"Logged in as @{me.username} (id: {me.id})")
    except TelegramUnauthorizedError:
        log.critical("BOT_TOKEN is invalid/unauthorized.")
        log.info("Double-check the token from @BotFather and your hosting panel's environment variables.")
        raise

    log.success("All feature modules loaded:")
    for name in ["start", "settings", "warn", "mute", "tag", "welcome",
                 "antifake", "antilink", "antiword", "antispam", "filters"]:
        log.info(f"   • {name}")

    log.section("POLLING")
    log.success("Bot is now online and listening for updates. 🚀")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        log.critical(
            "Telegram reports another instance of this bot is already polling. "
            "Make sure only ONE instance is running at a time (check for duplicate "
            "processes/servers on your hosting panel)."
        )
        raise
    except Exception as e:
        log.critical(f"Bot crashed with an unexpected error: {e}")
        raise
    finally:
        await bot.session.close()


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.warn("Bot stopped manually.")
    except SystemExit:
        raise
    except Exception:
        raise


if __name__ == "__main__":
    main()
