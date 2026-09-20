import logging
import sys
from datetime import datetime

class Colors:
    RESET = '\x1b[0m'
    BOLD = '\x1b[1m'
    DIM = '\x1b[2m'
    RED = '\x1b[38;5;203m'
    GREEN = '\x1b[38;5;84m'
    YELLOW = '\x1b[38;5;220m'
    BLUE = '\x1b[38;5;39m'
    MAGENTA = '\x1b[38;5;177m'
    CYAN = '\x1b[38;5;51m'
    ORANGE = '\x1b[38;5;208m'
    GREY = '\x1b[38;5;245m'
    WHITE = '\x1b[38;5;255m'
LEVEL_STYLE = {'DEBUG': (Colors.GREY, '🔍 DEBUG'), 'INFO': (Colors.CYAN, 'ℹ️  INFO '), 'SUCCESS': (Colors.GREEN, '✅ OK   '), 'WARNING': (Colors.YELLOW, '⚠️  WARN '), 'ERROR': (Colors.RED, '❌ ERROR'), 'CRITICAL': (Colors.RED + Colors.BOLD, '🔥 FATAL')}

def _supports_color() -> bool:
    import os
    if os.getenv('NO_COLOR'):
        return False
    return True
COLOR_ENABLED = _supports_color()

def _c(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f'{color}{text}{Colors.RESET}'

def _timestamp() -> str:
    return datetime.now().strftime('%H:%M:%S')

def _emit(level: str, tag: str, message: str):
    color, label = LEVEL_STYLE.get(level, (Colors.WHITE, level))
    ts = _c(f'[{_timestamp()}]', Colors.GREY)
    lvl = _c(label, color)
    tagged = _c(f'[{tag}]', Colors.MAGENTA + Colors.BOLD) if tag else ''
    print(f'{ts} {lvl} {tagged} {message}')
    sys.stdout.flush()

class BotLogger:

    def __init__(self, tag: str='BOT'):
        self.tag = tag

    def debug(self, message: str):
        _emit('DEBUG', self.tag, message)

    def info(self, message: str):
        _emit('INFO', self.tag, message)

    def success(self, message: str):
        _emit('SUCCESS', self.tag, message)

    def warn(self, message: str):
        _emit('WARNING', self.tag, message)

    def error(self, message: str):
        _emit('ERROR', self.tag, message)

    def critical(self, message: str):
        _emit('CRITICAL', self.tag, message)

    def banner(self, lines):
        width = max((len(_strip_ansi(line)) for line in lines)) + 4
        top = _c('╔' + '═' * width + '╗', Colors.CYAN)
        bottom = _c('╚' + '═' * width + '╝', Colors.CYAN)
        print(top)
        for line in lines:
            pad = width - len(_strip_ansi(line))
            print(_c('║ ', Colors.CYAN) + line + ' ' * (pad - 1) + _c('║', Colors.CYAN))
        print(bottom)
        sys.stdout.flush()

    def section(self, title: str):
        bar = '─' * 10
        print(_c(f'\n{bar} {title} {bar}', Colors.BLUE + Colors.BOLD))
        sys.stdout.flush()

def _strip_ansi(text: str) -> str:
    import re
    return re.sub('\\033\\[[0-9;]*m', '', text)

def get_logger(tag: str='BOT') -> BotLogger:
    return BotLogger(tag)

def quiet_third_party_loggers():
    for name in ('aiogram', 'aiogram.event', 'aiogram.dispatcher', 'asyncio'):
        logging.getLogger(name).setLevel(logging.WARNING)
