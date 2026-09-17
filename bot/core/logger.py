"""
Colorful console logger, Levanter-style.

Works on any hosting panel console that supports ANSI escape codes
(which is nearly all of them - Pterodactyl-based panels, Heroku,
Railway, Render, VPS terminals, etc). If the console does NOT support
color (rare), the codes just show as harmless characters and the text
is still fully readable.
"""

import logging
import sys
from datetime import datetime


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[38;5;203m"
    GREEN = "\033[38;5;84m"
    YELLOW = "\033[38;5;220m"
    BLUE = "\033[38;5;39m"
    MAGENTA = "\033[38;5;177m"
    CYAN = "\033[38;5;51m"
    ORANGE = "\033[38;5;208m"
    GREY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"


LEVEL_STYLE = {
    "DEBUG": (Colors.GREY, "🔍 DEBUG"),
    "INFO": (Colors.CYAN, "ℹ️  INFO "),
    "SUCCESS": (Colors.GREEN, "✅ OK   "),
    "WARNING": (Colors.YELLOW, "⚠️  WARN "),
    "ERROR": (Colors.RED, "❌ ERROR"),
    "CRITICAL": (Colors.RED + Colors.BOLD, "🔥 FATAL"),
}


def _supports_color() -> bool:
    # Most hosting panels (Pterodactyl/wings-based consoles included)
    # render ANSI fine even when stdout isn't a real TTY, so we default
    # to True unless explicitly disabled via NO_COLOR (a common convention).
    import os
    if os.getenv("NO_COLOR"):
        return False
    return True


COLOR_ENABLED = _supports_color()


def _c(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{color}{text}{Colors.RESET}"


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _emit(level: str, tag: str, message: str):
    color, label = LEVEL_STYLE.get(level, (Colors.WHITE, level))
    ts = _c(f"[{_timestamp()}]", Colors.GREY)
    lvl = _c(label, color)
    tagged = _c(f"[{tag}]", Colors.MAGENTA + Colors.BOLD) if tag else ""
    print(f"{ts} {lvl} {tagged} {message}")
    sys.stdout.flush()


class BotLogger:
    """Small convenience wrapper so handlers can do `log.info(...)`,
    `log.success(...)`, `log.warn(...)`, `log.error(...)` with a tag
    that identifies which module logged it (e.g. 'ANTISPAM', 'CORE')."""

    def __init__(self, tag: str = "BOT"):
        self.tag = tag

    def debug(self, message: str):
        _emit("DEBUG", self.tag, message)

    def info(self, message: str):
        _emit("INFO", self.tag, message)

    def success(self, message: str):
        _emit("SUCCESS", self.tag, message)

    def warn(self, message: str):
        _emit("WARNING", self.tag, message)

    def error(self, message: str):
        _emit("ERROR", self.tag, message)

    def critical(self, message: str):
        _emit("CRITICAL", self.tag, message)

    def banner(self, lines):
        """Print a boxed banner - used for the big startup logo/status block."""
        width = max(len(_strip_ansi(line)) for line in lines) + 4
        top = _c("╔" + "═" * width + "╗", Colors.CYAN)
        bottom = _c("╚" + "═" * width + "╝", Colors.CYAN)
        print(top)
        for line in lines:
            pad = width - len(_strip_ansi(line))
            print(_c("║ ", Colors.CYAN) + line + " " * (pad - 1) + _c("║", Colors.CYAN))
        print(bottom)
        sys.stdout.flush()

    def section(self, title: str):
        bar = "─" * 10
        print(_c(f"\n{bar} {title} {bar}", Colors.BLUE + Colors.BOLD))
        sys.stdout.flush()


def _strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


def get_logger(tag: str = "BOT") -> BotLogger:
    return BotLogger(tag)


# Silence aiogram's / asyncio's very verbose default INFO logs; we do
# our own pretty logging instead. Real errors still show (level ERROR+).
def quiet_third_party_loggers():
    for name in ("aiogram", "aiogram.event", "aiogram.dispatcher", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)
