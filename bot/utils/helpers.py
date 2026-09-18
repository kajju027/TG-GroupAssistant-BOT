import re
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMember, Message, InlineKeyboardMarkup, InlineKeyboardButton

LINK_PATTERN = re.compile(
    r"(https?://[^\s]+|t\.me/[^\s]+|telegram\.me/[^\s]+|@\w+)",
    re.IGNORECASE
)

def extract_links(text: str) -> list:
    return LINK_PATTERN.findall(text or "")

def is_telegram_link(text: str) -> bool:
    patterns = [r"t\.me/", r"telegram\.me/", r"telegram\.dog/"]
    return any(re.search(p, text, re.I) for p in patterns)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    if user_id is None:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except Exception:
        return False

async def is_creator(bot: Bot, chat_id: int, user_id: int) -> bool:
    if user_id is None:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.CREATOR
    except Exception:
        return False

async def is_message_sender_admin(message: Message) -> bool:
    """True if the person/entity that SENT `message` is an admin.

    Handles the normal case (message.from_user is a real user) and the
    anonymous-admin / linked-channel case (message.from_user is None and
    message.sender_chat is set instead) without raising when neither is
    present.
    """
    if message.from_user is not None:
        return await is_admin(message.bot, message.chat.id, message.from_user.id)
    if message.sender_chat is not None and message.sender_chat.id == message.chat.id:
        # Only an admin can post a message "as the group" (anonymous admin).
        return True
    return False

async def get_user_from_message(message: Message) -> tuple:
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return u.id, u.full_name, u.mention_html()
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        target = parts[1]
        if target.startswith("@"):
            try:
                chat = await message.bot.get_chat(target)
                return chat.id, chat.full_name, f"<a href='tg://user?id={chat.id}'>{chat.full_name}</a>"
            except Exception:
                pass
        elif target.isdigit():
            uid = int(target)
            try:
                chat = await message.bot.get_chat(uid)
                return chat.id, chat.full_name, f"<a href='tg://user?id={uid}'>{chat.full_name}</a>"
            except Exception:
                return uid, str(uid), f"<a href='tg://user?id={uid}'>{uid}</a>"
    return None, None, None

def on_off_kb(feature: str, state: bool, chat_id: int) -> InlineKeyboardMarkup:
    btn = InlineKeyboardButton(
        text="✅ ON" if state else "❌ OFF",
        callback_data=f"toggle:{feature}:{chat_id}:{'off' if state else 'on'}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])

def settings_main_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Anti-Link", callback_data=f"menu:antilink:{chat_id}"),
            InlineKeyboardButton(text="🔤 Anti-Word", callback_data=f"menu:antiword:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="🚫 Anti-Spam", callback_data=f"menu:antispam:{chat_id}"),
            InlineKeyboardButton(text="📵 Anti-Fake", callback_data=f"menu:antifake:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="👋 Welcome", callback_data=f"menu:welcome:{chat_id}"),
            InlineKeyboardButton(text="⚠️ Warn", callback_data=f"menu:warn:{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="🔇 Mute", callback_data=f"menu:mute:{chat_id}"),
            InlineKeyboardButton(text="🔍 Filters", callback_data=f"menu:filters:{chat_id}"),
        ],
        [InlineKeyboardButton(text="🎭 Auto-Reaction", callback_data=f"menu:reaction:{chat_id}")],
        [InlineKeyboardButton(text="❌ Close", callback_data="close")],
    ])

def back_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")]
    ])
