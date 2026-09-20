from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_settings, update_setting, get_banned_words, add_banned_word, remove_banned_word, add_warning
from bot.utils.helpers import is_admin as check_is_admin, mention_by_name
from bot.utils.autodelete import answer_and_autodelete
router = Router()

@router.message(Command('antiword'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antiword(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = '✅ ON' if s['antiword'] else '❌ OFF'
        words = await get_banned_words(message.chat.id)
        await message.answer(f'🔤 <b>Anti-Word:</b> {status}\n<b>Action:</b> {s['antiword_action'].upper()}\n<b>Words:</b> {(', '.join(words) if words else 'None')}\n\n<b>Usage:</b> /antiword on|off|add|remove|list|action [word]')
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'antiword', True)
        await message.answer('✅ <b>Anti-Word enabled.</b>')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'antiword', False)
        await message.answer('❌ <b>Anti-Word disabled.</b>')
    elif cmd == 'add' and len(parts) > 2:
        word = parts[2].strip().lower()
        await add_banned_word(message.chat.id, word)
        await message.answer(f'✅ Added banned word: <code>{word}</code>')
    elif cmd == 'remove' and len(parts) > 2:
        word = parts[2].strip().lower()
        await remove_banned_word(message.chat.id, word)
        await message.answer(f'✅ Removed banned word: <code>{word}</code>')
    elif cmd == 'list':
        words = await get_banned_words(message.chat.id)
        if words:
            await message.answer('🔤 <b>Banned words:</b>\n' + '\n'.join((f'• <code>{w}</code>' for w in words)))
        else:
            await message.answer('No banned words set.')
    elif cmd == 'action' and len(parts) > 2:
        action = parts[2].lower()
        if action not in ('delete', 'warn', 'kick', 'ban'):
            await message.answer('❌ Valid actions: delete, warn, kick, ban')
            return
        await update_setting(message.chat.id, 'antiword_action', action)
        await message.answer(f'✅ Anti-Word action set to <b>{action.upper()}</b>.')
    else:
        await message.answer('<b>Usage:</b> /antiword on|off|add [word]|remove [word]|list|action [delete/warn/kick/ban]')

@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text, ~F.text.startswith('/'))
async def check_words(message: Message):
    if not message.from_user:
        return
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    s = await get_settings(message.chat.id)
    if not s['antiword']:
        return
    banned = await get_banned_words(message.chat.id)
    if not banned:
        return
    text_lower = (message.text or '').lower()
    for word in banned:
        if word in text_lower:
            try:
                await message.delete()
            except Exception:
                pass
            action = s['antiword_action']
            uid = message.from_user.id
            mention = mention_by_name(uid, message.from_user.full_name)
            if action == 'warn':
                count = await add_warning(message.chat.id, uid, f'Used banned word: {word}')
                if count >= s['warn_limit']:
                    await answer_and_autodelete(message, f'⚠️ {mention} has been kicked for exceeding the warn limit.')
                    try:
                        await message.bot.ban_chat_member(message.chat.id, uid)
                        await message.bot.unban_chat_member(message.chat.id, uid)
                    except Exception:
                        pass
                else:
                    await answer_and_autodelete(message, f'🔤 <b>Banned word removed.</b>\n⚠️ {mention} has been warned ({count}/{s['warn_limit']})')
            elif action == 'kick':
                await answer_and_autodelete(message, f'🚪 {mention} was kicked for using a banned word.')
                try:
                    await message.bot.ban_chat_member(message.chat.id, uid)
                    await message.bot.unban_chat_member(message.chat.id, uid)
                except Exception:
                    pass
            elif action == 'ban':
                await answer_and_autodelete(message, f'🔨 {mention} was banned for using a banned word.')
                try:
                    await message.bot.ban_chat_member(message.chat.id, uid)
                except Exception:
                    pass
            else:
                await answer_and_autodelete(message, f'🔤 <b>Message deleted</b> — banned word used by {mention}.')
            return
