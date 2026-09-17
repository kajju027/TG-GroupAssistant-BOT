"""
Central configuration for the bot. Reads everything from environment
variables so the SAME code works whether it's run locally with a .env
file or downloaded fresh by index.py on a hosting panel.
"""

import os
import sys

from bot.core.logger import get_logger

log = get_logger("CONFIG")


def _get_int_env(name: str, default: int = 0) -> int:
    """Safely read an int env var. Many hosting panels set an EMPTY
    STRING instead of omitting the variable entirely, which would
    crash a plain int(os.getenv(...)) call. Falls back to `default`
    for missing/empty/invalid values instead of crashing."""
    raw = os.getenv(name, "")
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log.warn(f"Invalid value for {name}={raw!r}, using default {default}.")
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = _get_int_env("OWNER_ID", 0)
DB_PATH = os.getenv("DB_PATH", "bot.db").strip() or "bot.db"

# GitHub source info (used by index.py, kept here too so any handler
# that wants to display "running from commit X" can read it).
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"


def validate():
    """Called once from index.py right after the code is downloaded
    and before the bot actually starts polling. Fails loudly and
    clearly instead of letting aiogram raise a confusing error deep
    inside its own internals."""
    if not BOT_TOKEN or BOT_TOKEN.upper() in {"YOUR_BOT_TOKEN_HERE", "YOUR_BOT_TOKEN_FROM_BOTFATHER"}:
        log.critical("BOT_TOKEN is missing or not set.")
        log.info("Set it in your hosting panel's Environment Variables (or in a local .env file).")
        log.info("Get a token from @BotFather on Telegram.")
        sys.exit(1)

    if OWNER_ID == 0:
        log.warn("OWNER_ID is not set (or is 0). Owner-only commands will not work for anyone.")
        log.warn("Set OWNER_ID to your numeric Telegram user ID (get it from @userinfobot).")
