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
from bot.handlers import reactions, chat_tracker
from bot.middlewares.admin_check import AdminCheckMiddleware
log = get_logger('BOT')

def _build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AdminCheckMiddleware())
    dp.include_router(start.router)
    dp.include_router(chat_tracker.router)
    dp.include_router(settings.router)
    dp.include_router(warn.router)
    dp.include_router(mute.router)
    dp.include_router(tag.router)
    dp.include_router(welcome.router)
    dp.include_router(antifake.router)
    dp.include_router(reactions.router)
    dp.include_router(antilink.router)
    dp.include_router(antiword.router)
    dp.include_router(antispam.router)
    dp.include_router(filter_handler.router)
    return dp

async def run():
    quiet_third_party_loggers()
    validate()
    log.section('DATABASE')
    await init_db()
    log.success('Database ready.')
    log.section('STARTING BOT')
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = _build_dispatcher()
    try:
        me = await bot.get_me()
        log.success(f'Logged in as @{me.username} (id: {me.id})')
    except TelegramUnauthorizedError:
        log.critical('BOT_TOKEN is invalid/unauthorized.')
        log.info("Double-check the token from @BotFather and your hosting panel's environment variables.")
        raise
    log.success('All feature modules loaded:')
    for name in ['start', 'chat_tracker', 'settings', 'warn', 'mute', 'tag', 'welcome', 'antifake', 'antilink', 'antiword', 'antispam', 'filters', 'reactions']:
        log.info(f'   • {name}')
    log.section('POLLING')
    log.success('Bot is now online and listening for updates. 🚀')
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        log.critical('Telegram reports another instance of this bot is already polling. Make sure only ONE instance is running at a time (check for duplicate processes/servers on your hosting panel).')
        raise
    except Exception as e:
        log.critical(f'Bot crashed with an unexpected error: {e}')
        raise
    finally:
        await bot.session.close()

def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.warn('Bot stopped manually.')
    except SystemExit:
        raise
    except Exception:
        raise
if __name__ == '__main__':
    main()
