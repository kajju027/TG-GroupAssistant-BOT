from __future__ import annotations

import os
import time

from pathlib import Path

from dotenv import load_dotenv

# Repository root (…/bot_code when started through index.py).
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value) if minimum is not None else value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(int(default))).strip().casefold()
    return raw in {'1', 'true', 'yes', 'on'}


def _env_path(name: str, default: Path) -> Path:
    value = Path(os.getenv(name, str(default))).expanduser()
    return value if value.is_absolute() else BASE_DIR / value


def _env_ids(name: str) -> list[int]:
    raw = os.getenv(name, '').strip()
    result: list[int] = []
    for part in raw.replace(';', ',').split(','):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value > 0 and value not in result:
            result.append(value)
    return result


BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
OWNER_ID = _env_int('OWNER_ID', 0, minimum=0)
SUDO_IDS = list({OWNER_ID, *_env_ids('SUDO_IDS')} - {0})
TG_API_PROXY = os.getenv('TG_API_PROXY', '').strip()
TG_API_BASE = os.getenv('TG_API_BASE', '').strip().rstrip('/')

# Optional downloader API. When it is empty (or down) the downloader
# answers with a clean error instead of crashing the bot.
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.sayan-nexuswork.workers.dev').strip().rstrip('/')

# Persistent storage. index.py points DATA_DIR at the *panel* working
# directory (next to index.py), which survives code syncs and restarts.
# Everything else (sqlite + per-chat JSON) lives inside it.
DATA_DIR = _env_path('DATA_DIR', BASE_DIR / 'data')
DATABASE_PATH = _env_path('DATABASE_PATH', DATA_DIR / 'bot.sqlite3')
CHATS_DIR = _env_path('CHATS_DIR', DATA_DIR / 'chats')

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
MAX_DL_MB = _env_int('MAX_DOWNLOAD_MB', 50, minimum=1)

# Styling. Small caps are always on; animations default OFF for instant
# (super fast) replies. Set ANIMATIONS=true to get short intro effects.
STYLIZE_OUTPUT = _env_bool('STYLIZE_OUTPUT', True)
ANIMATIONS = _env_bool('ANIMATIONS', False)

START_TIME = time.time()

# Every emoji Telegram accepts as a bot reaction (positive ones only).
REACTION_EMOJIS: list[str] = [
    '👍', '❤', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱', '😢', '🎉',
    '🤩', '🙏', '👌', '🕊', '🥱', '🥴', '😍', '🐳', '❤\u200d🔥', '💯',
    '🤣', '⚡', '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '😴',
    '😭', '🤓', '👻', '👨\u200d💻', '👀', '🎃', '🙈', '😇', '😨', '🤝',
    '✍', '🤗', '🫡', '🎅', '🎄', '☃', '💅', '🤪', '🗿', '🆒', '💘',
    '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷', '😡', '🌚', '🌭',
]

# One-tap emoji sets for the reaction picker.
REACT_PRESETS: dict[str, list[str]] = {
    'fire': ['🔥', '❤\u200d🔥', '⚡', '💯', '🏆'],
    'party': ['🎉', '👏', '😁', '🤩', '🥰'],
    'love': ['❤', '❤\u200d🔥', '😍', '🥰', '💘'],
    'cool': ['😎', '🦄', '🏆', '💯', '🗿'],
    'fun': ['🤣', '😁', '🤯', '🎉', '👻'],
    'respect': ['👍', '👌', '🙏', '👏', '💯'],
}

# Pool used by the 🎲 random mode when no custom set was picked.
REACT_POOL: list[str] = ['🔥', '❤', '🎉', '🤩', '👏', '😁', '🥰', '💯', '⚡', '👀', '😍', '🏆', '🙏', '👍', '🤣', '😎']

PROVIDERS: dict[str, dict[str, str]] = {
    'youtube_audio': {'emoji': '🎧', 'label': 'YouTube Audio', 'endpoint': '/play', 'param': 'query'},
    'youtube_video': {'emoji': '🎬', 'label': 'YouTube Video', 'endpoint': '/video', 'param': 'query'},
    'twitter': {'emoji': '𝕏', 'label': 'X / Twitter', 'endpoint': '/twitter', 'param': 'url'},
    'instagram': {'emoji': '📸', 'label': 'Instagram', 'endpoint': '/insta', 'param': 'url'},
    'facebook': {'emoji': '📘', 'label': 'Facebook', 'endpoint': '/facebook', 'param': 'url'},
    'terabox': {'emoji': '📦', 'label': 'TeraBox', 'endpoint': '/terabox', 'param': 'url'},
    'pinterest': {'emoji': '📌', 'label': 'Pinterest', 'endpoint': '/pinterest', 'param': 'url'},
}

HOST_MAP: dict[str, str] = {
    'youtube.com': 'youtube', 'youtu.be': 'youtube', 'www.youtube.com': 'youtube',
    'youtube-nocookie.com': 'youtube', 'm.youtube.com': 'youtube',
    'twitter.com': 'twitter', 'x.com': 'twitter', 'www.twitter.com': 'twitter',
    'www.x.com': 'twitter', 't.co': 'twitter',
    'instagram.com': 'instagram', 'www.instagram.com': 'instagram', 'instagr.am': 'instagram',
    'facebook.com': 'facebook', 'www.facebook.com': 'facebook', 'm.facebook.com': 'facebook',
    'fb.watch': 'facebook', 'fb.me': 'facebook',
    'terabox.com': 'terabox', 'www.terabox.com': 'terabox', '1024terabox.com': 'terabox',
    'teraboxapp.com': 'terabox', '4funbox.com': 'terabox', 'freeterabox.com': 'terabox',
    'pinterest.com': 'pinterest', 'www.pinterest.com': 'pinterest',
    'in.pinterest.com': 'pinterest', 'pin.it': 'pinterest',
}
