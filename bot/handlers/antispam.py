from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import (
    get_settings, update_setting,
    get_spam_count, increment_spam, reset_spam
)
from bot.utils.helpers import is_admin as check_is_admin

router = Router()

@router.message(Command("antispam"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_antispam(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = "✅ ON" if s["antispam"] else "❌ OFF"
        await message.answer(
            f"🚫 <b>Anti-Spam:</b> {status}\n"
            f"Limit: <b>{s['antispam_limit']} messages</b>\n"
            f"Window: <b>{s['antispam_window']} seconds</b>\n\n"
            "Usage: /antispam on|off|limit [n]|window [s]"
        )
        return
    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "antispam", 1)
        await message.answer("✅ Anti-spam <b>enabled</b>.")
    elif cmd == "off":
        await update_setting(message.chat.id, "antispam", 0)
        await message.answer("❌ Anti-spam <b>disabled</b>.")
    elif cmd == "limit" and len(parts) > 2:
        try:
            n = int(parts[2])
            if n < 2 or n > 50:
                raise ValueError
            await update_setting(message.chat.id, "antispam_limit", n)
            await message.answer(f"✅ Spam limit set to <b>{n} messages</b>.")
        except ValueError:
            await message.answer("❌ Enter a number between 2 and 50.")
    elif cmd == "window" and len(parts) > 2:
        try:
            n = int(parts[2])
            if n < 5 or n > 300:
                raise ValueError
            await update_setting(message.chat.id, "antispam_window", n)
            await message.answer(f"✅ Spam window set to <b>{n} seconds</b>.")
        except ValueError:
            await message.answer("❌ Enter seconds between 5 and 300.")
    else:
        await message.answer("Usage: /antispam on|off|limit [n]|window [seconds]")


# Registered AFTER the command handler above. Also excludes any text
# starting with "/" so it never swallows a command intended for other
# routers (commands like /warn, /mute, /settings would otherwise never
# get a chance to run, since this handler used to match ALL messages
# with no text filter at all). Requires F.text so non-text messages
# (photos, stickers, etc. with no caption) don't fall through here.
@router.message(F.chat.type.in_({"group", "supergroup"}), F.text, ~F.text.startswith("/"))
async def check_spam(message: Message):
    if not message.from_user:
        return
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    s = await get_settings(message.chat.id)
    if not s["antispam"]:
        return
    uid = message.from_user.id
    chat_id = message.chat.id
    limit = s["antispam_limit"]
    window = s["antispam_window"]
    cur_count = await get_spam_count(chat_id, uid, window)
    new_count = await increment_spam(chat_id, uid)
    if new_count >= limit:
        name = message.from_user.full_name
        await reset_spam(chat_id, uid)
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(f"🚫 <b>{name}</b> is spamming! Muting for 5 minutes.")
        from aiogram.types import ChatPermissions
        import datetime
        try:
            await message.bot.restrict_chat_member(
                chat_id, uid,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.datetime.now() + datetime.timedelta(minutes=5)
            )
        except Exception:
            pass
