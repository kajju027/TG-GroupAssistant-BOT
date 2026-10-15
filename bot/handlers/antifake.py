from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated, Message
from bot.database import add_antifake_prefix, get_antifake_prefixes, get_settings, remove_antifake_prefix, update_setting
router = Router()

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_member_join(event: ChatMemberUpdated):
    raise SkipHandler

@router.message(Command('antifake'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antifake(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split()
    if len(parts) < 2:
        settings = await get_settings(message.chat.id)
        prefixes = await get_antifake_prefixes(message.chat.id)
        await message.answer(f"📵 <b>Anti-Fake Number</b>\n\nStatus: {('✅ ON' if settings['antifake'] else '❌ OFF')}\nMode: {settings['antifake_mode'].upper()}\nPrefixes: {(', '.join(prefixes) if prefixes else 'None')}\n\n⚠️ Telegram does not provide member phone numbers to bots, so this feature cannot automatically remove members. The stored prefix list is retained for future/manual workflows.")
        return
    command = parts[1].lower()
    if command == 'on':
        await update_setting(message.chat.id, 'antifake', True)
        await message.answer('✅ Anti-Fake preferences enabled (automatic phone checks are unavailable via Telegram Bot API).')
    elif command == 'off':
        await update_setting(message.chat.id, 'antifake', False)
        await message.answer('❌ Anti-Fake preferences disabled.')
    elif command == 'add' and len(parts) > 2:
        prefix = parts[2] if parts[2].startswith('+') else '+' + parts[2]
        if not prefix[1:].isdigit():
            await message.answer('❌ A prefix must contain digits, for example <code>+91</code>.')
            return
        await add_antifake_prefix(message.chat.id, prefix)
        await message.answer(f'✅ Added prefix: <code>{prefix}</code>')
    elif command == 'remove' and len(parts) > 2:
        prefix = parts[2] if parts[2].startswith('+') else '+' + parts[2]
        await remove_antifake_prefix(message.chat.id, prefix)
        await message.answer(f'✅ Removed prefix: <code>{prefix}</code>')
    elif command == 'list':
        prefixes = await get_antifake_prefixes(message.chat.id)
        await message.answer('📵 <b>Saved prefixes:</b>\n' + '\n'.join((f'• <code>{item}</code>' for item in prefixes)) if prefixes else 'No prefixes set.')
    elif command == 'mode' and len(parts) > 2:
        mode = parts[2].lower()
        if mode not in {'blacklist', 'whitelist'}:
            await message.answer('❌ Valid modes: blacklist, whitelist')
            return
        await update_setting(message.chat.id, 'antifake_mode', mode)
        await message.answer(f'✅ Mode saved as <b>{mode.upper()}</b>.')
    else:
        await message.answer('<b>Usage:</b> /antifake on|off|add [+prefix]|remove [+prefix]|list|mode [blacklist/whitelist]')
