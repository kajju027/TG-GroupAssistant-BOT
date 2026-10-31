from __future__ import annotations

import random

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils.style import to_small_caps

BUTTON_TEXT_LIMIT = 34

# One short, subtle divider — used sparingly on purpose.
DIVIDER = '<code>────────</code>'


def sc(t: str) -> str:
    """Small caps: the first letter of every word stays a normal capital,
    the rest becomes small caps. "Tagging Everyone" → "Tᴀɢɢɪɴɢ Eᴠᴇʀʏᴏɴᴇ"."""
    return to_small_caps(t)


def hdr(title: str, icon: str = '✦') -> str:
    return f'{icon} <b>{sc(title)}</b>'


def sep() -> str:
    return DIVIDER


def row(label: str, value: str, icon: str = '') -> str:
    """One clean settings line: `Label · value`."""
    return f'<b>{sc(label)}</b> · {value}'


def box(title: str, lines: list, icon: str = '✦') -> str:
    """Clean panel: bold small-caps title, one thin divider, body lines."""
    body = [line for line in lines if line is not None and line != '']
    return '\n'.join([hdr(title, icon), DIVIDER, *body])


def quote(text: str) -> str:
    return f'<blockquote>{text}</blockquote>'


def quote_expandable(text: str) -> str:
    """Collapsed-by-default blockquote (Telegram native)."""
    return f'<blockquote expandable>{text}</blockquote>'


def bold(t: str) -> str:
    return f'<b>{t}</b>'


def mono(t: str) -> str:
    return f'<code>{escape(str(t))}</code>'


def italic(t: str) -> str:
    return f'<i>{t}</i>'


def link(name: str, uid: int) -> str:
    return f'<a href="tg://user?id={int(uid)}">{escape(name)}</a>'


# ------------------------------------------------------------- buttons -----
def btn(text: str, data: str) -> InlineKeyboardButton:
    """Styled button: small caps, trimmed length — used everywhere so no
    button ever ships with a normal font or a bloated label."""
    label = to_small_caps(str(text))
    if len(label) > BUTTON_TEXT_LIMIT:
        label = label[:BUTTON_TEXT_LIMIT - 1].rstrip() + '…'
    return InlineKeyboardButton(text=label, callback_data=data)


def ubtn(text: str, url: str) -> InlineKeyboardButton:
    label = to_small_caps(str(text))
    if len(label) > BUTTON_TEXT_LIMIT:
        label = label[:BUTTON_TEXT_LIMIT - 1].rstrip() + '…'
    return InlineKeyboardButton(text=label, url=url)


def dot(state: bool) -> str:
    """Colour indicator: green = on, red = off."""
    return '🟢' if state else '🔴'


def status_text(on: bool) -> str:
    return f'{dot(on)} <b>{sc("On") if on else sc("Off")}</b>'


def tbtn(label: str, state: bool, data: str) -> InlineKeyboardButton:
    """Toggle button with colour indication: 🟢 Welcome · On"""
    text = f"{dot(state)} {sc(label)} · {sc('On') if state else sc('Off')}"
    return InlineKeyboardButton(text=text, callback_data=data)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def back_kb(data: str, extra: InlineKeyboardButton | None = None) -> InlineKeyboardMarkup:
    if extra is not None:
        return kb([extra, btn('🔙 Back', data)])
    return kb([btn('🔙 Back', data)])


def status_icon(on: bool) -> str:
    return '🟢' if on else '🔴'


def rand_emoji(pool: list[str] | None = None) -> str:
    from bot.core.config import REACT_POOL

    return random.choice(pool or REACT_POOL)


def progress_bar(current: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return '░' * width
    filled = max(0, min(width, round(width * current / total)))
    return '▓' * filled + '░' * (width - filled)


def fmt_size(b: int) -> str:
    if b < 1024:
        return f'{b} B'
    if b < 1024 ** 2:
        return f'{b / 1024:.1f} KB'
    return f'{b / 1024 / 1024:.1f} MB'


def fmt_dur(s) -> str:
    if s is None:
        return sc('N/A')
    s = int(s)
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f'{h}:{m:02d}:{sec:02d}'
    return f'{m}:{sec:02d}'


def fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, _ = divmod(seconds, 60)
    if d:
        return f'{d}ᴅ {h}ʜ {m}ᴍ'
    if h:
        return f'{h}ʜ {m}ᴍ'
    return f'{m}ᴍ'
