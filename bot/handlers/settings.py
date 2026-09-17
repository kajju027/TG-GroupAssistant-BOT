from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database import get_settings, update_setting
from bot.utils.helpers import settings_main_kb, is_admin

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


# ─── helper: re-show a sub-menu by cloning callback with new data ─
def _cb_for(callback: CallbackQuery, new_data: str) -> CallbackQuery:
    return callback.model_copy(update={"data": new_data})


# ═══════════════════════════════════════════════════════════════
# SUB-MENUS
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("menu:antilink:"))
async def menu_antilink(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    action = s["antilink_action"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Link", bool(s["antilink"]), "antilink", chat_id)],
        [InlineKeyboardButton(text=f"Action: {action.upper()} (tap to cycle)", callback_data=f"cycle:antilink_action:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "🔗 <b>Anti-Link Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antilink'] else '❌ OFF'}\n"
        f"Action: <b>{action.upper()}</b>\n\n"
        "Cycle order: delete → warn → kick → ban",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antiword:"))
async def menu_antiword(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    from bot.database import get_banned_words
    words = await get_banned_words(chat_id)
    word_list = ", ".join(words) if words else "None"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Word", bool(s["antiword"]), "antiword", chat_id)],
        [InlineKeyboardButton(text=f"Action: {s['antiword_action'].upper()} (tap to cycle)", callback_data=f"cycle:antiword_action:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "🔤 <b>Anti-Word Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antiword'] else '❌ OFF'}\n"
        f"Action: <b>{s['antiword_action'].upper()}</b>\n"
        f"Banned words: <code>{word_list}</code>\n\n"
        "<b>Commands in group:</b>\n"
        "/antiword add [word]\n"
        "/antiword remove [word]\n"
        "/antiword list",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antispam:"))
async def menu_antispam(callback: CallbackQuery):
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
        "🚫 <b>Anti-Spam Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antispam'] else '❌ OFF'}\n"
        f"Limit: <b>{s['antispam_limit']} messages</b> per <b>{s['antispam_window']}s</b>\n\n"
        "Tap buttons to cycle values.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:antifake:"))
async def menu_antifake(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    from bot.database import get_antifake_prefixes
    prefixes = await get_antifake_prefixes(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_toggle_btn("Anti-Fake", bool(s["antifake"]), "antifake", chat_id)],
        [InlineKeyboardButton(text=f"Mode: {s['antifake_mode'].upper()} (tap to cycle)", callback_data=f"cycle:antifake_mode:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    prefix_list = ", ".join(prefixes) if prefixes else "None"
    await callback.message.edit_text(
        "📵 <b>Anti-Fake Number Settings</b>\n\n"
        f"Status: {'✅ ON' if s['antifake'] else '❌ OFF'}\n"
        f"Mode: <b>{s['antifake_mode'].upper()}</b>\n"
        f"Prefixes: <code>{prefix_list}</code>\n\n"
        "<b>Commands:</b>\n"
        "/antifake add [+prefix]\n"
        "/antifake remove [+prefix]\n"
        "/antifake list\n\n"
        "blacklist = block listed prefixes\n"
        "whitelist = allow ONLY listed prefixes",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:welcome:"))
async def menu_welcome(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            _toggle_btn("Welcome", bool(s["welcome"]), "welcome", chat_id),
            _toggle_btn("Goodbye", bool(s["goodbye"]), "goodbye", chat_id),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "👋 <b>Welcome / Goodbye Settings</b>\n\n"
        f"Welcome: {'✅ ON' if s['welcome'] else '❌ OFF'}\n"
        f"Goodbye: {'✅ ON' if s['goodbye'] else '❌ OFF'}\n\n"
        f"<b>Welcome msg:</b>\n<code>{s['welcome_msg']}</code>\n\n"
        f"<b>Goodbye msg:</b>\n<code>{s['goodbye_msg']}</code>\n\n"
        "<b>Variables:</b> {name} {username} {group} {count} {id}\n\n"
        "<b>Commands in group:</b>\n"
        "/setwelcome [text]\n"
        "/setgoodbye [text]",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:warn:"))
async def menu_warn(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Limit: {s['warn_limit']} (tap to cycle)", callback_data=f"cycle:warn_limit:{chat_id}"),
            InlineKeyboardButton(text=f"Action: {s['warn_action'].upper()} (tap)", callback_data=f"cycle:warn_action:{chat_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "⚠️ <b>Warn System Settings</b>\n\n"
        f"Max warnings: <b>{s['warn_limit']}</b>\n"
        f"Action on exceed: <b>{s['warn_action'].upper()}</b>\n\n"
        "<b>Commands:</b>\n"
        "/warn [reply/@user] [reason]\n"
        "/unwarn [reply/@user]\n"
        "/warns [reply/@user]\n"
        "/resetwarns [reply/@user]",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:mute:"))
async def menu_mute(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        "🔇 <b>Mute Settings</b>\n\n"
        "<b>Commands:</b>\n"
        "/mute — mute entire group\n"
        "/unmute — unmute entire group\n"
        "/mute @user [1m/1h/1d] — mute a user\n"
        "/unmute @user — unmute a user",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("menu:filters:"))
async def menu_filters(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    from bot.database import get_filters
    filters = await get_filters(chat_id)
    filter_text = "\n".join([f"• <code>{f['keyword']}</code>" for f in filters]) or "No filters set."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"menu:main:{chat_id}")],
    ])
    await callback.message.edit_text(
        f"🔍 <b>Custom Filters ({len(filters)})</b>\n\n"
        f"{filter_text}\n\n"
        "<b>Commands:</b>\n"
        "/filter [keyword] [reply]\n"
        "/filters — list all\n"
        "/stop [keyword] — remove",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════════════════════
# TOGGLE  (on/off buttons)
# Uses model_copy to avoid Pydantic v2 immutability error
# ═══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("toggle:"))
async def toggle_setting(callback: CallbackQuery):
    _, feature, chat_id_str, new_state = callback.data.split(":")
    chat_id = int(chat_id_str)
    if not await _check_admin(callback, chat_id):
        return

    val = 1 if new_state == "on" else 0
    await update_setting(chat_id, feature, val)
    await callback.answer(f"{'✅ Enabled' if val else '❌ Disabled'}: {feature}")

    # Map feature → its menu handler + data string
    _menu_feature = "welcome" if feature == "goodbye" else feature
    _menu_map = {
        "antilink": (menu_antilink, f"menu:antilink:{chat_id}"),
        "antiword":  (menu_antiword,  f"menu:antiword:{chat_id}"),
        "antispam":  (menu_antispam,  f"menu:antispam:{chat_id}"),
        "antifake":  (menu_antifake,  f"menu:antifake:{chat_id}"),
        "welcome":   (menu_welcome,   f"menu:welcome:{chat_id}"),
        "warn":      (menu_warn,      f"menu:warn:{chat_id}"),
    }
    if _menu_feature in _menu_map:
        handler, new_data = _menu_map[_menu_feature]
        await handler(_cb_for(callback, new_data))


# ═══════════════════════════════════════════════════════════════
# CYCLE  (rotate through values)
# ═══════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("cycle:antilink_action:"))
async def cycle_antilink_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["delete", "warn", "kick", "ban"]
    cur = s["antilink_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "delete"
    await update_setting(chat_id, "antilink_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_antilink(_cb_for(callback, f"menu:antilink:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:antiword_action:"))
async def cycle_antiword_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["delete", "warn", "kick", "ban"]
    cur = s["antiword_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "delete"
    await update_setting(chat_id, "antiword_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_antiword(_cb_for(callback, f"menu:antiword:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:antifake_mode:"))
async def cycle_antifake_mode(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    modes = ["blacklist", "whitelist"]
    cur = s["antifake_mode"]
    nxt = modes[(modes.index(cur) + 1) % len(modes)] if cur in modes else "blacklist"
    await update_setting(chat_id, "antifake_mode", nxt)
    await callback.answer(f"Mode → {nxt.upper()}")
    await menu_antifake(_cb_for(callback, f"menu:antifake:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:antispam_limit:"))
async def cycle_antispam_limit(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [3, 5, 7, 10, 15, 20]
    cur = s["antispam_limit"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 5
    await update_setting(chat_id, "antispam_limit", nxt)
    await callback.answer(f"Limit → {nxt} msgs")
    await menu_antispam(_cb_for(callback, f"menu:antispam:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:antispam_window:"))
async def cycle_antispam_window(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [5, 10, 15, 30, 60]
    cur = s["antispam_window"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 10
    await update_setting(chat_id, "antispam_window", nxt)
    await callback.answer(f"Window → {nxt}s")
    await menu_antispam(_cb_for(callback, f"menu:antispam:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:warn_limit:"))
async def cycle_warn_limit(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = [2, 3, 5, 7, 10]
    cur = s["warn_limit"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else 3
    await update_setting(chat_id, "warn_limit", nxt)
    await callback.answer(f"Warn limit → {nxt}")
    await menu_warn(_cb_for(callback, f"menu:warn:{chat_id}"))


@router.callback_query(F.data.startswith("cycle:warn_action:"))
async def cycle_warn_action(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    if not await _check_admin(callback, chat_id):
        return
    s = await get_settings(chat_id)
    options = ["kick", "ban", "mute"]
    cur = s["warn_action"]
    nxt = options[(options.index(cur) + 1) % len(options)] if cur in options else "kick"
    await update_setting(chat_id, "warn_action", nxt)
    await callback.answer(f"Action → {nxt.upper()}")
    await menu_warn(_cb_for(callback, f"menu:warn:{chat_id}"))
