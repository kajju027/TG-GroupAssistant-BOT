import random
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.core.config import REACT_POOL

_SC = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
)


def sc(t: str) -> str:
    return t.translate(_SC)


def hdr(title: str) -> str:
    return f"<b>╔══〔 {sc(title)} 〕══╗</b>"


def ftr() -> str:
    return "<b>╚══════════════════════╝</b>"


def sep() -> str:
    return "  <code>━━━━━━━━━━━━━━━━━━━━━</code>"


def row(label: str, value: str, icon: str = "▸") -> str:
    return f"  {icon} <b>{sc(label)}:</b>  {value}"


def box(title: str, lines: list[str]) -> str:
    body = "\n".join(lines)
    return f"{hdr(title)}\n{body}\n{ftr()}"


def bold(t: str) -> str:
    return f"<b>{t}</b>"


def mono(t: str) -> str:
    return f"<code>{t}</code>"


def link(name: str, uid: int) -> str:
    return f'<a href="tg://user?id={uid}">{name}</a>'


def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def ubtn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def rand_emoji() -> str:
    return random.choice(REACT_POOL)


def status_icon(on: bool) -> str:
    return "✅" if on else "❌"
