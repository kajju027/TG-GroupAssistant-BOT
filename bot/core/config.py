import os
import sys
from bot.core.logger import get_logger
log = get_logger('CONFIG')

def _get_int_env(name: str, default: int=0) -> int:
    raw = os.getenv(name, '')
    if raw is None or raw.strip() == '':
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log.warn(f'Invalid value for {name}={raw!r}, using default {default}.')
        return default

def _resolve_data_dir() -> str:
    override = os.getenv('DATA_DIR', '').strip()
    if override:
        return os.path.abspath(override)

    this_file = os.path.abspath(__file__)
    parts = this_file.split(os.sep)
    if 'bot_code' in parts:
        idx = parts.index('bot_code')
        panel_root = os.sep.join(parts[:idx]) or os.sep
        return os.path.join(panel_root, 'bot_data')

    return os.path.abspath('bot_data')

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
OWNER_ID = _get_int_env('OWNER_ID', 0)
DATA_DIR = _resolve_data_dir()
CHATS_DIR = os.path.join(DATA_DIR, 'chats')
USERS_DIR = os.path.join(DATA_DIR, 'users')
GITHUB_REPO = os.getenv('GITHUB_REPO', '').strip()
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main').strip() or 'main'

def validate():
    if not BOT_TOKEN or BOT_TOKEN.upper() in {'YOUR_BOT_TOKEN_HERE', 'YOUR_BOT_TOKEN_FROM_BOTFATHER'}:
        log.critical('BOT_TOKEN is missing or not set.')
        log.info("Set it in your hosting panel's Environment Variables (or in a local .env file).")
        log.info('Get a token from @BotFather on Telegram.')
        sys.exit(1)
    if OWNER_ID == 0:
        log.warn('OWNER_ID is not set (or is 0). Owner-only commands will not work for anyone.')
        log.warn('Set OWNER_ID to your numeric Telegram user ID (get it from @userinfobot).')
    log.info(f'Persistent data directory: {DATA_DIR}')
