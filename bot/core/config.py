import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str        = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID: int         = int(os.getenv("OWNER_ID", "0"))
TG_API_PROXY: str     = os.getenv("TG_API_PROXY", "").strip().rstrip("/")
API_BASE_URL: str     = os.getenv("API_BASE_URL", "https://api.sayan-nexuswork.workers.dev").rstrip("/")
DATABASE_PATH: Path   = Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3"))
LOG_LEVEL: str        = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_WARNS: int        = int(os.getenv("MAX_WARNS", "3"))
MAX_DL_MB: int        = int(os.getenv("MAX_DOWNLOAD_MB", "50"))

FIRE_FX      = "5104841245755180586"
CONFETTI_FX  = "5046509860389126442"
HEART_FX     = "5159385139981059251"
THUMBSUP_FX  = "5046589136895476101"

REACT_POOL = [
    "🔥","❤️","👏","🎉","🤩","💯","⚡","🏆","👍","🎊",
    "🥳","💫","✨","🌟","🎯","💥","🎸","🎶","🌈","👑",
]

PROVIDERS: dict = {
    "youtube_audio": {"emoji": "🎧", "label": "YouTube Audio", "endpoint": "/play",      "param": "query"},
    "youtube_video": {"emoji": "🎬", "label": "YouTube Video", "endpoint": "/video",     "param": "query"},
    "twitter":       {"emoji": "𝕏",  "label": "X / Twitter",  "endpoint": "/twitter",   "param": "url"},
    "instagram":     {"emoji": "📸", "label": "Instagram",     "endpoint": "/insta",     "param": "url"},
    "facebook":      {"emoji": "📘", "label": "Facebook",      "endpoint": "/facebook",  "param": "url"},
    "terabox":       {"emoji": "📦", "label": "TeraBox",       "endpoint": "/terabox",   "param": "url"},
    "pinterest":     {"emoji": "📌", "label": "Pinterest",     "endpoint": "/pinterest", "param": "url"},
}

HOST_MAP: dict = {
    "youtube.com": "youtube",         "youtu.be": "youtube",
    "www.youtube.com": "youtube",     "youtube-nocookie.com": "youtube",
    "m.youtube.com": "youtube",
    "twitter.com": "twitter",         "x.com": "twitter",
    "www.twitter.com": "twitter",     "www.x.com": "twitter",
    "t.co": "twitter",
    "instagram.com": "instagram",     "www.instagram.com": "instagram",
    "instagr.am": "instagram",
    "facebook.com": "facebook",       "www.facebook.com": "facebook",
    "m.facebook.com": "facebook",     "fb.watch": "facebook",
    "fb.me": "facebook",
    "terabox.com": "terabox",         "www.terabox.com": "terabox",
    "1024terabox.com": "terabox",     "teraboxapp.com": "terabox",
    "4funbox.com": "terabox",         "freeterabox.com": "terabox",
    "pinterest.com": "pinterest",     "www.pinterest.com": "pinterest",
    "in.pinterest.com": "pinterest",  "pin.it": "pinterest",
}
