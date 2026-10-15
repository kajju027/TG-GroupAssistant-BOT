from __future__ import annotations
import asyncio
import logging
import sys
from pathlib import Path
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from bot import database as group_db
from bot.core import database as core_db
from bot.core.config import BOT_TOKEN, LOG_LEVEL, OWNER_ID, TG_API_PROXY
from bot.handlers import antifake, antilink, antiword, antispam, chat_tracker, download, filters, mute, owner, panel, reactions, settings, start, tag, warn, welcome
from bot.middlewares.admin_check import AdminCheckMiddleware
from bot.middlewares.tracking import GroupTrackingMiddleware
log_level = getattr(logging, LOG_LEVEL, logging.INFO)
if not isinstance(log_level, int):
    log_level = logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
_LOG = logging.getLogger('group_assistant_bot')

def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.middleware(GroupTrackingMiddleware())
    dispatcher.message.middleware(AdminCheckMiddleware())
    dispatcher.include_router(chat_tracker.router)
    dispatcher.include_router(antifake.router)
    dispatcher.include_router(welcome.router)
    dispatcher.include_router(start.router)
    dispatcher.include_router(owner.router)
    dispatcher.include_router(panel.router)
    dispatcher.include_router(settings.router)
    dispatcher.include_router(mute.router)
    dispatcher.include_router(warn.router)
    dispatcher.include_router(tag.router)
    dispatcher.include_router(antilink.router)
    dispatcher.include_router(antiword.router)
    dispatcher.include_router(antispam.router)
    dispatcher.include_router(filters.router)
    dispatcher.include_router(download.router)
    dispatcher.include_router(reactions.router)
    return dispatcher

async def _main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN is not set. Copy .env.example to .env and fill it in.')
    if OWNER_ID <= 0:
        raise RuntimeError('OWNER_ID is not set or invalid. It must be your numeric Telegram user ID.')
    core_db.init()
    await group_db.init_db()
    _LOG.info('Storage initialised.')
    session = AiohttpSession(proxy=TG_API_PROXY) if TG_API_PROXY else AiohttpSession()
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = build_dispatcher()
    allowed_updates = dispatcher.resolve_used_update_types()
    try:
        me = await bot.get_me()
        await bot.delete_webhook(drop_pending_updates=False)
        _LOG.info('@%s online | owner_id=%d | updates=%s', me.username, OWNER_ID, ','.join(allowed_updates))
        await dispatcher.start_polling(bot, allowed_updates=allowed_updates, close_bot_session=False, handle_signals=True)
    except TelegramUnauthorizedError as error:
        _LOG.critical('Bot token was rejected by Telegram: %s', error)
        raise RuntimeError('BOT_TOKEN is invalid or revoked.') from error
    except TelegramConflictError as error:
        _LOG.critical('Polling conflict: another process is already using this bot token. Stop every duplicate deployment before starting this instance. (%s)', error)
        raise
    except TelegramNetworkError as error:
        _LOG.critical('Telegram cannot be reached: %s', error)
        raise
    finally:
        await bot.session.close()
        _LOG.info('Bot stopped.')

def main() -> None:
    asyncio.run(_main())
if __name__ == '__main__':
    main()
