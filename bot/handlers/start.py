from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from bot.database import get_settings, init_db
from bot.utils.helpers import is_admin, settings_main_kb

router = Router()

@router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
async def start_group(message: Message):
    await get_settings(message.chat.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⚙️ Open Settings Panel",
            url=f"https://t.me/{(await message.bot.get_me()).username}?start=settings_{message.chat.id}"
        )
    ]])
    await message.answer(
        f"✅ <b>Bot activated in {message.chat.title}!</b>\n\n"
        "Click the button below to open the settings panel in my DM.",
        reply_markup=kb
    )

@router.message(CommandStart(), F.chat.type == "private")
async def start_dm(message: Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("settings_"):
        try:
            chat_id = int(args[1].replace("settings_", ""))
        except ValueError:
            await message.answer("❌ Invalid group ID.")
            return

        if not await is_admin(message.bot, chat_id, message.from_user.id):
            await message.answer("❌ You must be an admin in that group to access settings.")
            return

        try:
            chat = await message.bot.get_chat(chat_id)
            chat_name = chat.title
        except Exception:
            chat_name = str(chat_id)

        await message.answer(
            f"⚙️ <b>Settings Panel</b>\n"
            f"Group: <b>{chat_name}</b>\n\n"
            "Choose a feature to configure:",
            reply_markup=settings_main_kb(chat_id)
        )
    else:
        me = await message.bot.get_me()
        await message.answer(
            f"👋 Hello! I'm <b>{me.first_name}</b>, a powerful group management bot.\n\n"
            "➕ Add me to your group and send /start there to activate.\n\n"
            "<b>Available Commands:</b>\n"
            "/settings - Open settings panel\n"
            "/help - Show all commands"
        )

@router.message(Command("settings"), F.chat.type.in_({"group", "supergroup"}))
async def settings_from_group(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("❌ Admins only.")
        return
    me = await message.bot.get_me()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⚙️ Open Settings Panel",
            url=f"https://t.me/{me.username}?start=settings_{message.chat.id}"
        )
    ]])
    await message.answer("Click below to manage settings in DM:", reply_markup=kb)

@router.message(Command("settings"), F.chat.type == "private")
async def settings_dm(message: Message):
    await message.answer(
        "Please use /start from a group to open the settings panel for that group.",
    )

@router.message(Command("help"))
async def help_cmd(message: Message):
    text = (
        "<b>📋 Command List</b>\n\n"
        "<b>👥 Group Commands (Admin only):</b>\n"
        "/settings - Open settings panel in DM\n"
        "/warn [reply/@user] - Warn a user\n"
        "/unwarn [reply/@user] - Remove last warning\n"
        "/warns [reply/@user] - Check warnings\n"
        "/kick [reply/@user] - Kick a user\n"
        "/ban [reply/@user] - Ban a user\n"
        "/unban [reply/@user] - Unban a user\n"
        "/mute [reply/@user] [time] - Mute a user\n"
        "/unmute [reply/@user] - Unmute a user\n"
        "/promote [reply/@user] - Promote to admin\n"
        "/demote [reply/@user] - Demote admin\n"
        "/tag [all/admin] [msg] - Tag members\n"
        "/antilink [on/off] - Toggle anti-link\n"
        "/antiword [add/remove/list] - Manage banned words\n"
        "/antispam [on/off] [limit] - Toggle anti-spam\n"
        "/antifake [on/off] - Toggle anti-fake\n"
        "/filter [keyword] [reply] - Add filter\n"
        "/filters - List all filters\n"
        "/stop [keyword] - Remove filter\n"
        "/welcome [on/off] - Toggle welcome\n"
        "/setwelcome [text] - Set welcome message\n"
        "/setgoodbye [text] - Set goodbye message\n"
        "/mute - Mute the group\n"
        "/unmute - Unmute the group\n"
        "/pin [reply] - Pin a message\n"
        "/unpin - Unpin message\n"
        "/kick - Kick without ban\n"
    )
    await message.answer(text)

@router.callback_query(F.data == "close")
async def close_panel(callback: CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data.startswith("menu:main:"))
async def back_to_main(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[2])
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_name = chat.title
    except Exception:
        chat_name = str(chat_id)
    await callback.message.edit_text(
        f"⚙️ <b>Settings Panel</b>\nGroup: <b>{chat_name}</b>\n\nChoose a feature to configure:",
        reply_markup=settings_main_kb(chat_id)
    )
