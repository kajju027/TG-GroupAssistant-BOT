from __future__ import annotations

import datetime
import re

from html import escape

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, Message

LINK_PATTERN = re.compile('(https?://[^\\s]+|t\\.me/[^\\s]+|telegram\\.me/[^\\s]+|@\\w+)', re.IGNORECASE)

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
_ADMIN_TTL = 120.0
_admin_cache: dict[tuple[int, int], tuple[float, bool]] = {}
_bot_admin_cache: dict[int, tuple[float, bool]] = {}
_bot_id_cache: dict[int, int] = {}


# -------------------------------------------------------------- caches -----
def _cache_fresh(cache: dict, key, ttl: float):
    item = cache.get(key)
    if item and (datetime.datetime.now().timestamp() - item[0]) < ttl:
        return item[1]
    return None


def clear_admin_cache(chat_id: int | None = None, user_id: int | None = None) -> None:
    """Drop cached admin answers (after promote/demote for example)."""
    if chat_id is None and user_id is None:
        _admin_cache.clear()
        _bot_admin_cache.clear()
        return
    if user_id is None:
        for key in [k for k in _admin_cache if k[0] == chat_id]:
            _admin_cache.pop(key, None)
        _bot_admin_cache.pop(chat_id, None)
    else:
        _admin_cache.pop((chat_id, user_id), None)


async def get_bot_id(bot: Bot) -> int:
    try:
        if bot.id:
            return int(bot.id)
    except Exception:
        pass
    try:
        me = await bot.me()
    except Exception:
        try:
            me = await bot.get_me()
        except Exception:
            return 0
    return me.id


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Admin check with a 120s cache — keeps button taps instant."""
    if user_id is None:
        return False
    key = (chat_id, user_id)
    cached = _cache_fresh(_admin_cache, key, _ADMIN_TTL)
    if cached is not None:
        return cached
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        result = member.status in _ADMIN_STATUSES
    except Exception:
        result = False
    _admin_cache[key] = (datetime.datetime.now().timestamp(), result)
    return result


async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    cached = _cache_fresh(_bot_admin_cache, chat_id, _ADMIN_TTL)
    if cached is not None:
        return cached
    bot_id = await get_bot_id(bot)
    if not bot_id:
        return False
    try:
        member = await bot.get_chat_member(chat_id, bot_id)
        result = member.status in _ADMIN_STATUSES
    except Exception:
        result = False
    _bot_admin_cache[chat_id] = (datetime.datetime.now().timestamp(), result)
    return result


async def is_creator(bot: Bot, chat_id: int, user_id: int) -> bool:
    if user_id is None:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.CREATOR
    except Exception:
        return False


async def is_message_sender_admin(message: Message) -> bool:
    """Channel-post / anonymous-admin aware sender check."""
    if message.from_user is not None:
        return await is_admin(message.bot, message.chat.id, message.from_user.id)
    if message.sender_chat is not None and message.sender_chat.id == message.chat.id:
        return True
    return False


# ---------------------------------------------------------------- text -----
def extract_links(text: str) -> list:
    return LINK_PATTERN.findall(text or '')


def extract_domain(link: str) -> str:
    cleaned = re.sub('^https?://', '', link.strip(), flags=re.I)
    cleaned = re.sub('^www\\.', '', cleaned, flags=re.I)
    return cleaned.split('/')[0].lower()


def is_domain_whitelisted(link: str, whitelist: list) -> bool:
    domain = extract_domain(link)
    return any((domain == w or domain.endswith('.' + w) for w in whitelist))


def mention_by_name(user_id: int, name: str) -> str:
    safe_name = escape(str(name)).replace('<', '&lt;').replace('>', '&gt;')
    return f"<a href='tg://user?id={user_id}'>{safe_name}</a>"


# ---------------------------------------------------------------- users ----
async def get_user_from_message(message: Message) -> tuple:
    """Resolve the target user: reply » @username » numeric id."""
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return (u.id, u.full_name, mention_by_name(u.id, u.full_name))
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        target = parts[1]
        if target.startswith('@'):
            try:
                chat = await message.bot.get_chat(target)
                return (chat.id, getattr(chat, 'full_name', target), mention_by_name(chat.id, getattr(chat, 'full_name', target)))
            except Exception:
                return (None, None, None)
        if target.lstrip('-').isdigit():
            uid = int(target)
            try:
                chat = await message.bot.get_chat(uid)
                name = getattr(chat, 'full_name', None) or str(uid)
                return (chat.id, name, mention_by_name(uid, name))
            except Exception:
                return (uid, str(uid), mention_by_name(uid, str(uid)))
    return (None, None, None)


def parse_duration(value: str):
    """'10m', '2h', '1d' → timedelta."""
    match = re.fullmatch(r'(\d{1,4})([smhd])', (value or '').strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0 or amount > 366:
        return None
    table = {
        's': datetime.timedelta(seconds=amount),
        'm': datetime.timedelta(minutes=amount),
        'h': datetime.timedelta(hours=amount),
        'd': datetime.timedelta(days=amount),
    }
    return table[match.group(2)]


def find_duration(parts, start: int = 1):
    for part in parts[start:]:
        parsed = parse_duration(part)
        if parsed is not None:
            return parsed, part
    return None, None


def future(delta) -> datetime.datetime | None:
    if delta is None:
        return None
    return datetime.datetime.now(datetime.timezone.utc) + delta


# ------------------------------------------------------------ permissions --
MUTE_PERMS_OFF = ChatPermissions(
    can_send_messages=False, can_send_audios=False, can_send_documents=False,
    can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
    can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
    can_add_web_page_previews=False, can_change_info=False, can_invite_users=False,
    can_pin_messages=False,
)

DEFAULT_MEMBER_PERMS = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True,
    can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
    can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
    can_add_web_page_previews=True, can_change_info=False, can_invite_users=True,
    can_pin_messages=False,
)


# --------------------------------------------------------------- editing ---
async def safe_edit(message, text: str, reply_markup: InlineKeyboardMarkup | None = None, **kwargs) -> bool:
    """edit_text that swallows 'message is not modified' and gone messages."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
        return True
    except TelegramBadRequest as error:
        if 'message is not modified' in str(error).casefold():
            return True
        if 'message to edit not found' in str(error).casefold():
            return True
        return False
    except Exception:
        return False


async def get_bot_username(bot: Bot) -> str | None:
    try:
        me = await bot.me()
        return me.username
    except Exception:
        try:
            me = await bot.get_me()
            return me.username
        except Exception:
            return None
