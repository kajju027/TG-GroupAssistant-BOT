from __future__ import annotations
from html import escape
from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import ChatMemberUpdated, Message
from bot.database import get_settings, update_setting
from bot.utils.helpers import mention_by_name
router = Router()

def _format_msg(template: str, user, chat) -> str:
    values = {'{mention}': mention_by_name(user.id, user.full_name), '{name}': escape(user.full_name), '{username}': '@' + escape(user.username) if user.username else escape(user.full_name), '{group}': escape(chat.title or 'this group'), '{count}': '?', '{id}': str(user.id)}
    for placeholder, value in values.items():
        template = template.replace(placeholder, value)
    return template

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        raise SkipHandler
    settings = await get_settings(event.chat.id)
    if settings['welcome']:
        text = _format_msg(settings['welcome_msg'], user, event.chat)
        await event.bot.send_message(event.chat.id, f'🎉 <b>New Member!</b>\n\n{text}')
    raise SkipHandler

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_leave(event: ChatMemberUpdated):
    user = event.old_chat_member.user
    if user.is_bot:
        raise SkipHandler
    settings = await get_settings(event.chat.id)
    if settings['goodbye']:
        text = _format_msg(settings['goodbye_msg'], user, event.chat)
        await event.bot.send_message(event.chat.id, f'👋 <b>Member Left</b>\n\n{text}')
    raise SkipHandler

@router.message(Command('welcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_welcome(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        settings = await get_settings(message.chat.id)
        status = '✅ ON' if settings['welcome'] else '❌ OFF'
        await message.answer(f"👋 <b>Welcome:</b> {status}\n<b>Message:</b>\n<code>{escape(settings['welcome_msg'])}</code>\n\n<b>Usage:</b> /welcome on|off")
    elif parts[1].casefold() in {'on', 'off'}:
        enabled = parts[1].casefold() == 'on'
        await update_setting(message.chat.id, 'welcome', enabled)
        await message.answer('✅ <b>Welcome messages enabled.</b>' if enabled else '❌ <b>Welcome messages disabled.</b>')
    else:
        await message.answer('<b>Usage:</b> /welcome on|off')

@router.message(Command('goodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_goodbye(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        settings = await get_settings(message.chat.id)
        status = '✅ ON' if settings['goodbye'] else '❌ OFF'
        await message.answer(f"👋 <b>Goodbye:</b> {status}\n<b>Message:</b>\n<code>{escape(settings['goodbye_msg'])}</code>\n\n<b>Usage:</b> /goodbye on|off")
    elif parts[1].casefold() in {'on', 'off'}:
        enabled = parts[1].casefold() == 'on'
        await update_setting(message.chat.id, 'goodbye', enabled)
        await message.answer('✅ <b>Goodbye messages enabled.</b>' if enabled else '❌ <b>Goodbye messages disabled.</b>')
    else:
        await message.answer('<b>Usage:</b> /goodbye on|off')

@router.message(Command('setwelcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setwelcome(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer('<b>Usage:</b> /setwelcome [text]\n\n<b>Placeholders:</b> {mention} {name} {username} {group} {count} {id}')
        return
    await update_setting(message.chat.id, 'welcome_msg', parts[1][:4000])
    await message.answer('✅ <b>Welcome message updated.</b>')

@router.message(Command('setgoodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setgoodbye(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer('<b>Usage:</b> /setgoodbye [text]\n\n<b>Placeholders:</b> {mention} {name} {username} {group} {count} {id}')
        return
    await update_setting(message.chat.id, 'goodbye_msg', parts[1][:4000])
    await message.answer('✅ <b>Goodbye message updated.</b>')
