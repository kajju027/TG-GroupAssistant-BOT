from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from bot.database import get_settings, update_setting
from bot.utils.helpers import is_admin

router = Router()

def _format_msg(template: str, user, chat) -> str:
    count = chat.member_count if hasattr(chat, "member_count") else "?"
    return (
        template
        .replace("{name}", user.full_name)
        .replace("{username}", f"@{user.username}" if user.username else user.full_name)
        .replace("{group}", chat.title)
        .replace("{count}", str(count))
        .replace("{id}", str(user.id))
    )

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated):
    s = await get_settings(event.chat.id)
    if not s["welcome"]:
        return
    user = event.new_chat_member.user
    chat = event.chat
    text = _format_msg(s["welcome_msg"], user, chat)
    await event.bot.send_message(
        event.chat.id,
        f"👋 {user.mention_html()}\n\n{text}"
    )

@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_leave(event: ChatMemberUpdated):
    s = await get_settings(event.chat.id)
    if not s["goodbye"]:
        return
    user = event.old_chat_member.user
    chat = event.chat
    text = _format_msg(s["goodbye_msg"], user, chat)
    await event.bot.send_message(event.chat.id, f"👋 {text}")

@router.message(Command("welcome"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_welcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = "✅ ON" if s["welcome"] else "❌ OFF"
        await message.answer(
            f"👋 <b>Welcome:</b> {status}\n"
            f"Message: <code>{s['welcome_msg']}</code>\n\n"
            "Usage: /welcome on|off"
        )
        return
    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "welcome", 1)
        await message.answer("✅ Welcome messages <b>enabled</b>.")
    elif cmd == "off":
        await update_setting(message.chat.id, "welcome", 0)
        await message.answer("❌ Welcome messages <b>disabled</b>.")

@router.message(Command("goodbye"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_goodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = "✅ ON" if s["goodbye"] else "❌ OFF"
        await message.answer(
            f"👋 <b>Goodbye:</b> {status}\n"
            f"Message: <code>{s['goodbye_msg']}</code>\n\n"
            "Usage: /goodbye on|off"
        )
        return
    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "goodbye", 1)
        await message.answer("✅ Goodbye messages <b>enabled</b>.")
    elif cmd == "off":
        await update_setting(message.chat.id, "goodbye", 0)
        await message.answer("❌ Goodbye messages <b>disabled</b>.")

@router.message(Command("setwelcome"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_setwelcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Usage: /setwelcome [text]\n\n"
            "Variables: {name} {username} {group} {count} {id}"
        )
        return
    await update_setting(message.chat.id, "welcome_msg", parts[1])
    await message.answer(f"✅ Welcome message updated:\n\n<code>{parts[1]}</code>")

@router.message(Command("setgoodbye"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_setgoodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setgoodbye [text]\n\nVariables: {name} {username} {group}")
        return
    await update_setting(message.chat.id, "goodbye_msg", parts[1])
    await message.answer(f"✅ Goodbye message updated:\n\n<code>{parts[1]}</code>")
