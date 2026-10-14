import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
TG_API_PROXY: str = os.getenv("TG_API_PROXY", "").strip().rstrip("/")
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.sayan-nexuswork.workers.dev").rstrip("/")
DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_WARNS: int = int(os.getenv("MAX_WARNS", "3"))

REACT_POOL = ["🔥", "❤️", "👏", "🎉", "🤩", "💯", "⚡", "🏆", "👍", "🎊", "🥳", "💫", "✨", "🌟", "🎯", "💥"]
