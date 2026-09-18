from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_settings, update_setting, get_warnings, add_warning, reset_warnings
from bot.utils.helpers import is_admin as check_is_admin, get_user_from_message

router = Router()

async def _apply_warn_action(message: Message, user_id: int, action: str, name: str):
    if action == "kick":
        await message.answer(f"🚪 <b>{name}</b> was kicked for exceeding warn limit.")
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
            await message.bot.unban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    elif action == "ban":
        await message.answer(f"🔨 <b>{name}</b> was banned for exceeding warn limit.")
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    elif action == "mute":
        from aiogram.types import ChatPermissions
        import datetime
        await message.answer(f"🔇 <b>{name}</b> was muted for exceeding warn limit.")
        try:
            await message.bot.restrict_chat_member(
                message.chat.id, user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.datetime.now() + datetime.timedelta(hours=1)
            )
        except Exception:
            pass

@router.message(Command("warn"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warn(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer("❌ Cannot warn an admin.")
        return
    parts = message.text.split(maxsplit=2)
    reason = parts[-1] if len(parts) > 2 and not parts[-1].startswith("@") else "No reason given"
    s = await get_settings(message.chat.id)
    count = await add_warning(message.chat.id, uid, reason)
    limit = s["warn_limit"]
    if count >= limit:
        await message.answer(
            f"⚠️ {mention} has reached the warn limit ({count}/{limit})!\n"
            f"Action: <b>{s['warn_action'].upper()}</b>"
        )
        await _apply_warn_action(message, uid, s["warn_action"], name)
        await reset_warnings(message.chat.id, uid)
    else:
        await message.answer(
            f"⚠️ <b>Warning {count}/{limit}</b>\n"
            f"User: {mention}\n"
            f"Reason: {reason}"
        )

@router.message(Command("unwarn"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unwarn(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    warns = await get_warnings(message.chat.id, uid)
    if not warns:
        await message.answer(f"✅ {mention} has no warnings.")
        return
    from bot.database import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE id=(SELECT id FROM warnings WHERE chat_id=? AND user_id=? ORDER BY created_at DESC LIMIT 1)",
            (message.chat.id, uid)
        )
        await db.commit()
    remaining = len(warns) - 1
    await message.answer(f"✅ Removed 1 warning from {mention}. Remaining: <b>{remaining}</b>")

@router.message(Command("warns"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warns(message: Message):
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        if message.from_user is None:
            # Anonymous admin ran /warns with no reply/mention - there's no
            # user to check warnings for.
            await message.answer("❌ Reply to a user or mention them.")
            return
        uid = message.from_user.id
        mention = message.from_user.mention_html()
        name = message.from_user.full_name
    s = await get_settings(message.chat.id)
    warns = await get_warnings(message.chat.id, uid)
    if not warns:
        await message.answer(f"✅ {mention} has no warnings.")
        return
    text = f"⚠️ <b>Warnings for {mention}: {len(warns)}/{s['warn_limit']}</b>\n\n"
    for i, w in enumerate(warns, 1):
        text += f"{i}. {w['reason']} — <i>{w['created_at'][:16]}</i>\n"
    await message.answer(text)

@router.message(Command("resetwarns"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_resetwarns(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    await reset_warnings(message.chat.id, uid)
    await message.answer(f"✅ All warnings reset for {mention}.")

@router.message(Command("warnlimit"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warnlimit(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        await message.answer(f"Current warn limit: <b>{s['warn_limit']}</b>\nUsage: /warnlimit [number]")
        return
    try:
        n = int(parts[1])
        if n < 1 or n > 20:
            raise ValueError
        await update_setting(message.chat.id, "warn_limit", n)
        await message.answer(f"✅ Warn limit set to <b>{n}</b>.")
    except ValueError:
        await message.answer("❌ Enter a number between 1 and 20.")

@router.message(Command("warnaction"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warnaction(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        await message.answer(f"Current action: <b>{s['warn_action'].upper()}</b>\nUsage: /warnaction kick|ban|mute")
        return
    action = parts[1].lower()
    if action not in ("kick", "ban", "mute"):
        await message.answer("❌ Valid: kick, ban, mute")
        return
    await update_setting(message.chat.id, "warn_action", action)
    await message.answer(f"✅ Warn action set to <b>{action.upper()}</b>.")
