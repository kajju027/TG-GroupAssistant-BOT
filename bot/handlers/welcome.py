from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from bot.database import get_settings, update_setting
from bot.utils.helpers import mention_by_name
router = Router()

def _format_msg(template: str, user, chat) -> str:
    count = chat.member_count if hasattr(chat, 'member_count') else '?'
    mention = mention_by_name(user.id, user.full_name)
    return template.replace('{mention}', mention).replace('{name}', user.full_name).replace('{username}', f'@{user.username}' if user.username else user.full_name).replace('{group}', chat.title).replace('{count}', str(count)).replace('{id}', str(user.id))

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated):
    s = await get_settings(event.chat.id)
    if not s['welcome']:
        return
    user = event.new_chat_member.user
    chat = event.chat
    text = _format_msg(s['welcome_msg'], user, chat)
    await event.bot.send_message(event.chat.id, f'🎉 <b>New Member!</b>\n\n{text}')

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_leave(event: ChatMemberUpdated):
    s = await get_settings(event.chat.id)
    if not s['goodbye']:
        return
    user = event.old_chat_member.user
    chat = event.chat
    text = _format_msg(s['goodbye_msg'], user, chat)
    await event.bot.send_message(event.chat.id, f'👋 <b>Member Left</b>\n\n{text}')

@router.message(Command('welcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_welcome(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = '✅ ON' if s['welcome'] else '❌ OFF'
        await message.answer(f'👋 <b>Welcome:</b> {status}\n<b>Message:</b>\n<code>{s['welcome_msg']}</code>\n\n<b>Usage:</b> /welcome on|off')
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'welcome', True)
        await message.answer('✅ <b>Welcome messages enabled.</b>')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'welcome', False)
        await message.answer('❌ <b>Welcome messages disabled.</b>')

@router.message(Command('goodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_goodbye(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = '✅ ON' if s['goodbye'] else '❌ OFF'
        await message.answer(f'👋 <b>Goodbye:</b> {status}\n<b>Message:</b>\n<code>{s['goodbye_msg']}</code>\n\n<b>Usage:</b> /goodbye on|off')
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'goodbye', True)
        await message.answer('✅ <b>Goodbye messages enabled.</b>')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'goodbye', False)
        await message.answer('❌ <b>Goodbye messages disabled.</b>')

@router.message(Command('setwelcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setwelcome(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer('<b>Usage:</b> /setwelcome [text]\n\n<b>Placeholders:</b> {mention} {name} {username} {group} {count} {id}')
        return
    await update_setting(message.chat.id, 'welcome_msg', parts[1])
    await message.answer(f'✅ <b>Welcome message updated:</b>\n\n<code>{parts[1]}</code>')

@router.message(Command('setgoodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setgoodbye(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer('<b>Usage:</b> /setgoodbye [text]\n\n<b>Placeholders:</b> {mention} {name} {username} {group} {count} {id}')
        return
    await update_setting(message.chat.id, 'goodbye_msg', parts[1])
    await message.answer(f'✅ <b>Goodbye message updated:</b>\n\n<code>{parts[1]}</code>')
