from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from bot.database import get_settings, list_managed_chats
from bot.utils.helpers import is_admin, settings_main_kb, is_message_sender_admin, groups_picker_kb
router = Router()

async def _render_group_picker(user_id: int) -> tuple:
    chats = await list_managed_chats(user_id)
    if not chats:
        text = '👋 <b>No managed groups found yet.</b>\n\nAdd me to a group or channel as an <b>admin</b>, then send /start there once. After that, this menu will show it here for you to manage.'
        return (text, None)
    text = '🗂 <b>Your Groups & Channels</b>\n\nSelect one to open its settings panel:'
    return (text, groups_picker_kb(chats))

@router.message(CommandStart(), F.chat.type.in_({'group', 'supergroup'}))
async def start_group(message: Message):
    await get_settings(message.chat.id)
    me = await message.bot.get_me()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⚙️ Manage in DM', url=f'https://t.me/{me.username}?start=panel')]])
    await message.answer(f'✅ <b>Activated in {message.chat.title}!</b>\n\nOpen my DM to configure every setting from one clean panel.', reply_markup=kb)

@router.message(CommandStart(), F.chat.type == 'private')
async def start_dm(message: Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('settings_'):
        try:
            chat_id = int(args[1].replace('settings_', ''))
        except ValueError:
            await message.answer('❌ Invalid group ID.')
            return
        if not await is_admin(message.bot, chat_id, message.from_user.id):
            await message.answer('❌ You must be an admin in that group to access its settings.')
            return
        try:
            chat = await message.bot.get_chat(chat_id)
            chat_name = chat.title
        except Exception:
            chat_name = str(chat_id)
        await message.answer(f'⚙️ <b>Settings Panel</b>\nGroup: <b>{chat_name}</b>\n\nChoose a feature to configure:', reply_markup=settings_main_kb(chat_id))
        return
    text, kb = await _render_group_picker(message.from_user.id)
    if kb is None:
        me = await message.bot.get_me()
        await message.answer(
            f"👋 Hello! I'm <b>{me.first_name}</b>, a group management bot.\n\n"
            f"➕ Add me to your group or channel as an <b>admin</b>.\n"
            f"📋 Then send /start here again to open your management panel.\n\n"
            f"<b>Commands:</b>\n/start — open your groups panel\n/help — show all commands"
        )
        return
    await message.answer(text, reply_markup=kb)

@router.message(Command('settings'), F.chat.type.in_({'group', 'supergroup'}))
async def settings_from_group(message: Message):
    if not await is_message_sender_admin(message):
        await message.answer('❌ Admins only.')
        return
    me = await message.bot.get_me()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⚙️ Open Settings Panel', url=f'https://t.me/{me.username}?start=settings_{message.chat.id}')]])
    await message.answer("Tap below to manage this group's settings in DM:", reply_markup=kb)

@router.message(Command('settings'), F.chat.type == 'private')
async def settings_dm(message: Message):
    text, kb = await _render_group_picker(message.from_user.id)
    await message.answer(text, reply_markup=kb)

@router.message(Command('help'))
async def help_cmd(message: Message):
    text = "<b>📋 Command List</b>\n\n<b>👥 Group Commands (Admin only):</b>\n/settings — Open settings panel in DM\n/warn [reply/@user] — Warn a user\n/unwarn [reply/@user] — Remove last warning\n/warns [reply/@user] — Check warnings\n/kick [reply/@user] — Kick a user\n/ban [reply/@user] — Ban a user\n/unban [reply/@user] — Unban a user\n/mute [reply/@user] [time] — Mute a user\n/unmute [reply/@user] — Unmute a user\n/promote [reply/@user] — Promote to admin\n/demote [reply/@user] — Demote admin\n/tag [all/admin] [msg] — Tag members\n/antilink [on/off] — Toggle anti-link\n/antiword [add/remove/list] — Manage banned words\n/antispam [on/off] [limit] — Toggle anti-spam\n/antifake [on/off] — Toggle anti-fake\n/filter [keyword] [reply] — Add filter\n/filters — List all filters\n/stop [keyword] — Remove filter\n/welcome [on/off] — Toggle welcome\n/setwelcome [text] — Set welcome message\n/setgoodbye [text] — Set goodbye message\n/mute — Mute the entire group\n/unmute — Unmute the entire group\n/pin [reply] — Pin a message\n/unpin — Unpin message\n/kick — Kick without ban\n/reaction [on/off] — Toggle auto-reaction\n/reaction emoji [emoji1 emoji2 ...] — Set reaction emoji(s)\n   (works in groups AND channels)\n\n<b>🔒 Privacy:</b> only that group's own admins/owner can manage it."
    await message.answer(text)

@router.callback_query(F.data == 'close')
async def close_panel(callback: CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data == 'panel:list')
async def panel_list(callback: CallbackQuery):
    text, kb = await _render_group_picker(callback.from_user.id)
    if kb is None:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Close', callback_data='close')]])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith('panel:open:'))
async def panel_open(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer("❌ You're not an admin in that group anymore.", show_alert=True)
        return
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_name = chat.title
    except Exception:
        chat_name = str(chat_id)
    await callback.message.edit_text(f'⚙️ <b>Settings Panel</b>\nGroup: <b>{chat_name}</b>\n\nChoose a feature to configure:', reply_markup=settings_main_kb(chat_id))

@router.callback_query(F.data.startswith('menu:main:'))
async def back_to_main(callback: CallbackQuery):
    chat_id = int(callback.data.split(':')[2])
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_name = chat.title
    except Exception:
        chat_name = str(chat_id)
    await callback.message.edit_text(f'⚙️ <b>Settings Panel</b>\nGroup: <b>{chat_name}</b>\n\nChoose a feature to configure:', reply_markup=settings_main_kb(chat_id))
