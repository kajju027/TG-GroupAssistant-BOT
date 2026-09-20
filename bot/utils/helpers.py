import re
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
LINK_PATTERN = re.compile('(https?://[^\\s]+|t\\.me/[^\\s]+|telegram\\.me/[^\\s]+|@\\w+)', re.IGNORECASE)

def extract_links(text: str) -> list:
    return LINK_PATTERN.findall(text or '')

def is_telegram_link(text: str) -> bool:
    patterns = ['t\\.me/', 'telegram\\.me/', 'telegram\\.dog/']
    return any((re.search(p, text, re.I) for p in patterns))

def extract_domain(link: str) -> str:
    cleaned = re.sub('^https?://', '', link.strip(), flags=re.I)
    cleaned = re.sub('^www\\.', '', cleaned, flags=re.I)
    return cleaned.split('/')[0].lower()

def is_domain_whitelisted(link: str, whitelist: list) -> bool:
    domain = extract_domain(link)
    return any((domain == w or domain.endswith('.' + w) for w in whitelist))

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
    if message.from_user is not None:
        return await is_admin(message.bot, message.chat.id, message.from_user.id)
    if message.sender_chat is not None and message.sender_chat.id == message.chat.id:
        return True
    return False

def mention_by_name(user_id: int, name: str) -> str:
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    return f"<a href='tg://user?id={user_id}'>{safe_name}</a>"

async def get_user_from_message(message: Message) -> tuple:
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        if u is None:
            return (None, None, None)
        return (u.id, u.full_name, mention_by_name(u.id, u.full_name))
    parts = message.text.split() if message.text else []
    if len(parts) > 1:
        target = parts[1]
        if target.startswith('@'):
            try:
                chat = await message.bot.get_chat(target)
                return (chat.id, chat.full_name, mention_by_name(chat.id, chat.full_name))
            except Exception:
                pass
        elif target.isdigit():
            uid = int(target)
            try:
                chat = await message.bot.get_chat(uid)
                return (chat.id, chat.full_name, mention_by_name(uid, chat.full_name))
            except Exception:
                return (uid, str(uid), mention_by_name(uid, str(uid)))
    return (None, None, None)

def groups_picker_kb(chats: list) -> InlineKeyboardMarkup:
    rows = []
    for chat in chats:
        icon = '📢' if chat['type'] == 'channel' else '👥'
        title = chat['title']
        chat_id = chat['chat_id']
        rows.append([InlineKeyboardButton(text=f'{icon} {title}', callback_data=f'panel:open:{chat_id}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def settings_main_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔗 Anti-Link', callback_data=f'menu:antilink:{chat_id}'), InlineKeyboardButton(text='🔤 Anti-Word', callback_data=f'menu:antiword:{chat_id}')], [InlineKeyboardButton(text='🚫 Anti-Spam', callback_data=f'menu:antispam:{chat_id}'), InlineKeyboardButton(text='📵 Anti-Fake', callback_data=f'menu:antifake:{chat_id}')], [InlineKeyboardButton(text='👋 Welcome / Goodbye', callback_data=f'menu:welcome:{chat_id}'), InlineKeyboardButton(text='⚠️ Warnings', callback_data=f'menu:warn:{chat_id}')], [InlineKeyboardButton(text='🔇 Mute', callback_data=f'menu:mute:{chat_id}'), InlineKeyboardButton(text='🔍 Filters', callback_data=f'menu:filters:{chat_id}')], [InlineKeyboardButton(text='🎭 Auto-Reaction', callback_data=f'menu:reaction:{chat_id}')], [InlineKeyboardButton(text='🔙 My Groups', callback_data='panel:list'), InlineKeyboardButton(text='❌ Close', callback_data='close')]])

def back_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
