from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from bot.database import get_settings, update_setting, get_antifake_prefixes, add_antifake_prefix, remove_antifake_prefix
from bot.utils.helpers import mention_by_name
router = Router()

def _get_phone_prefix(phone: str) -> str:
    phone = phone.replace('+', '').replace(' ', '')
    for length in [3, 2, 1]:
        if len(phone) >= length:
            return '+' + phone[:length]
    return '+' + phone

async def _is_fake(chat_id: int, user_id: int, bot) -> bool:
    s = await get_settings(chat_id)
    if not s['antifake']:
        return False
    prefixes = await get_antifake_prefixes(chat_id)
    if not prefixes:
        return False
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        phone = getattr(member.user, 'phone_number', None)
    except Exception:
        return False
    if not phone:
        return s['antifake_mode'] == 'whitelist'
    user_prefix = _get_phone_prefix(phone)
    if s['antifake_mode'] == 'blacklist':
        return any((user_prefix.startswith(p) for p in prefixes))
    return not any((user_prefix.startswith(p) for p in prefixes))

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_member_join(event: ChatMemberUpdated):
    if await _is_fake(event.chat.id, event.new_chat_member.user.id, event.bot):
        mention = mention_by_name(event.new_chat_member.user.id, event.new_chat_member.user.full_name)
        await event.bot.ban_chat_member(event.chat.id, event.new_chat_member.user.id)
        await event.bot.send_message(event.chat.id, f'📵 {mention} was removed <b>(fake/restricted number)</b>.')

@router.message(Command('antifake'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antifake(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = '✅ ON' if s['antifake'] else '❌ OFF'
        prefixes = await get_antifake_prefixes(message.chat.id)
        await message.answer(f'📵 <b>Anti-Fake:</b> {status}\n<b>Mode:</b> {s['antifake_mode'].upper()}\n<b>Prefixes:</b> {(', '.join(prefixes) if prefixes else 'None')}\n\n<b>Usage:</b> /antifake on|off|add [+prefix]|remove [+prefix]|list|mode [blacklist/whitelist]')
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'antifake', True)
        await message.answer('✅ <b>Anti-Fake enabled.</b>')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'antifake', False)
        await message.answer('❌ <b>Anti-Fake disabled.</b>')
    elif cmd == 'add' and len(parts) > 2:
        prefix = parts[2] if parts[2].startswith('+') else '+' + parts[2]
        await add_antifake_prefix(message.chat.id, prefix)
        await message.answer(f'✅ Added prefix: <code>{prefix}</code>')
    elif cmd == 'remove' and len(parts) > 2:
        prefix = parts[2] if parts[2].startswith('+') else '+' + parts[2]
        await remove_antifake_prefix(message.chat.id, prefix)
        await message.answer(f'✅ Removed prefix: <code>{prefix}</code>')
    elif cmd == 'list':
        prefixes = await get_antifake_prefixes(message.chat.id)
        if prefixes:
            await message.answer('📵 <b>Prefixes:</b>\n' + '\n'.join((f'• <code>{p}</code>' for p in prefixes)))
        else:
            await message.answer('No prefixes set.')
    elif cmd == 'mode' and len(parts) > 2:
        mode = parts[2].lower()
        if mode not in ('blacklist', 'whitelist'):
            await message.answer('❌ Valid modes: blacklist, whitelist')
            return
        await update_setting(message.chat.id, 'antifake_mode', mode)
        await message.answer(f'✅ Mode set to <b>{mode.upper()}</b>.')
    else:
        await message.answer('<b>Usage:</b> /antifake on|off|add [+prefix]|remove [+prefix]|list|mode [blacklist/whitelist]')
