import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core.config import BOT_TOKEN, OWNER_ID, TG_API_PROXY, LOG_LEVEL
from bot.core import database as db
from bot.middlewares.tracking import GroupTrackingMiddleware
from bot.handlers import start, owner, group, react, download

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_LOG = logging.getLogger("group_assistant_bot")


async def _main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set.")
    if OWNER_ID <= 0:
        raise RuntimeError("OWNER_ID is not set or invalid.")

    db.init()
    _LOG.info("Database initialised.")

    if TG_API_PROXY:
        _LOG.info("Telegram API proxy: %s", TG_API_PROXY)
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(TG_API_PROXY, is_local=False)
        )
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(GroupTrackingMiddleware())

    dp.include_router(start.router)
    dp.include_router(owner.router)
    dp.include_router(group.router)
    dp.include_router(download.router)
    dp.include_router(react.router)

    attempt = 0
    while True:
        try:
            me = await bot.get_me()
            break
        except TelegramNetworkError as e:
            delay = min(60, 5 * (2 ** min(attempt, 4)))
            _LOG.error("Telegram unreachable — retrying in %ds (%s)", delay, e)
            attempt += 1
            await asyncio.sleep(delay)
        except TelegramUnauthorizedError as e:
            _LOG.critical("Invalid BOT_TOKEN: %s", e)
            raise RuntimeError("Bot token rejected.") from e

    _LOG.info("@%s online | owner_id=%d", me.username, OWNER_ID)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types() + ["channel_post"],
        )
    finally:
        await bot.session.close()
        _LOG.info("Bot stopped.")


def main():
    asyncio.run(_main())
