from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.utils.helpers import is_admin

router = Router()

@router.message(Command("tag"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_tag(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=2)
    mode = parts[1].lower() if len(parts) > 1 else "all"
    custom_msg = parts[2] if len(parts) > 2 else ""

    try:
        members = await message.bot.get_chat_administrators(message.chat.id)
    except Exception as e:
        await message.answer(f"❌ Failed to fetch members: {e}")
        return

    if mode == "admin":
        targets = [m.user for m in members if not m.user.is_bot]
        label = "👑 Admins"
    elif mode == "notadmin":
        admin_ids = {m.user.id for m in members}
        label = "👥 Members"
        await message.answer(
            "⚠️ Tagging all non-admins requires fetching all members, which Telegram API does not support directly. "
            "Only admins can be tagged via API. Use /tag all or /tag admin instead."
        )
        return
    else:
        targets = [m.user for m in members if not m.user.is_bot]
        label = "📢 All Members"

    mentions = " ".join(
        f"<a href='tg://user?id={u.id}'>\u200b</a>" for u in targets
    )
    text = f"{label}\n{custom_msg}\n{mentions}" if custom_msg else f"{label}\n{mentions}"
    await message.answer(text)
