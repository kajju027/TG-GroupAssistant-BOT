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
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage

from bot import database as group_db
from bot.core import database as core_db
from bot.core.config import ANIMATIONS, BOT_TOKEN, LOG_LEVEL, OWNER_ID, STYLIZE_OUTPUT, TG_API_BASE, TG_API_PROXY
from bot.core.logger import get_logger, quiet_third_party_loggers
from bot.handlers import (
    antilink,
    antiword,
    antispam,
    channel_guard,
    chat_tracker,
    download,
    filters,
    mute,
    owner,
    panel,
    reactions,
    settings,
    start,
    tag,
    warn,
    welcome,
)
from bot.middlewares.admin_check import AdminCheckMiddleware
from bot.middlewares.tracking import GroupTrackingMiddleware
from bot.utils import style

log_level = getattr(logging, LOG_LEVEL, logging.INFO)
if not isinstance(log_level, int):
    log_level = logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
_LOG = logging.getLogger('group_assistant_bot')
_BANNER = get_logger('STARTUP')

_PROXY_SCHEME_ALIASES = {'https': 'http', 'socks5h': 'socks5', 'socks4a': 'socks4'}
_SUPPORTED_PROXY_SCHEMES = {'http', 'socks4', 'socks5'}


def normalise_proxy(raw: str) -> str | None:
    """Turn a user supplied proxy string into a URL python-socks accepts.

    Returns None when the value is empty or unusable, so the bot can connect
    directly: a broken proxy must never keep it offline."""
    value = (raw or '').strip()
    if not value:
        return None
    if '://' not in value:
        _LOG.info('TG_API_PROXY has no scheme; treating it as an HTTP proxy.')
        value = 'http://' + value
    scheme, _, rest = value.partition('://')
    scheme = scheme.lower()
    alias = _PROXY_SCHEME_ALIASES.get(scheme)
    if alias is not None:
        _LOG.warning('TG_API_PROXY scheme "%s://" is not supported by python-socks; using it as "%s://" instead.', scheme, alias)
        value = alias + '://' + rest
        scheme = alias
    if scheme not in _SUPPORTED_PROXY_SCHEMES:
        _LOG.warning('TG_API_PROXY scheme "%s://" is not supported. Supported: http, socks5, socks4. Connecting directly.', scheme)
        return None
    return value


def proxy_display(proxy_url: str | None) -> str:
    if not proxy_url:
        return 'OFF (direct)'
    scheme, _, rest = proxy_url.partition('://')
    host_part = rest.split('@')[-1]
    return f'ON ({scheme}://{host_part})'


def fresh_session(proxy_url: str | None) -> tuple[AiohttpSession, bool]:
    session: AiohttpSession | None = None
    if proxy_url:
        try:
            session = AiohttpSession(proxy=proxy_url)
        except ValueError as error:
            _LOG.warning('TG_API_PROXY could not be applied (%s). Connecting directly instead.', error)
    applied = session is not None
    if session is None:
        session = AiohttpSession()
    if TG_API_BASE:
        _LOG.info('Routing every API call through the Telegram mirror %s.', TG_API_BASE)
        session.api = TelegramAPIServer.from_base(TG_API_BASE)
    return session, applied


def build_bot(proxy_url: str | None) -> tuple[Bot, bool]:
    session, applied = fresh_session(proxy_url)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return bot, applied


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Tracking runs before every handler (outer); admin checks run only for
    # matched handlers (inner) and are cached.
    dispatcher.message.outer_middleware(GroupTrackingMiddleware())
    dispatcher.channel_post.outer_middleware(GroupTrackingMiddleware())
    dispatcher.message.middleware(AdminCheckMiddleware())

    # Order matters: trackers → greetings → menus/panels → moderation →
    # protections → filters → downloads → reactions → channel guard.
    dispatcher.include_router(chat_tracker.router)
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
    dispatcher.include_router(channel_guard.router)

    @dispatcher.errors()
    async def on_error(*args):
        # aiogram 3 passes a single ErrorEvent; stay tolerant of both shapes.
        exception = None
        update = None
        if args:
            first = args[0]
            exception = getattr(first, 'exception', None)
            update = getattr(first, 'update', None)
            if exception is None and len(args) > 1:
                update = first
                exception = args[1]
        _LOG.error('Unhandled error: %s', exception, exc_info=exception or True)
        message = getattr(update, 'message', None) or getattr(update, 'effective_message', None)
        try:
            if message is not None and hasattr(message, 'answer'):
                await message.answer('⚠️ Something went wrong. Please try again.')
        except Exception:
            pass
        return True

    return dispatcher


async def connect(bot: Bot, using_proxy: bool):
    """Call get_me once; if a configured proxy is unreachable, retry directly."""
    try:
        return await bot.get_me()
    except TelegramNetworkError as error:
        if not using_proxy:
            raise
        _LOG.warning('The configured proxy did not answer (%s). Retrying once without a proxy.', error)
        await bot.session.close()
        bot.session, _ = fresh_session(None)
        return await bot.get_me()


async def _main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN is not set. Copy .env.example to .env and fill it in.')
    if OWNER_ID <= 0:
        raise RuntimeError('OWNER_ID is not set or invalid. It must be your numeric Telegram user ID.')
    if STYLIZE_OUTPUT:
        style.patch_outgoing_messages()
    quiet_third_party_loggers()
    core_db.init()
    await group_db.init_db()
    _LOG.info('Storage initialised.')
    proxy_url = normalise_proxy(TG_API_PROXY)
    bot, using_proxy = build_bot(proxy_url)
    dispatcher = build_dispatcher()
    allowed_updates = dispatcher.resolve_used_update_types()
    stats_task = asyncio.create_task(core_db.stats_flush_loop())
    try:
        me = await connect(bot, using_proxy)
        await bot.delete_webhook(drop_pending_updates=True)
        banner_lines = [
            f'🤖  @{me.username} is online',
            f'👑  Owner ID: {OWNER_ID}',
            f'🎨  Stylish fonts: {"ON" if STYLIZE_OUTPUT else "OFF"}',
            f'🎬  Animations: {"ON" if ANIMATIONS else "OFF (instant replies)"}',
            f'🔌  API proxy: {proxy_display(proxy_url if using_proxy else None)}',
        ]
        if TG_API_BASE:
            banner_lines.append(f'🌐  API mirror: {TG_API_BASE}')
        banner_lines.append(f'📡  Updates: {", ".join(allowed_updates)}')
        _BANNER.banner(banner_lines)
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
        stats_task.cancel()
        try:
            core_db.flush_stats()
        except Exception:
            pass
        await bot.session.close()
        _LOG.info('Bot stopped.')


def main() -> None:
    asyncio.run(_main())


if __name__ == '__main__':
    main()
