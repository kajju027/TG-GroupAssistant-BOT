from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.core import database as db
from bot.core.config import CONFETTI_FX, HEART_FX, OWNER_ID
from bot.utils import anim
from bot.utils.filters import NotBlockedFilter
from bot.utils.ui import bold, box, btn, italic, kb, link, quote, row, sc, sep, ubtn

router = Router()

_DL_CMDS = box('Downloads', [row('YouTube Audio', '/play &lt;song/url&gt;', '🎧'), row('YouTube Video', '/video &lt;query/url&gt;', '🎬'), row('X / Twitter', '/tw &lt;url&gt;', '𝕏'), row('Instagram', '/ig &lt;url&gt;', '📸'), row('Facebook', '/fb &lt;url&gt;', '📘'), row('TeraBox', '/tb &lt;url&gt;', '📦'), row('Pinterest', '/pinterest &lt;url&gt;', '📌'), sep(), f"  💡 {italic(sc('Send a supported URL in private chat for auto-detect'))}"])
_GROUP_CMDS = box('Group Management', [row('Settings panel', '/settings', '⚙️'), row('Anti-link', '/antilink on | off', '🔗'), row('Anti-word', '/antiword add &lt;word&gt;', '🔤'), row('Anti-spam', '/antispam on | off', '🚫'), row('Welcome', '/welcome, /setwelcome', '👋'), row('Goodbye', '/goodbye, /setgoodbye', '🚪'), row('Tag everyone', '/everyone &lt;message&gt;', '📣'), row('Tag admins', '/tag admin &lt;message&gt;', '👑'), row('Warnings', '/warn, /unwarn, /warns', '⚠️'), row('Moderation', '/mute, /ban, /kick, /pin', '🛡️'), row('Filters', '/filter, /filters, /stop', '🔎'), row('Reaction', '/reaction on | off', '🎭')])
_OWNER_CMDS = box('Owner Panel', [row('Allow User', '/allow &lt;id/@user&gt;', '👤'), row('Disallow', '/disallow &lt;id/@user&gt;', '🚫'), row('Block', '/block &lt;id/@user&gt;', '🔒'), row('Unblock', '/unblock &lt;id/@user&gt;', '🔓'), row('Users List', '/users', '📋'), row('Broadcast', '/broadcast &lt;text&gt;', '📢'), row('Stats', '/stats', '📊')])


def _start_text(user_id: int, name: str) -> str:
    if user_id == OWNER_ID:
        return box('Group Assistant', [
            f"  👑 {bold(sc('Owner'))} — {link(name, user_id)}",
            sep(),
            quote(sc('All systems ready. Full access granted.')),
            sep(),
            f"  ✨ {sc('Tap a button below to navigate')}",
        ])
    if db.is_allowed(user_id):
        return box('Group Assistant', [
            f"  ✅ {bold(sc('Access Granted'))} — {link(name, user_id)}",
            sep(),
            quote(sc('You can use the private downloader.')),
            sep(),
            f"  ✨ {sc('Tap a button below to navigate')}",
        ])
    return box('Group Assistant', [
        f"  🔒 {bold(sc('Private downloads'))}",
        sep(),
        quote(sc('Group admins can use /settings inside their groups.')),
        quote(sc('Contact the owner for private downloader access.')),
    ])


def _add_group_button(username: str | None):
    if username:
        return ubtn('➕ Add To Group', f'https://t.me/{username}?startgroup=assistant')
    return btn('⚙️ Group Settings', 'menu:help:group')


def _start_kb(user_id: int, username: str | None):
    first = [btn('📋 Commands', 'menu:help')]
    if user_id == OWNER_ID:
        first.append(btn('📊 Stats', 'show_stats'))
    else:
        first.append(btn('ℹ️ About', 'menu:about'))
    second = [_add_group_button(username)]
    if user_id == OWNER_ID:
        second.append(btn('ℹ️ About', 'menu:about'))
    return kb(first, second)


def _hub_kb(user_id: int):
    second_row = [btn('🛡️ Group Management', 'menu:help:group')]
    if user_id == OWNER_ID:
        second_row.append(btn('👑 Owner', 'menu:help:owner'))
    return kb(
        [btn('⬇️ Downloads', 'menu:help:dl')],
        second_row,
        [btn('🔙 Back', 'menu:start')],
    )


def _back_kb(data: str = 'menu:help'):
    return kb([btn('🔙 Back', data)])


def _help_hub_text(user_id: int) -> str:
    lines = [row('Downloads', sc('Media downloader suite'), '⬇️'), row('Group Management', sc('Moderation and automation'), '🛡️')]
    if user_id == OWNER_ID:
        lines.append(row('Owner Panel', sc('Full bot control'), '👑'))
    lines += [sep(), f"  ✨ {italic(sc('Pick a section to view its commands'))}"]
    return box('Command Center', lines)


def _about_text(user_id: int, name: str) -> str:
    lines = [
        row('Bot', bold(sc('Group Assistant')), '🤖'),
        row('Engine', bold(sc('aiogram 3 - async python')), '⚙️'),
        row('Style', bold(sc('Small caps fonts')), '✨'),
        row('Motion', bold(sc('Multi reaction animations')), '🎬'),
        sep(),
        quote(sc('Moderation, welcome, reactions, downloads and filters in one assistant.')),
    ]
    if user_id == OWNER_ID:
        lines.append(f"  👑 {sc('Signed in as owner')} — {link(name, user_id)}")
    return box('About', lines)


def _stats_text() -> str:
    groups = db.all_groups()
    allowed = db.get_allowed()
    return box('Bot Statistics', [
        row('Allowed Users', bold(str(len(allowed))), '👤'),
        row('Groups Active', bold(str(len(groups))), '👥'),
        row('Messages', bold(str(db.get_stat('messages'))), '💬'),
        row('Reactions', bold(str(db.get_stat('reactions'))), '⚡'),
        row('Downloads', bold(str(db.get_stat('downloads'))), '⬇️'),
        row('Commands Used', bold(str(db.get_stat('commands'))), '📊'),
        sep(),
        f"  🔄 {italic(sc('Tap refresh to update the numbers'))}",
    ])


async def _edit_menu(callback: CallbackQuery, text: str, markup=None) -> None:
    message = callback.message
    if message is None:
        return
    if hasattr(message, 'edit_text'):
        try:
            await message.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest as error:
            if 'message is not modified' in str(error).casefold():
                return
    try:
        await message.answer(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


@router.message(CommandStart(), NotBlockedFilter())
async def cmd_start(message: Message, is_admin: bool = False):
    db.inc_stat('commands')
    user = message.from_user
    user_id = user.id
    name = user.full_name
    if message.chat.type in {'group', 'supergroup'}:
        if is_admin:
            markup = kb([btn('⚙️ Settings', f"menu:main:{message.chat.id}"), btn('📋 Commands', 'menu:help:group')])
            await message.answer('✅ <b>Group Assistant is ready.</b>', reply_markup=markup)
        else:
            await message.answer('👋 Add me as an administrator, then ask a group admin to use /settings.')
        return
    username = None
    try:
        me = await message.bot.me()
        username = me.username
    except Exception:
        try:
            me = await message.bot.get_me()
            username = me.username
        except Exception:
            username = None
    effect = HEART_FX if user_id == OWNER_ID else (CONFETTI_FX if db.is_allowed(user_id) else None)
    await anim.play(
        message,
        _start_text(user_id, name),
        kind='sparkle',
        reply_markup=_start_kb(user_id, username),
        message_effect_id=effect,
    )


@router.callback_query(lambda query: query.data == 'menu:start')
async def cb_start_menu(callback: CallbackQuery):
    user = callback.from_user
    username = None
    try:
        username = (await callback.bot.me()).username
    except Exception:
        pass
    await callback.answer()
    await _edit_menu(callback, _start_text(user.id, user.full_name), _start_kb(user.id, username))


@router.callback_query(lambda query: query.data in {'menu:help', 'help_cmds'})
async def cb_help_hub(callback: CallbackQuery):
    await callback.answer()
    await _edit_menu(callback, _help_hub_text(callback.from_user.id), _hub_kb(callback.from_user.id))


@router.callback_query(lambda query: query.data == 'menu:help:dl')
async def cb_help_dl(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != OWNER_ID and not db.is_allowed(user_id):
        await callback.answer('You do not have downloader access.', show_alert=True)
        return
    await callback.answer()
    await _edit_menu(callback, _DL_CMDS, _back_kb())


@router.callback_query(lambda query: query.data == 'menu:help:group')
async def cb_help_group(callback: CallbackQuery):
    await callback.answer()
    await _edit_menu(callback, _GROUP_CMDS, _back_kb())


@router.callback_query(lambda query: query.data == 'menu:help:owner')
async def cb_help_owner(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer('Owner only section.', show_alert=True)
        return
    await callback.answer()
    await _edit_menu(callback, _OWNER_CMDS, _back_kb())


@router.callback_query(lambda query: query.data == 'menu:about')
async def cb_about(callback: CallbackQuery):
    await callback.answer()
    await _edit_menu(callback, _about_text(callback.from_user.id, callback.from_user.full_name), _back_kb('menu:start'))


@router.callback_query(lambda query: query.data in {'show_stats', 'refresh_stats'})
async def cb_stats(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer('Owner only section.', show_alert=True)
        return
    await callback.answer()
    await _edit_menu(callback, _stats_text(), kb([btn('🔄 Refresh', 'refresh_stats'), btn('🔙 Back', 'menu:start')]))


@router.message(Command('help'), NotBlockedFilter())
async def cmd_help(message: Message, is_admin: bool = False):
    db.inc_stat('commands')
    if message.chat.type in {'group', 'supergroup'}:
        if not is_admin:
            await message.answer('ℹ️ Only group admins can use the moderation controls. Ask an admin to use /settings.')
            return
        markup = kb([btn('⚙️ Settings', f"menu:main:{message.chat.id}"), btn('⬇️ Downloads', 'menu:help:dl')])
        await anim.play(message, _GROUP_CMDS, kind='sparkle', reply_markup=markup)
        return
    user_id = message.from_user.id
    await anim.play(message, _help_hub_text(user_id), kind='sparkle', reply_markup=_hub_kb(user_id))
