from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.utils.helpers import mention_by_name
router = Router()

@router.message(Command('tag'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_tag(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=2)
    mode = parts[1].lower() if len(parts) > 1 else 'all'
    custom_msg = parts[2] if len(parts) > 2 else ''
    try:
        members = await message.bot.get_chat_administrators(message.chat.id)
    except Exception as e:
        await message.answer(f'❌ Failed to fetch members: {e}')
        return
    if mode == 'admin':
        targets = [m.user for m in members if not m.user.is_bot]
        label = '👑 <b>Admins</b>'
    elif mode == 'notadmin':
        await message.answer("⚠️ Tagging all non-admins isn't supported by the Telegram API (it can only list admins). Use /tag all or /tag admin instead.")
        return
    else:
        targets = [m.user for m in members if not m.user.is_bot]
        label = '📢 <b>All Members</b>'
    if not targets:
        await message.answer('No members found to tag.')
        return
    mentions = ', '.join((mention_by_name(u.id, u.full_name) for u in targets))
    text = f'{label}\n{custom_msg}\n\n{mentions}' if custom_msg else f'{label}\n\n{mentions}'
    await message.answer(text)
