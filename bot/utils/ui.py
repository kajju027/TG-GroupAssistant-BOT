from __future__ import annotations

import random

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.core.config import REACT_POOL
from bot.utils.style import to_small_caps


def sc(t: str) -> str:
    """Small caps with a twist: the first letter of every word stays a normal
    capital letter and the rest of the word becomes small caps.

    "Tagging Everyone" -> "Tᴀɢɢɪɴɢ Eᴠᴇʀʏᴏɴᴇ"
    """
    return to_small_caps(t)


DIVIDER = '<code>───────────────</code>'


def hdr(title: str, icon: str = '✦') -> str:
    return f'{icon} <b>{sc(title)}</b>'


def ftr(tag: str = '') -> str:
    return f'<i>{sc(tag)}</i>' if tag else ''


def sep() -> str:
    return DIVIDER


def row(label: str, value: str, icon: str = '') -> str:
    """One clean settings line: `Label · value`. The legacy `icon` argument is
    accepted so old call sites keep working, but it is no longer rendered."""
    return f'<b>{sc(label)}</b> · {value}'


def box(title: str, lines: list, footer_tag: str = '', icon: str = '✦') -> str:
    """Build a clean panel: title, thin divider, body lines, optional footer."""
    body = [line for line in lines if line is not None and line != '']
    parts = [hdr(title, icon), DIVIDER, *body]
    footer = ftr(footer_tag)
    if footer:
        parts += [DIVIDER, footer]
    return '\n'.join(parts)


def quote(text: str) -> str:
    return f'<blockquote>{text}</blockquote>'


def quote_expandable(text: str) -> str:
    """A collapsed-by-default blockquote (Telegram native)."""
    return f'<blockquote expandable>{text}</blockquote>'


def bold(t: str) -> str:
    return f'<b>{t}</b>'


def mono(t: str) -> str:
    return f'<code>{escape(str(t))}</code>'


def italic(t: str) -> str:
    return f'<i>{t}</i>'


def link(name: str, uid: int) -> str:
    return f'<a href="tg://user?id={int(uid)}">{escape(name)}</a>'


def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def ubtn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def rand_emoji() -> str:
    return random.choice(REACT_POOL)


def status_icon(on: bool) -> str:
    return '🟢' if on else '🔴'


def status_text(on: bool) -> str:
    """Coloured status used in both messages and button labels."""
    return f'{status_icon(on)} {sc("On") if on else sc("Off")}'


def toggle_btn(label: str, state: bool, feature: str, chat_id: int) -> InlineKeyboardButton:
    """Inline toggle button with colour indication (green on / red off)."""
    action = 'off' if state else 'on'
    return InlineKeyboardButton(
        text=f"{status_icon(state)} {label} · {'ON' if state else 'OFF'}",
        callback_data=f'toggle:{feature}:{chat_id}:{action}',
    )


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
