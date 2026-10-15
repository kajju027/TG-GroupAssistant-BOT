import random
from html import escape
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.core.config import REACT_POOL
_SC = str.maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 'ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ')

def sc(t: str) -> str:
    return t.translate(_SC)

def hdr(title: str) -> str:
    return f'<b>╔══〔 {sc(title)} 〕══╗</b>'

def ftr(tag: str='') -> str:
    tag_part = f' {sc(tag)}' if tag else ''
    return f'<b>╚═══════════════════╝</b>{tag_part}'

def sep() -> str:
    return '  <code>━━━━━━━━━━━━━━━━━━━━</code>'

def row(label: str, value: str, icon: str='▸') -> str:
    return f'  {icon} <b>{sc(label)}:</b>  {value}'

def box(title: str, lines: list[str], footer_tag: str='') -> str:
    return f'{hdr(title)}\n' + '\n'.join(lines) + f'\n{ftr(footer_tag)}'

def quote(text: str) -> str:
    return f'<blockquote>{text}</blockquote>'

def bold(t: str) -> str:
    return f'<b>{t}</b>'

def mono(t: str) -> str:
    return f'<code>{t}</code>'

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
    return '✅' if on else '❌'

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
