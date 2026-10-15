from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from bot.core import database as db
from bot.core.config import HEART_FX, OWNER_ID
from bot.utils.filters import NotBlockedFilter
from bot.utils.ui import bold, box, btn, italic, kb, link, quote, row, sc, sep
router = Router()
_DL_CMDS = box('Downloads', [row('YouTube Audio', '/play &lt;song/url&gt;', '🎧'), row('YouTube Video', '/video &lt;query/url&gt;', '🎬'), row('X / Twitter', '/tw &lt;url&gt;', '𝕏'), row('Instagram', '/ig &lt;url&gt;', '📸'), row('Facebook', '/fb &lt;url&gt;', '📘'), row('TeraBox', '/tb &lt;url&gt;', '📦'), row('Pinterest', '/pinterest &lt;url&gt;', '📌'), sep(), f"  💡 {italic(sc('Send a supported URL in private chat for auto-detect'))}"])
_GROUP_CMDS = box('Group Management', [row('Settings panel', '/settings', '⚙️'), row('Anti-link', '/antilink on | off', '🔗'), row('Anti-word', '/antiword add &lt;word&gt;', '🔤'), row('Anti-spam', '/antispam on | off', '🚫'), row('Welcome', '/welcome, /setwelcome', '👋'), row('Warnings', '/warn, /unwarn, /warns', '⚠️'), row('Moderation', '/mute, /ban, /kick, /pin', '🛡️'), row('Filters', '/filter, /filters, /stop', '🔎'), row('Reaction', '/reaction on | off', '🎭'), row('Tag admins', '/tag admin &lt;message&gt;', '📣')])
_OWNER_CMDS = box('Owner Panel', [row('Allow User', '/allow &lt;id/@user&gt;', '👤'), row('Disallow', '/disallow &lt;id/@user&gt;', '🚫'), row('Block', '/block &lt;id/@user&gt;', '🔒'), row('Unblock', '/unblock &lt;id/@user&gt;', '🔓'), row('Users List', '/users', '📋'), row('Broadcast', '/broadcast &lt;text&gt;', '📢'), row('Stats', '/stats', '📊')])

async def _send_group_help(message: Message) -> None:
    await message.answer(_GROUP_CMDS, parse_mode=ParseMode.HTML)
    await message.answer('<i>For moderation commands I must be a group administrator with the required Telegram permissions.</i>')

@router.message(CommandStart(), NotBlockedFilter())
async def cmd_start(message: Message, is_admin: bool=False):
    db.inc_stat('commands')
    user_id = message.from_user.id
    name = message.from_user.full_name
    if message.chat.type in {'group', 'supergroup'}:
        if is_admin:
            await message.answer('✅ <b>Group Assistant is ready.</b> Use /settings to configure this group.')
        else:
            await message.answer('👋 Add me as an administrator, then ask a group admin to use /settings.')
        return
    if user_id == OWNER_ID:
        text = box('Group Assistant Bot', [f"  👑 {bold(sc('Owner'))} — {link(name, user_id)}", sep(), quote(sc('All systems ready. Full access granted.')), sep(), f"  {sc('Use /help to view commands')}"])
        markup = kb([btn('📋 Commands', 'help_cmds'), btn('📊 Stats', 'show_stats')])
    elif db.is_allowed(user_id):
        text = box('Group Assistant Bot', [f"  ✅ {bold(sc('Access Granted'))} — {link(name, user_id)}", sep(), quote(sc('You can use the private downloader.')), sep(), f"  {sc('Use /help to view commands')}"])
        markup = kb([btn('📋 Commands', 'help_cmds')])
    else:
        text = box('Group Assistant Bot', [f"  🔒 {bold(sc('Private downloads'))}", sep(), quote(sc('Group admins can use /settings inside their groups.')), quote(sc('Contact the owner for private downloader access.'))])
        markup = None
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=markup, message_effect_id=HEART_FX if user_id == OWNER_ID else None)

@router.callback_query(lambda query: query.data in {'help_cmds', 'show_stats'})
async def cb_help(callback: CallbackQuery):
    await callback.answer()
    if callback.data == 'show_stats':
        groups = db.all_groups()
        allowed = db.get_allowed()
        await callback.message.answer(box('Bot Statistics', [row('Allowed Users', bold(str(len(allowed))), '👤'), row('Groups Active', bold(str(len(groups))), '👥'), row('Messages', bold(str(db.get_stat('messages'))), '💬'), row('Reactions', bold(str(db.get_stat('reactions'))), '⚡'), row('Downloads', bold(str(db.get_stat('downloads'))), '⬇️'), row('Commands Used', bold(str(db.get_stat('commands'))), '📊')]), parse_mode=ParseMode.HTML)
        return
    user_id = callback.from_user.id
    if user_id == OWNER_ID:
        await callback.message.answer(_OWNER_CMDS, parse_mode=ParseMode.HTML)
    if user_id == OWNER_ID or db.is_allowed(user_id):
        await callback.message.answer(_DL_CMDS, parse_mode=ParseMode.HTML)
    await callback.message.answer(_GROUP_CMDS, parse_mode=ParseMode.HTML)

@router.message(Command('help'), NotBlockedFilter())
async def cmd_help(message: Message, is_admin: bool=False):
    db.inc_stat('commands')
    if message.chat.type in {'group', 'supergroup'}:
        if not is_admin:
            await message.answer('ℹ️ Only group admins can use the moderation controls. Ask an admin to use /settings.')
            return
        await _send_group_help(message)
        return
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        await message.answer(_OWNER_CMDS, parse_mode=ParseMode.HTML)
    if user_id == OWNER_ID or db.is_allowed(user_id):
        await message.answer(_DL_CMDS, parse_mode=ParseMode.HTML)
    await message.answer(_GROUP_CMDS, parse_mode=ParseMode.HTML)
