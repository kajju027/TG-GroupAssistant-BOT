import asyncio
from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from bot.core import database as db
from bot.utils.filters import OwnerFilter
from bot.utils.ui import sc, box, row, sep, bold, mono, link, kb, btn

router = Router()


class BcastState(StatesGroup):
    waiting = State()


async def _resolve_user(message: Message, bot: Bot):
    args = message.text.split(None, 1)
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return u.id, u.username or "", u.full_name
    if len(args) < 2:
        return None, None, None
    target = args[1].strip()
    if target.lstrip("-").isdigit():
        uid = int(target)
        try:
            chat = await bot.get_chat(uid)
            return uid, getattr(chat, "username", "") or "", getattr(chat, "full_name", "") or str(uid)
        except Exception:
            return uid, "", str(uid)
    if target.startswith("@"):
        try:
            chat = await bot.get_chat(target)
            return chat.id, chat.username or "", getattr(chat, "full_name", "") or target
        except Exception:
            return None, None, None
    return None, None, None


@router.message(Command("allow"), OwnerFilter())
async def allow_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, uname, name = await _resolve_user(message, bot)
    if not uid:
        await message.reply(
            box("Allow User", [f"  {sc('Reply to a user or pass ID/@username')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    if uid == message.from_user.id:
        await message.reply(
            box("Allow User", [f"  {sc('You are the owner — no need!')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.add_allowed(uid, uname, name)
    await message.reply(
        box("User Allowed", [
            row("Name", link(name or str(uid), uid), "👤"),
            row("ID",   mono(str(uid)), "🆔"),
            sep(),
            f"  ✅ {sc('Access granted successfully')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("disallow"), OwnerFilter())
async def disallow_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, _, name = await _resolve_user(message, bot)
    if not uid:
        await message.reply(
            box("Disallow User", [f"  {sc('Reply to a user or pass ID/@username')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.del_allowed(uid)
    await message.reply(
        box("Access Revoked", [
            row("ID",   mono(str(uid)), "🆔"),
            sep(),
            f"  🚫 {sc('Access removed')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("block"), OwnerFilter())
async def block_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, _, name = await _resolve_user(message, bot)
    if not uid:
        await message.reply(
            box("Block User", [f"  {sc('Reply to a user or pass ID/@username')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.block_user(uid)
    db.del_allowed(uid)
    await message.reply(
        box("User Blocked", [
            row("ID", mono(str(uid)), "🔒"),
            sep(),
            f"  ❌ {sc('User is now blocked from this bot')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("unblock"), OwnerFilter())
async def unblock_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, _, name = await _resolve_user(message, bot)
    if not uid:
        await message.reply(
            box("Unblock User", [f"  {sc('Reply to a user or pass ID/@username')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.unblock_user(uid)
    await message.reply(
        box("User Unblocked", [
            row("ID", mono(str(uid)), "🔓"),
            sep(),
            f"  ✅ {sc('User can access the bot again')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("users"), OwnerFilter())
async def list_users(message: Message):
    db.inc_stat("commands")
    users = db.get_allowed()
    if not users:
        await message.reply(
            box("Allowed Users", [f"  {sc('No users have been allowed yet')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    lines = []
    for i, u in enumerate(users, 1):
        name = u["first_name"] or "Unknown"
        uid = u["user_id"]
        uname = f"@{u['username']}" if u["username"] else mono(str(uid))
        lines.append(f"  <b>{i}.</b> {link(name, uid)} — {uname}")
    lines.insert(0, row("Total", bold(str(len(users))), "📋"))
    lines.insert(1, sep())
    await message.reply(
        box("Allowed Users", lines),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("stats"), OwnerFilter())
async def show_stats(message: Message):
    db.inc_stat("commands")
    groups = db.all_groups()
    users = db.get_allowed()
    await message.reply(
        box("Bot Statistics", [
            row("Allowed Users",  bold(str(len(users))),                     "👤"),
            row("Groups Active",  bold(str(len(groups))),                    "👥"),
            row("Messages",       bold(str(db.get_stat("messages"))),        "💬"),
            row("Reactions Sent", bold(str(db.get_stat("reactions"))),       "⚡"),
            row("Commands Used",  bold(str(db.get_stat("commands"))),        "📊"),
            row("Music Played",   bold(str(db.get_stat("music"))),           "🎵"),
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("broadcast"), OwnerFilter())
async def start_broadcast(message: Message, state: FSMContext):
    db.inc_stat("commands")
    args = message.text.split(None, 1)
    if len(args) > 1:
        await _do_broadcast(message, args[1], message.bot)
        return
    await message.reply(
        box("Broadcast", [f"  {sc('Send the message you want to broadcast:')}"]),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(BcastState.waiting)


@router.message(BcastState.waiting, OwnerFilter())
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await _do_broadcast(message, message.text or "", bot)


async def _do_broadcast(message: Message, text: str, bot: Bot):
    groups = db.all_groups()
    sent = failed = 0
    status_msg = await message.reply(
        box("Broadcasting", [f"  ⏳ {sc('Sending to')} {bold(str(len(groups)))} {sc('groups')}..."]),
        parse_mode=ParseMode.HTML,
    )
    for g in groups:
        try:
            await bot.send_message(g["chat_id"], text, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await status_msg.edit_text(
        box("Broadcast Complete", [
            row("Sent",   bold(str(sent)),   "✅"),
            row("Failed", bold(str(failed)), "❌"),
        ]),
        parse_mode=ParseMode.HTML,
    )
