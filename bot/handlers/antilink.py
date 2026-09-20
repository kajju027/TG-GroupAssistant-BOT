import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_settings, update_setting, add_whitelist_link, remove_whitelist_link, get_whitelisted_links, add_warning
from bot.utils.helpers import is_admin as check_is_admin, mention_by_name, is_domain_whitelisted, extract_domain
from bot.utils.autodelete import answer_and_autodelete
router = Router()
LINK_RE = re.compile('(https?://[^\\s]+|t\\.me/[^\\s]+|telegram\\.me/[^\\s]+)', re.IGNORECASE)

async def _apply_action(message: Message, action: str):
    uid = message.from_user.id
    mention = mention_by_name(uid, message.from_user.full_name)
    try:
        await message.delete()
    except Exception:
        pass
    if action == 'warn':
        s = await get_settings(message.chat.id)
        count = await add_warning(message.chat.id, uid, 'Sent a link')
        if count >= s['warn_limit']:
            await answer_and_autodelete(message, f'⚠️ {mention} has been kicked for exceeding the warn limit.')
            try:
                await message.bot.ban_chat_member(message.chat.id, uid)
                await message.bot.unban_chat_member(message.chat.id, uid)
            except Exception:
                pass
        else:
            await answer_and_autodelete(message, f'🔗 <b>Link removed.</b>\n⚠️ {mention} has been warned ({count}/{s['warn_limit']})\n<b>Reason:</b> Sent a link')
    elif action == 'kick':
        await answer_and_autodelete(message, f'🚪 {mention} was kicked for sending a link.')
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
            await message.bot.unban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    elif action == 'ban':
        await answer_and_autodelete(message, f'🔨 {mention} was banned for sending a link.')
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    else:
        await answer_and_autodelete(message, f'🔗 <b>Link removed</b> from {mention}.')

@router.message(Command('antilink'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antilink(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = '✅ ON' if s['antilink'] else '❌ OFF'
        await message.answer(f'🔗 <b>Anti-Link:</b> {status}\n<b>Action:</b> {s['antilink_action'].upper()}\n\n<b>Usage:</b>\n/antilink on|off\n/antilink action [delete/warn/kick/ban]\n/antilink allow [domain]\n/antilink disallow [domain]\n/antilink domains')
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'antilink', True)
        await message.answer('✅ <b>Anti-Link enabled.</b>')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'antilink', False)
        await message.answer('❌ <b>Anti-Link disabled.</b>')
    elif cmd in ('allow', 'whitelist', 'wl') and len(parts) > 2:
        domain = extract_domain(parts[2])
        await add_whitelist_link(message.chat.id, domain)
        await message.answer(f'✅ Links from <code>{domain}</code> will no longer be removed.')
    elif cmd in ('disallow', 'unwhitelist', 'unwl') and len(parts) > 2:
        domain = extract_domain(parts[2])
        await remove_whitelist_link(message.chat.id, domain)
        await message.answer(f'✅ Removed <code>{domain}</code> from the allowed list.')
    elif cmd in ('domains', 'allowed'):
        whitelist = await get_whitelisted_links(message.chat.id)
        text = '\n'.join((f'• <code>{d}</code>' for d in whitelist)) or 'No allowed domains set.'
        await message.answer(f'🌐 <b>Allowed Domains</b>\n\n{text}')
    elif cmd == 'action' and len(parts) > 2:
        action = parts[2].lower()
        if action not in ('delete', 'warn', 'kick', 'ban'):
            await message.answer('❌ Valid actions: delete, warn, kick, ban')
            return
        await update_setting(message.chat.id, 'antilink_action', action)
        await message.answer(f'✅ Anti-Link action set to <b>{action.upper()}</b>.')
    else:
        await message.answer('<b>Usage:</b>\n/antilink on|off\n/antilink action [delete/warn/kick/ban]\n/antilink allow [domain]\n/antilink disallow [domain]\n/antilink domains')

@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text, ~F.text.startswith('/'))
async def check_links(message: Message):
    if not message.from_user:
        return
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    s = await get_settings(message.chat.id)
    if not s['antilink']:
        return
    links = LINK_RE.findall(message.text or '')
    if not links:
        return
    whitelist = s.get('antilink_whitelist', [])
    for link in links:
        if not is_domain_whitelisted(link, whitelist):
            await _apply_action(message, s['antilink_action'])
            return
