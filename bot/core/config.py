from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')

def _env_int(name: str, default: int, *, minimum: int | None=None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value) if minimum is not None else value

def _env_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else BASE_DIR / value
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
OWNER_ID = _env_int('OWNER_ID', 0, minimum=0)
TG_API_PROXY = os.getenv('TG_API_PROXY', '').strip()
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.sayan-nexuswork.workers.dev').strip().rstrip('/')
DATA_DIR = _env_path('DATA_DIR', 'data')
DATABASE_PATH = _env_path('DATABASE_PATH', 'data/bot.sqlite3')
CHATS_DIR = _env_path('CHATS_DIR', 'data/chats')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
MAX_WARNS = _env_int('MAX_WARNS', 3, minimum=1)
MAX_DL_MB = _env_int('MAX_DOWNLOAD_MB', 50, minimum=1)
FIRE_FX = '5104841245755180586'
CONFETTI_FX = '5046509860389126442'
HEART_FX = '5159385139981059251'
THUMBSUP_FX = '5046589136895476101'
REACT_POOL = ['🔥', '❤️', '👏', '🎉', '🤩', '💯', '⚡', '🏆', '👍', '🎊', '🥳', '💫', '✨', '🌟', '🎯', '💥', '🎸', '🎶', '🌈', '👑']
PROVIDERS: dict[str, dict[str, str]] = {'youtube_audio': {'emoji': '🎧', 'label': 'YouTube Audio', 'endpoint': '/play', 'param': 'query'}, 'youtube_video': {'emoji': '🎬', 'label': 'YouTube Video', 'endpoint': '/video', 'param': 'query'}, 'twitter': {'emoji': '𝕏', 'label': 'X / Twitter', 'endpoint': '/twitter', 'param': 'url'}, 'instagram': {'emoji': '📸', 'label': 'Instagram', 'endpoint': '/insta', 'param': 'url'}, 'facebook': {'emoji': '📘', 'label': 'Facebook', 'endpoint': '/facebook', 'param': 'url'}, 'terabox': {'emoji': '📦', 'label': 'TeraBox', 'endpoint': '/terabox', 'param': 'url'}, 'pinterest': {'emoji': '📌', 'label': 'Pinterest', 'endpoint': '/pinterest', 'param': 'url'}}
HOST_MAP: dict[str, str] = {'youtube.com': 'youtube', 'youtu.be': 'youtube', 'www.youtube.com': 'youtube', 'youtube-nocookie.com': 'youtube', 'm.youtube.com': 'youtube', 'twitter.com': 'twitter', 'x.com': 'twitter', 'www.twitter.com': 'twitter', 'www.x.com': 'twitter', 't.co': 'twitter', 'instagram.com': 'instagram', 'www.instagram.com': 'instagram', 'instagr.am': 'instagram', 'facebook.com': 'facebook', 'www.facebook.com': 'facebook', 'm.facebook.com': 'facebook', 'fb.watch': 'facebook', 'fb.me': 'facebook', 'terabox.com': 'terabox', 'www.terabox.com': 'terabox', '1024terabox.com': 'terabox', 'teraboxapp.com': 'terabox', '4funbox.com': 'terabox', 'freeterabox.com': 'terabox', 'pinterest.com': 'pinterest', 'www.pinterest.com': 'pinterest', 'in.pinterest.com': 'pinterest', 'pin.it': 'pinterest'}
