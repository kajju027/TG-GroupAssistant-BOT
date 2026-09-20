from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database import get_settings, update_setting, get_banned_words, get_antifake_prefixes, get_filters, get_whitelisted_links
from bot.utils.helpers import is_admin
router = Router()

def _toggle_btn(label: str, state: bool, feature: str, chat_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=f'{label}: {('✅ ON' if state else '❌ OFF')}', callback_data=f'toggle:{feature}:{chat_id}:{('off' if state else 'on')}')

async def _check_admin(callback: CallbackQuery, chat_id: int) -> bool:
    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer("❌ You're not an admin in that group!", show_alert=True)
        return False
    return True

def _cb_for(callback: CallbackQuery, new_data: str) -> CallbackQuery:
    return callback.model_copy(update={'data': new_data})

@router.callback_query(F.data.startswith('menu:antilink:'))
async def menu_antilink(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    action = s['antilink_action']
    whitelist = s.get('antilink_whitelist', [])
    domains_text = ', '.join(whitelist) if whitelist else 'None'
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Anti-Link', bool(s['antilink']), 'antilink', chat_id)], [InlineKeyboardButton(text=f'Action: {action.upper()}  (tap to cycle)', callback_data=f'cycle:antilink_action:{chat_id}')], [InlineKeyboardButton(text='🌐 Allowed Domains', callback_data=f'menu:antilink_domains:{chat_id}')], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'🔗 <b>Anti-Link Settings</b>\n\nStatus: {('✅ ON' if s['antilink'] else '❌ OFF')}\nAction: <b>{action.upper()}</b>\nAllowed domains: <code>{domains_text}</code>\n\nCycle order: delete → warn → kick → ban\nLinks from allowed domains are never touched.', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:antilink_domains:'))
async def menu_antilink_domains(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    whitelist = await get_whitelisted_links(chat_id)
    domains_text = '\n'.join((f'• <code>{d}</code>' for d in whitelist)) or 'No allowed domains yet.'
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:antilink:{chat_id}')]])
    await callback.message.edit_text(f'🌐 <b>Allowed Domains</b>\n\n{domains_text}\n\nLinks matching these domains are never deleted by Anti-Link.\n\n<b>Commands in group:</b>\n/antilink allow [domain]\n/antilink disallow [domain]\n/antilink domains — list all\n\nExample: <code>/antilink allow youtube.com</code>', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:antiword:'))
async def menu_antiword(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    words = await get_banned_words(chat_id)
    word_list = ', '.join(words) if words else 'None'
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Anti-Word', bool(s['antiword']), 'antiword', chat_id)], [InlineKeyboardButton(text=f'Action: {s['antiword_action'].upper()}  (tap to cycle)', callback_data=f'cycle:antiword_action:{chat_id}')], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'🔤 <b>Anti-Word Settings</b>\n\nStatus: {('✅ ON' if s['antiword'] else '❌ OFF')}\nAction: <b>{s['antiword_action'].upper()}</b>\nBanned words: <code>{word_list}</code>\n\n<b>Commands in group:</b>\n/antiword add [word]\n/antiword remove [word]\n/antiword list', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:antispam:'))
async def menu_antispam(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Anti-Spam', bool(s['antispam']), 'antispam', chat_id)], [InlineKeyboardButton(text=f'Limit: {s['antispam_limit']} msgs', callback_data=f'cycle:antispam_limit:{chat_id}'), InlineKeyboardButton(text=f'Window: {s['antispam_window']}s', callback_data=f'cycle:antispam_window:{chat_id}')], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'🚫 <b>Anti-Spam Settings</b>\n\nStatus: {('✅ ON' if s['antispam'] else '❌ OFF')}\nLimit: <b>{s['antispam_limit']} messages</b> per <b>{s['antispam_window']}s</b>\n\nTap the buttons above to cycle through values.', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:antifake:'))
async def menu_antifake(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    prefixes = await get_antifake_prefixes(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Anti-Fake', bool(s['antifake']), 'antifake', chat_id)], [InlineKeyboardButton(text=f'Mode: {s['antifake_mode'].upper()}  (tap to cycle)', callback_data=f'cycle:antifake_mode:{chat_id}')], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    prefix_list = ', '.join(prefixes) if prefixes else 'None'
    await callback.message.edit_text(f'📵 <b>Anti-Fake Number Settings</b>\n\nStatus: {('✅ ON' if s['antifake'] else '❌ OFF')}\nMode: <b>{s['antifake_mode'].upper()}</b>\nPrefixes: <code>{prefix_list}</code>\n\n<b>Commands in group:</b>\n/antifake add [+prefix]\n/antifake remove [+prefix]\n/antifake list\n\nBlacklist = block listed prefixes\nWhitelist = allow ONLY listed prefixes', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:welcome:'))
async def menu_welcome(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Welcome', bool(s['welcome']), 'welcome', chat_id), _toggle_btn('Goodbye', bool(s['goodbye']), 'goodbye', chat_id)], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'👋 <b>Welcome / Goodbye Settings</b>\n\nWelcome: {('✅ ON' if s['welcome'] else '❌ OFF')}\nGoodbye: {('✅ ON' if s['goodbye'] else '❌ OFF')}\n\n<b>Welcome message:</b>\n<code>{s['welcome_msg']}</code>\n\n<b>Goodbye message:</b>\n<code>{s['goodbye_msg']}</code>\n\n<b>Placeholders:</b> {{mention}} {{name}} {{username}} {{group}} {{count}} {{id}}\n\n<b>Commands in group:</b>\n/setwelcome [text]\n/setgoodbye [text]', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:warn:'))
async def menu_warn(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'Limit: {s['warn_limit']}  (tap to cycle)', callback_data=f'cycle:warn_limit:{chat_id}'), InlineKeyboardButton(text=f'Action: {s['warn_action'].upper()}  (tap)', callback_data=f'cycle:warn_action:{chat_id}')], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'⚠️ <b>Warn System Settings</b>\n\nMax warnings: <b>{s['warn_limit']}</b>\nAction on exceed: <b>{s['warn_action'].upper()}</b>\n\n<b>Commands in group:</b>\n/warn [reply/@user] [reason]\n/unwarn [reply/@user]\n/warns [reply/@user]\n/resetwarns [reply/@user]', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:mute:'))
async def menu_mute(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text('🔇 <b>Mute Settings</b>\n\n<b>Commands in group:</b>\n/mute — mute the entire group\n/unmute — unmute the entire group\n/mute @user [1m/1h/1d] — mute a user\n/unmute @user — unmute a user', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:reaction:'))
async def menu_reaction(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    emojis = s.get('reaction_emojis', ['👍'])
    emoji_text = ' '.join(emojis)
    kb = InlineKeyboardMarkup(inline_keyboard=[[_toggle_btn('Auto-Reaction', bool(s['reaction_enabled']), 'reaction_enabled', chat_id)], [InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'🎭 <b>Auto-Reaction Settings</b>\n\nStatus: {('✅ ON' if s['reaction_enabled'] else '❌ OFF')}\nEmojis: {emoji_text}\n\nEvery new post gets a random emoji reaction from this list, a few seconds after it arrives.\n\n<b>Commands (group or channel):</b>\n/reaction on|off\n/reaction emoji [emoji1 emoji2 ...]', reply_markup=kb)

@router.callback_query(F.data.startswith('menu:filters:'))
async def menu_filters(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    filters = await get_filters(chat_id)
    filter_text = '\n'.join((f'• <code>{f['keyword']}</code>' for f in filters)) or 'No filters set.'
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Back', callback_data=f'menu:main:{chat_id}')]])
    await callback.message.edit_text(f'🔍 <b>Custom Filters ({len(filters)})</b>\n\n{filter_text}\n\n<b>Commands in group:</b>\n/filter [keyword] [reply]\n/filters — list all\n/stop [keyword] — remove', reply_markup=kb)

@router.callback_query(F.data.startswith('toggle:'))
async def toggle_setting(callback: CallbackQuery):
    _, feature, chat_id_str, new_state = callback.data.split(':')
    chat_id = int(chat_id_str)
    if not await _check_admin(callback, chat_id):
        return
    val = new_state == 'on'
    await update_setting(chat_id, feature, val)
    await callback.answer(f'{('✅ Enabled' if val else '❌ Disabled')}: {feature.replace('_', ' ')}')
    _menu_feature = 'welcome' if feature == 'goodbye' else feature
    _menu_map = {'antilink': menu_antilink, 'antiword': menu_antiword, 'antispam': menu_antispam, 'antifake': menu_antifake, 'welcome': menu_welcome, 'warn': menu_warn, 'reaction_enabled': menu_reaction}
    if _menu_feature in _menu_map:
        await _menu_map[_menu_feature](_cb_for(callback, f'menu:{_menu_feature}:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:antilink_action:'))
async def cycle_antilink_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ['delete', 'warn', 'kick', 'ban']
    cur = s['antilink_action']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 'delete'
    await update_setting(chat_id, 'antilink_action', nxt)
    await callback.answer(f'Action → {nxt.upper()}')
    await menu_antilink(_cb_for(callback, f'menu:antilink:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:antiword_action:'))
async def cycle_antiword_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ['delete', 'warn', 'kick', 'ban']
    cur = s['antiword_action']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 'delete'
    await update_setting(chat_id, 'antiword_action', nxt)
    await callback.answer(f'Action → {nxt.upper()}')
    await menu_antiword(_cb_for(callback, f'menu:antiword:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:antifake_mode:'))
async def cycle_antifake_mode(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    modes = ['blacklist', 'whitelist']
    cur = s['antifake_mode']
    nxt = modes[(modes.index(cur) + 1) % len(modes)] if cur in modes else 'blacklist'
    await update_setting(chat_id, 'antifake_mode', nxt)
    await callback.answer(f'Mode → {nxt.upper()}')
    await menu_antifake(_cb_for(callback, f'menu:antifake:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:antispam_limit:'))
async def cycle_antispam_limit(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [3, 5, 7, 10, 15, 20]
    cur = s['antispam_limit']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 5
    await update_setting(chat_id, 'antispam_limit', nxt)
    await callback.answer(f'Limit → {nxt} msgs')
    await menu_antispam(_cb_for(callback, f'menu:antispam:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:antispam_window:'))
async def cycle_antispam_window(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [5, 10, 15, 30, 60]
    cur = s['antispam_window']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 10
    await update_setting(chat_id, 'antispam_window', nxt)
    await callback.answer(f'Window → {nxt}s')
    await menu_antispam(_cb_for(callback, f'menu:antispam:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:warn_limit:'))
async def cycle_warn_limit(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [2, 3, 5, 7, 10]
    cur = s['warn_limit']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 3
    await update_setting(chat_id, 'warn_limit', nxt)
    await callback.answer(f'Warn limit → {nxt}')
    await menu_warn(_cb_for(callback, f'menu:warn:{chat_id}'))

@router.callback_query(F.data.startswith('cycle:warn_action:'))
async def cycle_warn_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ['kick', 'ban', 'mute']
    cur = s['warn_action']
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 'kick'
    await update_setting(chat_id, 'warn_action', nxt)
    await callback.answer(f'Action → {nxt.upper()}')
    await menu_warn(_cb_for(callback, f'menu:warn:{chat_id}'))
