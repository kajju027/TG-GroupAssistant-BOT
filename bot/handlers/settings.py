from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.database import (
    get_settings, update_setting, get_banned_words, get_antifake_prefixes,
    get_filters, get_whitelisted_links, add_whitelist_link, remove_whitelist_link,
    add_banned_word, remove_banned_word, add_antifake_prefix, remove_antifake_prefix,
    add_filter, remove_filter,
)
from bot.utils.helpers import is_admin
from bot.states import PanelInput

router = Router()


def _toggle_btn(label: str, state: bool, feature: str, chat_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{label}: {'✅ ON' if state else '❌ OFF'}",
        callback_data=f"toggle:{feature}:{chat_id}:{'off' if state else 'on'}",
    )


async def _check_admin(callback: CallbackQuery, chat_id: int) -> bool:
    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer("❌ You're not an admin in that group!", show_alert=True)
        return False
    return True


def _cb_for(callback: CallbackQuery, new_data: str) -> CallbackQuery:
    return callback.model_copy(update={"data": new_data})


def _cancel_kb(back_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Cancel", callback_data=back_data)]
    ])


@router.callback_query(F.data.startswith("menu:antilink:"))
async def menu_antilink(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    action = s["antilink_action"]
    whitelist = s.get("antilink_whitelist", [])
    domains_text = ", ".join(whitelist) if whitelist else "None"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Link", bool(s["antilink"]), "antilink", chat_id)],
        [InlineKeyboardButton(text=f"Action: {action.upper()}  (tap to cycle)", callback_data=f"cycle:antilink_action:{chat_id}")],
        [InlineKeyboardButton(text="🌐 Allowed Domains", callback_data=f"menu:antilink_domains:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🔗 <b>Anti-Link Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antilink'] else '❌ OFF'}\n"
        f"Action: <b>{action.upper()}</b>\n"
        f"Allowed domains: <code>{domains_text}</code>\n\n"
        f"Cycle order: delete → warn → kick → ban\n"
        f"Links from allowed domains are never touched.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antilink_domains:"))
async def menu_antilink_domains(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    whitelist = await get_whitelisted_links(chat_id)
    domains_text = "\n".join(f"• <code>{d}</code>" for d in whitelist) or "No allowed domains yet."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Domain", callback_data=f"ask:antilink_allow:{chat_id}"),
            InlineKeyboardButton(text="➖ Remove Domain", callback_data=f"ask:antilink_disallow:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:antilink:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🌐 <b>Allowed Domains</b>\n\n{domains_text}\n\n"
        f"Links matching these domains are never deleted by Anti-Link.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antiword:"))
async def menu_antiword(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    words = await get_banned_words(chat_id)
    word_list = ", ".join(words) if words else "None"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Word", bool(s["antiword"]), "antiword", chat_id)],
        [InlineKeyboardButton(text=f"Action: {s['antiword_action'].upper()}  (tap to cycle)", callback_data=f"cycle:antiword_action:{chat_id}")],
        [
            InlineKeyboardButton(text="➕ Add Word", callback_data=f"ask:antiword_add:{chat_id}"),
            InlineKeyboardButton(text="➖ Remove Word", callback_data=f"ask:antiword_remove:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🔤 <b>Anti-Word Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antiword'] else '❌ OFF'}\n"
        f"Action: <b>{s['antiword_action'].upper()}</b>\n"
        f"Banned words: <code>{word_list}</code>",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antispam:"))
async def menu_antispam(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Spam", bool(s["antispam"]), "antispam", chat_id)],
        [
            InlineKeyboardButton(text=f"Limit: {s['antispam_limit']} msgs", callback_data=f"cycle:antispam_limit:{chat_id}"),
            InlineKeyboardButton(text=f"Window: {s['antispam_window']}s", callback_data=f"cycle:antispam_window:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🚫 <b>Anti-Spam Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antispam'] else '❌ OFF'}\n"
        f"Limit: <b>{s['antispam_limit']} messages</b> per <b>{s['antispam_window']}s</b>\n\n"
        f"Tap the buttons above to cycle through values.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antifake:"))
async def menu_antifake(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    prefixes = await get_antifake_prefixes(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Fake", bool(s["antifake"]), "antifake", chat_id)],
        [InlineKeyboardButton(text=f"Mode: {s['antifake_mode'].upper()}  (tap to cycle)", callback_data=f"cycle:antifake_mode:{chat_id}")],
        [
            InlineKeyboardButton(text="➕ Add Prefix", callback_data=f"ask:antifake_add:{chat_id}"),
            InlineKeyboardButton(text="➖ Remove Prefix", callback_data=f"ask:antifake_remove:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    prefix_list = ", ".join(prefixes) if prefixes else "None"
    await callback.message.edit_text(
        f"📵 <b>Anti-Fake Number Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antifake'] else '❌ OFF'}\n"
        f"Mode: <b>{s['antifake_mode'].upper()}</b>\n"
        f"Prefixes: <code>{prefix_list}</code>\n\n"
        f"Blacklist = block listed prefixes\n"
        f"Whitelist = allow ONLY listed prefixes",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:welcome:"))
async def menu_welcome(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            _toggle_btn("Welcome", bool(s["welcome"]), "welcome", chat_id),
            _toggle_btn("Goodbye", bool(s["goodbye"]), "goodbye", chat_id),
        ],
        [
            InlineKeyboardButton(text="✏️ Edit Welcome Text", callback_data=f"ask:welcome_msg:{chat_id}"),
            InlineKeyboardButton(text="✏️ Edit Goodbye Text", callback_data=f"ask:goodbye_msg:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"👋 <b>Welcome / Goodbye Settings</b>\n\n"
        f"Welcome: {'✅ ON' if s['welcome'] else '❌ OFF'}\n"
        f"Goodbye: {'✅ ON' if s['goodbye'] else '❌ OFF'}\n\n"
        f"<b>Welcome message:</b>\n<code>{s['welcome_msg']}</code>\n\n"
        f"<b>Goodbye message:</b>\n<code>{s['goodbye_msg']}</code>\n\n"
        f"<b>Placeholders:</b> {{mention}} {{name}} {{username}} {{group}} {{count}} {{id}}",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:warn:"))
async def menu_warn(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Limit: {s['warn_limit']}  (tap to cycle)", callback_data=f"cycle:warn_limit:{chat_id}"),
            InlineKeyboardButton(text=f"Action: {s['warn_action'].upper()}  (tap)", callback_data=f"cycle:warn_action:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"⚠️ <b>Warn System Settings</b>\n\n"
        f"Max warnings: <b>{s['warn_limit']}</b>\n"
        f"Action on exceed: <b>{s['warn_action'].upper()}</b>",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:mute:"))
async def menu_mute(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "🔇 <b>Mute</b>\n\n"
        "Use /mute and /unmute in the group to mute/unmute the whole "
        "group, or reply to a user with /mute [1m/1h/1d] to mute just "
        "them.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:reaction:"))
async def menu_reaction(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    mode = s.get("reaction_mode", "automatic")
    emojis = s.get("reaction_emojis", ["👍"])
    emoji_text = " ".join(emojis) if mode == "custom" else "(auto-picked from popular reactions)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Auto-Reaction", bool(s["reaction_enabled"]), "reaction_enabled", chat_id)],
        [
            InlineKeyboardButton(
                text=f"{'✅' if mode == 'automatic' else '⬜'} Automatic",
                callback_data=f"reactmode:automatic:{chat_id}",
            ),
            InlineKeyboardButton(
                text=f"{'✅' if mode == 'custom' else '⬜'} Custom",
                callback_data=f"reactmode:custom:{chat_id}",
            ),
        ],
        [InlineKeyboardButton(text="✏️ Edit Custom Emojis", callback_data=f"ask:reaction_emojis:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "🎭 <b>Auto-Reaction Settings</b>\n\n"
        f"Status: {'✅ ON' if s['reaction_enabled'] else '❌ OFF'}\n"
        f"Mode: <b>{mode.upper()}</b>\n"
        f"Emojis: {emoji_text}\n\n"
        "<b>Automatic</b> — the bot picks from a curated set of good "
        "reactions on its own.\n"
        "<b>Custom</b> — you choose the emoji list; each new post cycles "
        "to the next one in order.\n\n"
        "Works on every post in the group or channel, no matter who "
        "sent it (including admins), a few seconds after it arrives.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:filters:"))
async def menu_filters(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    filters = await get_filters(chat_id)
    filter_text = "\n".join(f"• <code>{f['keyword']}</code>" for f in filters) or "No filters set."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Filter", callback_data=f"ask:filter_add:{chat_id}"),
            InlineKeyboardButton(text="➖ Remove Filter", callback_data=f"ask:filter_remove:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🔍 <b>Custom Filters ({len(filters)})</b>\n\n{filter_text}",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_setting(callback: CallbackQuery, state: FSMContext):
    _, feature, chat_id_str, new_state = callback.data.split(":")
    chat_id = int(chat_id_str)
    if not await _check_admin(callback, chat_id):
        return
    val = new_state == "on"
    await update_setting(chat_id, feature, val)
    await callback.answer(f"{'✅ Enabled' if val else '❌ Disabled'}: {feature.replace('_', ' ')}")
    _menu_feature = "welcome" if feature == "goodbye" else feature
    _menu_map = {
        "antilink": menu_antilink,
        "antiword": menu_antiword,
        "antispam": menu_antispam,
        "antifake": menu_antifake,
        "welcome": menu_welcome,
        "warn": menu_warn,
        "reaction_enabled": menu_reaction,
    }
    if _menu_feature in _menu_map:
        await _menu_map[_menu_feature](_cb_for(callback, f"menu:{_menu_feature}:{chat_id}"), state)


@router.callback_query(F.data.startswith("reactmode:"))
async def set_reaction_mode(callback: CallbackQuery, state: FSMContext):
    _, mode, chat_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)
    if not await _check_admin(callback, chat_id):
        return
    await update_setting(chat_id, "reaction_mode", mode)
    await callback.answer(f"Mode → {mode.upper()}")
    await menu_reaction(_cb_for(callback, f"menu:reaction:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:antilink_action:"))
async def cycle_antilink_action(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["delete", "warn", "kick", "ban"]
    cur = s["antilink_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "delete"
    await update_setting(chat_id, "antilink_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_antilink(_cb_for(callback, f"menu:antilink:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:antiword_action:"))
async def cycle_antiword_action(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["delete", "warn", "kick", "ban"]
    cur = s["antiword_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "delete"
    await update_setting(chat_id, "antiword_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_antiword(_cb_for(callback, f"menu:antiword:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:antifake_mode:"))
async def cycle_antifake_mode(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    modes = ["blacklist", "whitelist"]
    cur = s["antifake_mode"]
    nxt = modes[(modes.index(cur) + 1) % len(modes)] if cur in modes else "blacklist"
    await update_setting(chat_id, "antifake_mode", nxt)
    await callback.answer(f"Mode → {nxt.upper()}")
    await menu_antifake(_cb_for(callback, f"menu:antifake:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:antispam_limit:"))
async def cycle_antispam_limit(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [3, 5, 7, 10, 15, 20]
    cur = s["antispam_limit"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 5
    await update_setting(chat_id, "antispam_limit", nxt)
    await callback.answer(f"Limit → {nxt} msgs")
    await menu_antispam(_cb_for(callback, f"menu:antispam:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:antispam_window:"))
async def cycle_antispam_window(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [5, 10, 15, 30, 60]
    cur = s["antispam_window"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 10
    await update_setting(chat_id, "antispam_window", nxt)
    await callback.answer(f"Window → {nxt}s")
    await menu_antispam(_cb_for(callback, f"menu:antispam:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:warn_limit:"))
async def cycle_warn_limit(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [2, 3, 5, 7, 10]
    cur = s["warn_limit"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 3
    await update_setting(chat_id, "warn_limit", nxt)
    await callback.answer(f"Warn limit → {nxt}")
    await menu_warn(_cb_for(callback, f"menu:warn:{chat_id}"), state)


@router.callback_query(F.data.startswith("cycle:warn_action:"))
async def cycle_warn_action(callback: CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["kick", "ban", "mute"]
    cur = s["warn_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "kick"
    await update_setting(chat_id, "warn_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_warn(_cb_for(callback, f"menu:warn:{chat_id}"), state)


_ASK_CONFIG = {
    "antilink_allow": (PanelInput.antilink_allow_domain, "Send the domain to allow (e.g. <code>youtube.com</code>)", "menu:antilink_domains:"),
    "antilink_disallow": (PanelInput.antilink_disallow_domain, "Send the domain to remove from the allowed list", "menu:antilink_domains:"),
    "antiword_add": (PanelInput.antiword_add_word, "Send the word to ban", "menu:antiword:"),
    "antiword_remove": (PanelInput.antiword_remove_word, "Send the word to remove from the banned list", "menu:antiword:"),
    "antifake_add": (PanelInput.antifake_add_prefix, "Send the phone prefix to add (e.g. <code>+92</code>)", "menu:antifake:"),
    "antifake_remove": (PanelInput.antifake_remove_prefix, "Send the phone prefix to remove", "menu:antifake:"),
    "welcome_msg": (PanelInput.welcome_message, "Send the new welcome message.\n\nPlaceholders: {mention} {name} {username} {group} {count} {id}", "menu:welcome:"),
    "goodbye_msg": (PanelInput.goodbye_message, "Send the new goodbye message.\n\nPlaceholders: {mention} {name} {username} {group} {count} {id}", "menu:welcome:"),
    "reaction_emojis": (PanelInput.reaction_custom_emojis, "Send your emoji list separated by commas, e.g.\n<code>🔥, 🌚, 👀, 🎉</code>", "menu:reaction:"),
    "filter_add": (PanelInput.filter_add_keyword, "Send the keyword that should trigger this filter (e.g. <code>fc</code>)", "menu:filters:"),
    "filter_remove": (PanelInput.filter_remove_keyword, "Send the keyword of the filter to remove", "menu:filters:"),
}


@router.callback_query(F.data.startswith("ask:"))
async def ask_for_input(callback: CallbackQuery, state: FSMContext):
    _, kind, chat_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)
    if not await _check_admin(callback, chat_id):
        return
    target_state, prompt, back_prefix = _ASK_CONFIG[kind]
    await state.set_state(target_state)
    await state.update_data(chat_id=chat_id, back_data=f"{back_prefix}{chat_id}", back_prefix=back_prefix)
    await callback.message.edit_text(
        f"✏️ {prompt}\n\n<i>Reply to this chat with your answer, or tap Cancel.</i>",
        reply_markup=_cancel_kb(f"{back_prefix}{chat_id}"),
    )


@router.message(PanelInput.antilink_allow_domain, F.chat.type == "private")
async def input_antilink_allow(message, state: FSMContext):
    from bot.utils.helpers import extract_domain
    data = await state.get_data()
    chat_id = data["chat_id"]
    domain = extract_domain(message.text.strip())
    await add_whitelist_link(chat_id, domain)
    await state.clear()
    await message.answer(f"✅ <code>{domain}</code> added to allowed domains.")
    await _reopen_menu(message, chat_id, "menu:antilink_domains:")


@router.message(PanelInput.antilink_disallow_domain, F.chat.type == "private")
async def input_antilink_disallow(message, state: FSMContext):
    from bot.utils.helpers import extract_domain
    data = await state.get_data()
    chat_id = data["chat_id"]
    domain = extract_domain(message.text.strip())
    await remove_whitelist_link(chat_id, domain)
    await state.clear()
    await message.answer(f"✅ <code>{domain}</code> removed from allowed domains.")
    await _reopen_menu(message, chat_id, "menu:antilink_domains:")


@router.message(PanelInput.antiword_add_word, F.chat.type == "private")
async def input_antiword_add(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    word = message.text.strip().lower()
    await add_banned_word(chat_id, word)
    await state.clear()
    await message.answer(f"✅ <code>{word}</code> added to banned words.")
    await _reopen_menu(message, chat_id, "menu:antiword:")


@router.message(PanelInput.antiword_remove_word, F.chat.type == "private")
async def input_antiword_remove(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    word = message.text.strip().lower()
    await remove_banned_word(chat_id, word)
    await state.clear()
    await message.answer(f"✅ <code>{word}</code> removed from banned words.")
    await _reopen_menu(message, chat_id, "menu:antiword:")


@router.message(PanelInput.antifake_add_prefix, F.chat.type == "private")
async def input_antifake_add(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    prefix = message.text.strip()
    prefix = prefix if prefix.startswith("+") else "+" + prefix
    await add_antifake_prefix(chat_id, prefix)
    await state.clear()
    await message.answer(f"✅ <code>{prefix}</code> added.")
    await _reopen_menu(message, chat_id, "menu:antifake:")


@router.message(PanelInput.antifake_remove_prefix, F.chat.type == "private")
async def input_antifake_remove(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    prefix = message.text.strip()
    prefix = prefix if prefix.startswith("+") else "+" + prefix
    await remove_antifake_prefix(chat_id, prefix)
    await state.clear()
    await message.answer(f"✅ <code>{prefix}</code> removed.")
    await _reopen_menu(message, chat_id, "menu:antifake:")


@router.message(PanelInput.welcome_message, F.chat.type == "private")
async def input_welcome_msg(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    await update_setting(chat_id, "welcome_msg", message.html_text or message.text)
    await state.clear()
    await message.answer("✅ Welcome message updated.")
    await _reopen_menu(message, chat_id, "menu:welcome:")


@router.message(PanelInput.goodbye_message, F.chat.type == "private")
async def input_goodbye_msg(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    await update_setting(chat_id, "goodbye_msg", message.html_text or message.text)
    await state.clear()
    await message.answer("✅ Goodbye message updated.")
    await _reopen_menu(message, chat_id, "menu:welcome:")


@router.message(PanelInput.reaction_custom_emojis, F.chat.type == "private")
async def input_reaction_emojis(message, state: FSMContext):
    from bot.handlers.reactions import ALLOWED_EMOJI
    data = await state.get_data()
    chat_id = data["chat_id"]
    candidates = [e.strip() for e in message.text.split(",") if e.strip()]
    valid = [e for e in candidates if e in ALLOWED_EMOJI]
    invalid = [e for e in candidates if e not in ALLOWED_EMOJI]
    if not valid:
        await message.answer("❌ None of those are supported reaction emojis. Try again.")
        return
    await update_setting(chat_id, "reaction_emojis", valid)
    await update_setting(chat_id, "reaction_mode", "custom")
    await update_setting(chat_id, "_reaction_index", 0)
    await state.clear()
    msg = f"✅ Custom emojis set: {' '.join(valid)}"
    if invalid:
        msg += f"\n⚠️ Skipped unsupported: {' '.join(invalid)}"
    await message.answer(msg)
    await _reopen_menu(message, chat_id, "menu:reaction:")


@router.message(PanelInput.filter_add_keyword, F.chat.type == "private")
async def input_filter_keyword(message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(pending_keyword=message.text.strip().lower())
    await state.set_state(PanelInput.filter_add_reply)
    await message.answer(
        "Now send the reply text this filter should send.",
        reply_markup=_cancel_kb(f"menu:filters:{data['chat_id']}"),
    )


@router.message(PanelInput.filter_add_reply, F.chat.type == "private")
async def input_filter_reply(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    keyword = data["pending_keyword"]
    reply_text = message.html_text or message.text
    await add_filter(chat_id, keyword, reply_text)
    await state.clear()
    await message.answer(f"✅ Filter added: <code>{keyword}</code>")
    await _reopen_menu(message, chat_id, "menu:filters:")


@router.message(PanelInput.filter_remove_keyword, F.chat.type == "private")
async def input_filter_remove(message, state: FSMContext):
    data = await state.get_data()
    chat_id = data["chat_id"]
    keyword = message.text.strip().lower()
    await remove_filter(chat_id, keyword)
    await state.clear()
    await message.answer(f"✅ Filter <code>{keyword}</code> removed.")
    await _reopen_menu(message, chat_id, "menu:filters:")


class _NullState:
    async def clear(self):
        pass

    async def set_state(self, *_a, **_kw):
        pass

    async def get_data(self):
        return {}

    async def update_data(self, **_kw):
        pass


async def _reopen_menu(message, chat_id: int, menu_prefix: str):
    menu_map = {
        "menu:antilink_domains:": menu_antilink_domains,
        "menu:antiword:": menu_antiword,
        "menu:antifake:": menu_antifake,
        "menu:welcome:": menu_welcome,
        "menu:reaction:": menu_reaction,
        "menu:filters:": menu_filters,
    }
    handler = menu_map.get(menu_prefix)
    if not handler:
        return
    sent = await message.answer("⏳")
    fake_cb = CallbackQuery(
        id="internal",
        from_user=message.from_user,
        chat_instance="internal",
        data=f"{menu_prefix}{chat_id}",
        message=sent,
    )
    object.__setattr__(fake_cb, "_bot", message.bot)
    try:
        await handler(fake_cb, _NullState())
    except Exception:
        pass
