from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.core.config import REACTION_EMOJIS, REACT_PRESETS
from bot.database import (
    add_banned_word,
    add_filter,
    add_whitelist_link,
    get_banned_words,
    get_filters,
    get_settings,
    get_whitelisted_links,
    remove_banned_word,
    remove_filter,
    remove_whitelist_link,
    reset_chat_settings,
    update_setting,
)
from bot.states import PanelInput
from bot.utils.helpers import safe_edit
from bot.utils.ui import bold, box, btn, dot, italic, kb, mono, quote, quote_expandable, row, sc, tbtn

router = Router()

ACTIONS = ['delete', 'warn', 'kick', 'ban']
WARN_ACTIONS = ['kick', 'ban', 'mute']
SPAM_LIMITS = [3, 5, 7, 10, 15, 20]
SPAM_WINDOWS = [5, 10, 15, 30, 60]
WARN_LIMITS = [2, 3, 5, 7, 10]

EMOJI_PER_PAGE = 20
KEYWORD_MAX = 24  # keeps callback data safely under Telegram's 64 bytes


def _cb_part(text: str, limit: int = 32) -> str:
    return text.encode('utf-8')[:limit].decode('utf-8', errors='ignore')


# --------------------------------------------------------------- helpers ---
async def _chat_meta(chat_id: int) -> dict:
    data = await get_settings(chat_id)
    return {
        'title': data.get('chat_title') or 'Untitled',
        'type': data.get('chat_type') or 'group',
        'bot_admin': bool(data.get('bot_is_admin')),
    }


def _preview(text: str, limit: int = 200) -> str:
    text = (text or '').strip()
    if not text:
        return italic(sc('Not set yet.'))
    return quote_expandable(escape(text[:limit]) + ('…' if len(text) > limit else ''))


async def _check_access(callback: CallbackQuery, chat_id: int) -> bool:
    from bot.handlers.panel import can_manage

    if not await can_manage(callback, chat_id, callback.from_user.id):
        await callback.answer('You are not an admin in that chat.', show_alert=True)
        return False
    return True


def _panel_back_kb(chat_id: int) -> list:
    return [btn('🔙 Back', f'pm:{chat_id}'), btn('❌ Close', 'close')]


# ------------------------------------------------------------ main panel ---
async def render_chat_panel(chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    s = await get_settings(chat_id)
    meta = await _chat_meta(chat_id)
    is_channel = meta['type'] == 'channel'
    icon = '📢' if is_channel else '👥'
    filters_count = len(s.get('filters', {})) if isinstance(s.get('filters'), dict) else 0
    lines = [
        f"{icon} <b>{escape(meta['title'][:48])}</b>",
        row('Id', mono(str(chat_id))),
        row('Bot', f"🟢 {sc('Admin')}" if meta['bot_admin'] else f"⚠️ {sc('No admin rights')}"),
        '',
        quote(sc('Everything for this chat is configured here — nothing is set inside the chat itself.')),
    ]
    if is_channel:
        rows = [
            [btn(f"🎭 Reactions {dot(bool(s.get('reaction_enabled')))}", f'pv:rx:{chat_id}')],
            [btn(f"🛡️ Guard {dot(bool(s.get('antitag')))}", f'pv:cg:{chat_id}')],
            [btn('♻️ Reset Settings', f'rst:{chat_id}')],
            [btn('🔙 Chats', 'panel:list'), btn('❌ Close', 'close')],
        ]
    else:
        rows = [
            [btn(f"🎭 Reactions {dot(bool(s.get('reaction_enabled')))}", f'pv:rx:{chat_id}'),
             btn(f"👋 Welcome {dot(bool(s.get('welcome')))}", f'pv:wc:{chat_id}')],
            [btn(f"🔗 Anti Link {dot(bool(s.get('antilink')))}", f'pv:al:{chat_id}'),
             btn(f"🔤 Anti Word {dot(bool(s.get('antiword')))}", f'pv:aw:{chat_id}')],
            [btn(f"🚫 Anti Spam {dot(bool(s.get('antispam')))}", f'pv:as:{chat_id}'),
             btn(f"⚠️ Warns {dot(True)}", f'pv:wn:{chat_id}')],
            [btn(f"🔎 Filters ({filters_count})", f'pv:fl:{chat_id}')],
            [btn('♻️ Reset Settings', f'rst:{chat_id}')],
            [btn('🔙 Chats', 'panel:list'), btn('❌ Close', 'close')],
        ]
    return box('Chat Settings ⚙️', lines), kb(*rows)


async def _back_to_panel(callback: CallbackQuery, chat_id: int) -> None:
    text, markup = await render_chat_panel(chat_id)
    if callback.message is not None:
        if not await safe_edit(callback.message, text, markup):
            await callback.message.answer(text, reply_markup=markup)


async def _rerender(callback: CallbackQuery, data: str) -> None:
    """Re-run a panel handler with a rewritten callback payload."""
    cb2 = callback.model_copy(update={'data': data})
    route = data.split(':')[1]
    if route == 'rx':
        await pv_reactions(cb2)
    elif route == 'wc':
        await pv_welcome(cb2)
    elif route == 'al':
        await pv_antilink(cb2)
    elif route == 'aw':
        await pv_antiword(cb2)
    elif route == 'as':
        await pv_antispam(cb2)
    elif route == 'wn':
        await pv_warns(cb2)
    elif route == 'fl':
        await pv_filters(cb2)
    elif route == 'cg':
        await pv_guard(cb2)


# -------------------------------------------------------- panel routers ---
@router.callback_query(F.data.startswith('pm:'))
async def panel_main(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[1])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    await _back_to_panel(callback, chat_id)


# ------------------------------------------------------------ reactions ---
def _rx_text(s: dict) -> str:
    mode = s.get('reaction_mode') or 'random'
    emojis = [e for e in (s.get('reaction_emojis') or []) if e in REACTION_EMOJIS]
    if not emojis:
        emojis = ['🔥', '❤', '👏', '🎉', '💯']
    mode_label = {'random': '🎲 Random', 'cycle': '🔄 Cycle', 'fixed': '📌 Fixed'}.get(mode, '🎲 Random')
    return box('Super Reactions 🎭', [
        row('Status', f"{dot(bool(s.get('reaction_enabled')))} <b>{sc('On') if s.get('reaction_enabled') else sc('Off')}</b>"),
        row('Mode', bold(sc(mode_label))),
        row('Set', ' '.join(emojis)),
        '',
        quote(sc('The bot reacts to every new message with a big animated emoji — in groups and channels. Tap emojis to build your own set, or use a preset.')),
    ])


def _rx_kb(chat_id: int, s: dict, page: int = 0) -> InlineKeyboardMarkup:
    selected = [e for e in (s.get('reaction_emojis') or []) if e in REACTION_EMOJIS]
    mode = s.get('reaction_mode') or 'random'
    emoji_pages = (len(REACTION_EMOJIS) + EMOJI_PER_PAGE - 1) // EMOJI_PER_PAGE
    presets_page = emoji_pages
    page = max(0, min(page, presets_page))

    rows = [[tbtn('Reactions', bool(s.get('reaction_enabled')), f'tgl:rx:{chat_id}')]]
    rows.append([
        InlineKeyboardButton(text=('✅ ' if mode == 'random' else '') + '🎲 Random', callback_data=f'rx:{chat_id}:m:random'),
        InlineKeyboardButton(text=('✅ ' if mode == 'cycle' else '') + '🔄 Cycle', callback_data=f'rx:{chat_id}:m:cycle'),
        InlineKeyboardButton(text=('✅ ' if mode == 'fixed' else '') + '📌 Fixed', callback_data=f'rx:{chat_id}:m:fixed'),
    ])

    if page == presets_page:
        presets = [
            ('🔥 Fire', 'fire'), ('🎉 Party', 'party'), ('❤️ Love', 'love'),
            ('😎 Cool', 'cool'), ('🤣 Fun', 'fun'), ('👍 Respect', 'respect'),
        ]
        for i in range(0, len(presets), 2):
            rows.append([btn(label, f'rx:{chat_id}:pre:{key}') for label, key in presets[i:i + 2]])
        rows.append([btn('🧹 Clear Set', f'rx:{chat_id}:pre:clear')])
        nav = [btn('⬅️ Emojis', f'rx:{chat_id}:pg:0')]
        rows.append(nav)
    else:
        chunk = REACTION_EMOJIS[page * EMOJI_PER_PAGE:(page + 1) * EMOJI_PER_PAGE]
        for i in range(0, len(chunk), 5):
            line = []
            for j, emoji in enumerate(chunk[i:i + 5]):
                index = page * EMOJI_PER_PAGE + i + j
                mark = '✅' if emoji in selected else '▫️'
                line.append(InlineKeyboardButton(text=f'{mark}{emoji}', callback_data=f'rx:{chat_id}:t:{page}:{index}'))
            rows.append(line)
        nav = []
        if page > 0:
            nav.append(btn('⬅️', f'rx:{chat_id}:pg:{page - 1}'))
        nav.append(btn('🎁 Presets', f'rx:{chat_id}:pg:{presets_page}'))
        if page < emoji_pages - 1:
            nav.append(btn('➡️', f'rx:{chat_id}:pg:{page + 1}'))
        rows.append(nav)

    rows.append(_panel_back_kb(chat_id))
    return kb(*rows)


def _emoji_pages() -> int:
    return (len(REACTION_EMOJIS) + EMOJI_PER_PAGE - 1) // EMOJI_PER_PAGE


@router.callback_query(F.data.startswith('pv:rx:'))
async def pv_reactions(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    if callback.message is not None:
        await safe_edit(callback.message, _rx_text(s), _rx_kb(chat_id, s, 0))


@router.callback_query(F.data.startswith('rx:'))
async def rx_actions(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        parts = callback.data.split(':')
        chat_id = int(parts[1])
        action = parts[2]
    except (AttributeError, IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    s = await get_settings(chat_id)
    selected = [e for e in (s.get('reaction_emojis') or []) if e in REACTION_EMOJIS]

    if action == 'pg':
        try:
            page = int(parts[3])
        except (IndexError, ValueError):
            page = 0
        await callback.answer()
        if callback.message is not None:
            await safe_edit(callback.message, _rx_text(s), _rx_kb(chat_id, s, page))
        return

    if action == 'm':
        mode = parts[3] if len(parts) > 3 and parts[3] in {'random', 'cycle', 'fixed'} else 'random'
        await update_setting(chat_id, 'reaction_mode', mode)
        await callback.answer(f'Mode → {mode}')
        s = await get_settings(chat_id)
        if callback.message is not None:
            await safe_edit(callback.message, _rx_text(s), _rx_kb(chat_id, s, 0))
        return

    if action == 't':
        try:
            page = int(parts[3])
            index = int(parts[4])
        except (IndexError, ValueError):
            await callback.answer()
            return
        if 0 <= index < len(REACTION_EMOJIS):
            emoji = REACTION_EMOJIS[index]
            if emoji in selected:
                selected.remove(emoji)
                await callback.answer(f'Removed {emoji}')
            else:
                selected.append(emoji)
                await callback.answer(f'Added {emoji}')
            if not selected:
                selected = ['🔥']
            await update_setting(chat_id, 'reaction_emojis', selected)
        else:
            await callback.answer()
        s = await get_settings(chat_id)
        if callback.message is not None:
            await safe_edit(callback.message, _rx_text(s), _rx_kb(chat_id, s, page))
        return

    if action == 'pre':
        key = parts[3] if len(parts) > 3 else ''
        if key == 'clear':
            await update_setting(chat_id, 'reaction_emojis', [])
            await callback.answer('Set cleared — the default pool is used.')
        elif key in REACT_PRESETS:
            await update_setting(chat_id, 'reaction_emojis', list(REACT_PRESETS[key]))
            await callback.answer('Preset applied ✅')
        else:
            await callback.answer()
        s = await get_settings(chat_id)
        if callback.message is not None:
            await safe_edit(callback.message, _rx_text(s), _rx_kb(chat_id, s, _emoji_pages()))
        return

    await callback.answer()


# ------------------------------------------------------------- welcome ----
@router.callback_query(F.data.startswith('pv:wc:'))
async def pv_welcome(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    text = box('Welcome & Goodbye 👋', [
        row('Welcome', f"{dot(bool(s.get('welcome')))} <b>{sc('On') if s.get('welcome') else sc('Off')}</b>"),
        row('Goodbye', f"{dot(bool(s.get('goodbye')))} <b>{sc('On') if s.get('goodbye') else sc('Off')}</b>"),
        '',
        f"<b>{sc('Welcome message')}</b>",
        _preview(s.get('welcome_msg', '')),
        '',
        f"<b>{sc('Goodbye message')}</b>",
        _preview(s.get('goodbye_msg', '')),
        '',
        quote(sc('Placeholders: {mention} {name} {username} {group} {count} {id} — welcome fires for new members, goodbye when they leave.')),
    ])
    markup = kb(
        [tbtn('Welcome', bool(s.get('welcome')), f'tgl:wc:{chat_id}'), tbtn('Goodbye', bool(s.get('goodbye')), f'tgl:gw:{chat_id}')],
        [btn('✏️ Edit Welcome', f'ask:welcome:{chat_id}'), btn('✏️ Edit Goodbye', f'ask:goodbye:{chat_id}')],
        _panel_back_kb(chat_id),
    )
    if callback.message is not None:
        await safe_edit(callback.message, text, markup)


# ------------------------------------------------------------ anti-link ---
@router.callback_query(F.data.startswith('pv:al:'))
async def pv_antilink(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    whitelist = await get_whitelisted_links(chat_id)
    lines = [
        row('Status', f"{dot(bool(s.get('antilink')))} <b>{sc('On') if s.get('antilink') else sc('Off')}</b>"),
        row('Action', bold(sc(s.get('antilink_action', 'delete')))),
        row('Admins', sc('always exempt')),
    ]
    if whitelist:
        lines += ['', f"<b>{sc('Allowed domains')}</b>"]
        for domain in whitelist[:15]:
            lines.append(f"  🌐 {mono(escape(domain))}")
    else:
        lines += ['', italic(sc('No allowed domains yet — every link is handled.'))]
    text = box('Anti Link 🔗', lines)
    rows = [
        [tbtn('Anti Link', bool(s.get('antilink')), f'tgl:al:{chat_id}')],
        [btn('⚡ Action', f'cyc:al_action:{chat_id}'), btn('➕ Allow Domain', f'ask:allow_domain:{chat_id}')],
    ]
    for domain in whitelist[:15]:
        rows.append([InlineKeyboardButton(text=f'🗑 {_cb_part(domain, 20)}', callback_data=f'alx:{chat_id}:{_cb_part(domain, 24)}')])
    rows.append(_panel_back_kb(chat_id))
    if callback.message is not None:
        await safe_edit(callback.message, text, kb(*rows))


# ------------------------------------------------------------ anti-word ---
@router.callback_query(F.data.startswith('pv:aw:'))
async def pv_antiword(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    words = await get_banned_words(chat_id)
    lines = [
        row('Status', f"{dot(bool(s.get('antiword')))} <b>{sc('On') if s.get('antiword') else sc('Off')}</b>"),
        row('Action', bold(sc(s.get('antiword_action', 'delete')))),
        row('Words', bold(str(len(words)))),
    ]
    if words:
        lines += ['']
        for word in words[:15]:
            lines.append(f"  🔤 {mono(escape(word))}")
    text = box('Anti Word 🔤', lines)
    rows = [
        [tbtn('Anti Word', bool(s.get('antiword')), f'tgl:aw:{chat_id}')],
        [btn('⚡ Action', f'cyc:aw_action:{chat_id}'), btn('➕ Add Word', f'ask:add_word:{chat_id}')],
    ]
    for word in words[:15]:
        rows.append([InlineKeyboardButton(text=f'🗑 {_cb_part(word, 20)}', callback_data=f'awx:{chat_id}:{_cb_part(word, 24)}')])
    rows.append(_panel_back_kb(chat_id))
    if callback.message is not None:
        await safe_edit(callback.message, text, kb(*rows))


# ------------------------------------------------------------ anti-spam ---
@router.callback_query(F.data.startswith('pv:as:'))
async def pv_antispam(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    text = box('Anti Spam 🚫', [
        row('Status', f"{dot(bool(s.get('antispam')))} <b>{sc('On') if s.get('antispam') else sc('Off')}</b>"),
        row('Limit', bold(f"{s.get('antispam_limit', 5)} {sc('messages')}")),
        row('Window', bold(f"{s.get('antispam_window', 10)} {sc('seconds')}")),
        '',
        quote(sc('Anyone sending more messages than the limit inside the window is muted for 5 minutes. Admins are never touched.')),
    ])
    markup = kb(
        [tbtn('Anti Spam', bool(s.get('antispam')), f'tgl:as:{chat_id}')],
        [btn('➕ Limit', f'cyc:as_limit:{chat_id}'), btn('⏱️ Window', f'cyc:as_window:{chat_id}')],
        _panel_back_kb(chat_id),
    )
    if callback.message is not None:
        await safe_edit(callback.message, text, markup)


# ---------------------------------------------------------------- warns ---
@router.callback_query(F.data.startswith('pv:wn:'))
async def pv_warns(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    text = box('Warn System ⚠️', [
        row('Limit', bold(str(s.get('warn_limit', 3)))),
        row('Action', bold(sc(s.get('warn_action', 'kick')))),
        '',
        quote(sc('Use /warn, /unwarn, /warns and /resetwarns in the group. When a user hits the limit, the action above fires automatically.')),
    ])
    markup = kb(
        [btn('➕ Limit', f'cyc:wn_limit:{chat_id}'), btn('⚡ Action', f'cyc:wn_action:{chat_id}')],
        _panel_back_kb(chat_id),
    )
    if callback.message is not None:
        await safe_edit(callback.message, text, markup)


# -------------------------------------------------------------- filters ---
@router.callback_query(F.data.startswith('pv:fl:'))
async def pv_filters(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    filters = await get_filters(chat_id)
    lines = [row('Total', bold(str(len(filters))))]
    if filters:
        lines += ['']
        for item in filters[:15]:
            lines.append(f"  🔎 {mono(escape(item['keyword'][:30]))}")
    else:
        lines += ['', italic(sc('No filters yet — add one and the bot replies whenever someone types the keyword.'))]
    text = box('Filters 🔎', lines)
    rows = [[btn('➕ Add Filter', f'ask:filter_kw:{chat_id}')]]
    for item in filters[:15]:
        token = _cb_part(item['keyword'], 24)
        rows.append([
            InlineKeyboardButton(text=f'🔎 {_cb_part(item["keyword"], 20)}', callback_data=f'flv:{chat_id}:{token}'),
            InlineKeyboardButton(text='🗑', callback_data=f'flx:{chat_id}:{token}'),
        ])
    rows.append(_panel_back_kb(chat_id))
    if callback.message is not None:
        await safe_edit(callback.message, text, kb(*rows))


def _find_filter(filters: list, token: str) -> dict | None:
    """Locate a filter from a callback token (exact match first, then prefix)."""
    for item in filters:
        if item['keyword'] == token:
            return item
    for item in filters:
        if item['keyword'].startswith(token):
            return item
    return None


@router.callback_query(F.data.startswith('flv:'))
async def fl_view(callback: CallbackQuery):
    try:
        parts = callback.data.split(':', 2)
        chat_id = int(parts[1])
        token = parts[2]
    except (AttributeError, IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    entry = _find_filter(await get_filters(chat_id), token)
    if entry is None:
        await callback.answer('This filter no longer exists.', show_alert=True)
        return
    text = box('Filter 🔎', [
        row('Keyword', mono(escape(entry['keyword']))),
        '',
        f"<b>{sc('Reply')}</b>",
        _preview(entry['reply'], 800),
    ])
    markup = kb(
        [btn('🗑 Delete Filter', f'flx:{chat_id}:{_cb_part(entry["keyword"], 24)}')],
        [btn('🔙 Back', f'pv:fl:{chat_id}'), btn('❌ Close', 'close')],
    )
    if callback.message is not None:
        await safe_edit(callback.message, text, markup)


@router.callback_query(F.data.startswith('flx:'))
async def fl_delete(callback: CallbackQuery):
    try:
        parts = callback.data.split(':', 2)
        chat_id = int(parts[1])
        token = parts[2]
    except (AttributeError, IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    entry = _find_filter(await get_filters(chat_id), token)
    if entry is not None:
        await remove_filter(chat_id, entry['keyword'])
        await callback.answer('Filter removed ✅')
    else:
        await callback.answer('Already gone.')
    if callback.message is not None:
        await _rerender(callback, f'pv:fl:{chat_id}')


# --------------------------------------------------------- channel guard --
@router.callback_query(F.data.startswith('pv:cg:'))
async def pv_guard(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        chat_id = int(callback.data.split(':')[2])
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer()
    s = await get_settings(chat_id)
    text = box('Channel Guard 🛡️', [
        row('Status', f"{dot(bool(s.get('antitag')))} <b>{sc('On') if s.get('antitag') else sc('Off')}</b>"),
        '',
        quote(sc('When ON, every message posted by any bot in this channel that tries to tag a user is deleted instantly. Human posts are never touched.')),
    ])
    markup = kb(
        [tbtn('Guard', bool(s.get('antitag')), f'tgl:cg:{chat_id}')],
        _panel_back_kb(chat_id),
    )
    if callback.message is not None:
        await safe_edit(callback.message, text, markup)


# ---------------------------------------------------------------- reset ---
@router.callback_query(F.data.startswith('rst:'))
async def reset_settings_flow(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    parts = (callback.data or '').split(':')
    if len(parts) == 3 and parts[1] == 'go':
        try:
            chat_id = int(parts[2])
        except ValueError:
            await callback.answer('Invalid request.', show_alert=True)
            return
        if not await _check_access(callback, chat_id):
            return
        await reset_chat_settings(chat_id)
        await callback.answer('Settings reset to defaults ✅')
        await _back_to_panel(callback, chat_id)
        return
    if len(parts) == 2:
        try:
            chat_id = int(parts[1])
        except ValueError:
            await callback.answer('Invalid request.', show_alert=True)
            return
        if not await _check_access(callback, chat_id):
            return
        await callback.answer()
        text = box('Reset Settings ♻️', [
            quote(sc('Every feature in this chat goes back to factory defaults — everything OFF. Filters, banned words and allowed domains are kept; delete them from their panels if needed.')),
        ])
        markup = kb(
            [btn('✅ Yes, Reset', f'rst:go:{chat_id}')],
            _panel_back_kb(chat_id),
        )
        if callback.message is not None:
            await safe_edit(callback.message, text, markup)
        return
    await callback.answer('Invalid request.', show_alert=True)


# -------------------------------------------------------------- toggles ---
TOGGLE_KEYS = {
    'rx': ('reaction_enabled', 'rx'),
    'wc': ('welcome', 'wc'),
    'gw': ('goodbye', 'wc'),
    'al': ('antilink', 'al'),
    'aw': ('antiword', 'aw'),
    'as': ('antispam', 'as'),
    'cg': ('antitag', 'cg'),
}


@router.callback_query(F.data.startswith('tgl:'))
async def toggle_setting(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        _, feature, chat_id_text = callback.data.split(':')
        chat_id = int(chat_id_text)
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    entry = TOGGLE_KEYS.get(feature)
    if entry is None:
        await callback.answer('Unknown feature.', show_alert=True)
        return
    key, panel_route = entry
    s = await get_settings(chat_id)
    new_state = not bool(s.get(key))
    if key in {'welcome', 'goodbye'} and new_state:
        text_key = 'welcome_msg' if key == 'welcome' else 'goodbye_msg'
        if not s.get(text_key):
            await callback.answer('Set a message first — tap Edit below.', show_alert=True)
            return
    await update_setting(chat_id, key, new_state)
    await callback.answer(f"{'✅ On' if new_state else '❌ Off'}")
    if callback.message is not None:
        await _rerender(callback, f'pv:{panel_route}:{chat_id}')


# --------------------------------------------------------------- cycles ---
CYCLE_MAP = {
    'al_action': ('antilink_action', ACTIONS, 'al'),
    'aw_action': ('antiword_action', ACTIONS, 'aw'),
    'as_limit': ('antispam_limit', SPAM_LIMITS, 'as'),
    'as_window': ('antispam_window', SPAM_WINDOWS, 'as'),
    'wn_limit': ('warn_limit', WARN_LIMITS, 'wn'),
    'wn_action': ('warn_action', WARN_ACTIONS, 'wn'),
}


@router.callback_query(F.data.startswith('cyc:'))
async def cycle_setting(callback: CallbackQuery, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    try:
        _, key, chat_id_text = callback.data.split(':')
        chat_id = int(chat_id_text)
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    entry = CYCLE_MAP.get(key)
    if entry is None:
        await callback.answer('Unknown option.', show_alert=True)
        return
    setting_key, options, panel_route = entry
    s = await get_settings(chat_id)
    current = s.get(setting_key)
    nxt = options[(options.index(current) + 1) % len(options)] if current in options else options[0]
    await update_setting(chat_id, setting_key, nxt)
    await callback.answer(f'→ {nxt}')
    if callback.message is not None:
        await _rerender(callback, f'pv:{panel_route}:{chat_id}')


# ------------------------------------------------------------ deletions ---
@router.callback_query(F.data.startswith('awx:'))
async def aw_delete(callback: CallbackQuery):
    try:
        parts = callback.data.split(':', 2)
        chat_id = int(parts[1])
        token = parts[2]
    except (AttributeError, IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    words = await get_banned_words(chat_id)
    target = next((w for w in words if w == token), None) or next((w for w in words if w.startswith(token)), None)
    if target is not None:
        await remove_banned_word(chat_id, target)
        await callback.answer('Word removed ✅')
    else:
        await callback.answer('Already gone.')
    if callback.message is not None:
        await _rerender(callback, f'pv:aw:{chat_id}')


@router.callback_query(F.data.startswith('alx:'))
async def al_delete(callback: CallbackQuery):
    try:
        parts = callback.data.split(':', 2)
        chat_id = int(parts[1])
        token = parts[2]
    except (AttributeError, IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    domains = await get_whitelisted_links(chat_id)
    target = next((d for d in domains if d == token), None) or next((d for d in domains if d.startswith(token)), None)
    if target is not None:
        await remove_whitelist_link(chat_id, target)
        await callback.answer('Domain removed ✅')
    else:
        await callback.answer('Already gone.')
    if callback.message is not None:
        await _rerender(callback, f'pv:al:{chat_id}')


# ---------------------------------------------------------- text inputs --
_ASK_CONFIG = {
    'welcome': (PanelInput.welcome_text, 'Send the new welcome message.', 'wc'),
    'goodbye': (PanelInput.goodbye_text, 'Send the new goodbye message.', 'wc'),
    'allow_domain': (PanelInput.antilink_domain, 'Send the domain to allow, e.g. youtube.com', 'al'),
    'add_word': (PanelInput.antiword_add, 'Send the word or phrase to ban.', 'aw'),
    'filter_kw': (PanelInput.filter_keyword, 'Send the keyword that should trigger the filter.', 'fl'),
}


@router.callback_query(F.data.startswith('ask:'))
async def ask_for_input(callback: CallbackQuery, state: FSMContext):
    try:
        _, kind, chat_id_text = callback.data.split(':')
        chat_id = int(chat_id_text)
        target_state, prompt, route = _ASK_CONFIG[kind]
    except (AttributeError, KeyError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await state.set_state(target_state)
    await state.update_data(chat_id=chat_id, back_route=route)
    placeholders = ''
    if kind in {'welcome', 'goodbye'}:
        placeholders = '\n\n' + sc('Placeholders: {mention} {name} {username} {group} {count} {id}')
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            f'✏️ <b>{sc(prompt)}</b>{placeholders}',
            kb([btn('❌ Cancel', f'cx:{route}:{chat_id}')]),
        )


@router.callback_query(F.data.startswith('cx:'))
async def cancel_input(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        _, route, chat_id_text = callback.data.split(':')
        chat_id = int(chat_id_text)
    except (AttributeError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await _check_access(callback, chat_id):
        return
    await callback.answer('Cancelled')
    if callback.message is not None:
        await _rerender(callback, f'pv:{route}:{chat_id}')


async def _active_fsm_chat(message: Message, state: FSMContext) -> int | None:
    data = await state.get_data()
    try:
        chat_id = int(data['chat_id'])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await message.answer('⚠️ This settings session expired. Open /settings again.')
        return None
    from bot.handlers.panel import can_manage

    if message.from_user is None or not await can_manage(message, chat_id, message.from_user.id):
        await state.clear()
        await message.answer('❌ You are no longer allowed to manage that chat.')
        return None
    return chat_id


async def _reopen_panel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get('chat_id')
    await state.clear()
    text, markup = await render_chat_panel(int(chat_id))
    await message.answer('✅ <b>Saved.</b>')
    await message.answer(text, reply_markup=markup)


def _input_text(message: Message) -> str:
    return (message.text or '').strip()


@router.message(PanelInput.welcome_text, F.chat.type == 'private', F.text)
async def input_welcome(message: Message, state: FSMContext):
    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    await update_setting(chat_id, 'welcome_msg', (message.html_text or message.text or '')[:4000])
    await update_setting(chat_id, 'welcome', True)
    await _reopen_panel(message, state)


@router.message(PanelInput.goodbye_text, F.chat.type == 'private', F.text)
async def input_goodbye(message: Message, state: FSMContext):
    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    await update_setting(chat_id, 'goodbye_msg', (message.html_text or message.text or '')[:4000])
    await update_setting(chat_id, 'goodbye', True)
    await _reopen_panel(message, state)


@router.message(PanelInput.antilink_domain, F.chat.type == 'private', F.text)
async def input_allow_domain(message: Message, state: FSMContext):
    from bot.utils.helpers import extract_domain

    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    domain = extract_domain(_input_text(message))
    if not domain or '.' not in domain:
        await message.answer(f"❌ {sc('Send a valid domain, for example')} <code>youtube.com</code>.")
        return
    await add_whitelist_link(chat_id, domain)
    await _reopen_panel(message, state)


@router.message(PanelInput.antiword_add, F.chat.type == 'private', F.text)
async def input_add_word(message: Message, state: FSMContext):
    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    word = _input_text(message).casefold()[:KEYWORD_MAX]
    if not word:
        await message.answer(f"❌ {sc('Send a word or phrase to ban.')}")
        return
    await add_banned_word(chat_id, word)
    await _reopen_panel(message, state)


@router.message(PanelInput.filter_keyword, F.chat.type == 'private', F.text)
async def input_filter_keyword(message: Message, state: FSMContext):
    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    keyword = _input_text(message).casefold()
    if not keyword:
        await message.answer(f"❌ {sc('Send a keyword first.')}")
        return
    if len(keyword) > KEYWORD_MAX:
        await message.answer(f"❌ {sc('Keep the keyword under')} {KEYWORD_MAX} {sc('characters.')}")
        return
    await state.update_data(pending_keyword=keyword)
    await state.set_state(PanelInput.filter_reply)
    await message.answer(
        f"✏️ <b>{sc('Now send the reply text for this filter.')}</b>",
        reply_markup=kb([btn('❌ Cancel', f'cx:fl:{chat_id}')]),
    )


@router.message(PanelInput.filter_reply, F.chat.type == 'private', F.text)
async def input_filter_reply(message: Message, state: FSMContext):
    chat_id = await _active_fsm_chat(message, state)
    if chat_id is None:
        return
    data = await state.get_data()
    keyword = str(data.get('pending_keyword', '')).casefold()
    if not keyword:
        await state.clear()
        await message.answer('⚠️ The filter keyword was missing. Open /settings and try again.')
        return
    await add_filter(chat_id, keyword, (message.html_text or message.text or '')[:4000])
    await _reopen_panel(message, state)
