import asyncio
from datetime import timedelta
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from bot.core import database as db
from bot.core.config import MAX_WARNS, OWNER_ID
from bot.utils.filters import AllowedFilter
from bot.utils.ui import sc, box, row, sep, bold, mono, italic, link, quote

router = Router()

_GRP = F.chat.type.in_({"group", "supergroup"})


async def _target(message: Message, bot: Bot):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        return None, None
    t = parts[1].strip().split()[0]
    if t.lstrip("-").isdigit():
        uid = int(t)
        try:
            m = await bot.get_chat_member(message.chat.id, uid)
            return uid, m.user.full_name
        except Exception:
            return uid, str(uid)
    if t.startswith("@"):
        try:
            chat = await bot.get_chat(t)
            return chat.id, getattr(chat, "full_name", t)
        except Exception:
            return None, None
    return None, None


def _reason(message: Message, skip: int = 1) -> str:
    parts = message.text.split(None, skip + 1)
    return parts[-1] if len(parts) > skip + 1 else sc("No reason provided")


async def _bot_admin(message: Message, bot: Bot) -> bool:
    try:
        m = await bot.get_chat_member(message.chat.id, bot.id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False


def _is_privileged(uid: int) -> bool:
    return uid == OWNER_ID or db.is_allowed(uid)


@router.message(Command("ban"), AllowedFilter(), _GRP)
async def ban_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    if not await _bot_admin(message, bot):
        await message.reply(box("Ban 🔨", [f"  ⚠️ {sc('I need admin rights')}"]), parse_mode=ParseMode.HTML)
        return
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Ban 🔨", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    if _is_privileged(uid):
        await message.reply(box("Ban 🔨", [f"  🛡️ {sc('Cannot ban a privileged user')}"]), parse_mode=ParseMode.HTML)
        return
    reason = _reason(message)
    try:
        await bot.ban_chat_member(message.chat.id, uid)
        await message.reply(
            box("User Banned 🔨", [
                row("User",   link(name, uid), "🔨"),
                row("ID",     mono(str(uid)),  "🆔"),
                row("Reason", reason,          "📝"),
                sep(),
                quote(sc("User has been permanently banned.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply(box("Ban Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("unban"), AllowedFilter(), _GRP)
async def unban_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Unban ✅", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    try:
        await bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
        await message.reply(
            box("User Unbanned ✅", [
                row("User", link(name, uid), "✅"),
                row("ID",   mono(str(uid)),  "🆔"),
                sep(),
                quote(sc("User can rejoin the group.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply(box("Unban Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("kick"), AllowedFilter(), _GRP)
async def kick_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    if not await _bot_admin(message, bot):
        await message.reply(box("Kick 👢", [f"  ⚠️ {sc('I need admin rights')}"]), parse_mode=ParseMode.HTML)
        return
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Kick 👢", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    if _is_privileged(uid):
        await message.reply(box("Kick 👢", [f"  🛡️ {sc('Cannot kick a privileged user')}"]), parse_mode=ParseMode.HTML)
        return
    try:
        await bot.ban_chat_member(message.chat.id, uid)
        await asyncio.sleep(0.4)
        await bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
        await message.reply(
            box("User Kicked 👢", [
                row("User", link(name, uid), "👢"),
                row("ID",   mono(str(uid)),  "🆔"),
                sep(),
                quote(sc("User removed from the group.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply(box("Kick Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("mute"), AllowedFilter(), _GRP)
async def mute_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    if not await _bot_admin(message, bot):
        await message.reply(box("Mute 🔇", [f"  ⚠️ {sc('I need admin rights')}"]), parse_mode=ParseMode.HTML)
        return
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Mute 🔇", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    if _is_privileged(uid):
        await message.reply(box("Mute 🔇", [f"  🛡️ {sc('Cannot mute a privileged user')}"]), parse_mode=ParseMode.HTML)
        return
    minutes = None
    for part in message.text.split()[1:]:
        if part.isdigit():
            minutes = int(part)
            break
    until = timedelta(minutes=minutes) if minutes else None
    try:
        await bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        dur = f"{minutes} {sc('min')}" if minutes else sc("indefinite")
        await message.reply(
            box("User Muted 🔇", [
                row("User",     link(name, uid), "🔇"),
                row("ID",       mono(str(uid)),  "🆔"),
                row("Duration", bold(dur),       "⏱️"),
                sep(),
                quote(sc("User cannot send messages.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply(box("Mute Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("unmute"), AllowedFilter(), _GRP)
async def unmute_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Unmute 🔊", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    try:
        await bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await message.reply(
            box("User Unmuted 🔊", [
                row("User", link(name, uid), "🔊"),
                row("ID",   mono(str(uid)),  "🆔"),
                sep(),
                quote(sc("User can speak again.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply(box("Unmute Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("warn"), AllowedFilter(), _GRP)
async def warn_user(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Warn ⚠️", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    if _is_privileged(uid):
        await message.reply(box("Warn ⚠️", [f"  🛡️ {sc('Cannot warn a privileged user')}"]), parse_mode=ParseMode.HTML)
        return
    reason = _reason(message)
    count  = db.add_warn(uid, message.chat.id, reason)
    lines  = [
        row("User",   link(name, uid),              "⚠️"),
        row("Reason", reason,                       "📝"),
        row("Count",  bold(f"{count}/{MAX_WARNS}"), "📊"),
    ]
    if count >= MAX_WARNS:
        lines += [sep(), quote(sc("Max warnings reached — auto-ban applied."))]
        await message.reply(box("User Warned ⚠️", lines), parse_mode=ParseMode.HTML)
        try:
            await bot.ban_chat_member(message.chat.id, uid)
            db.clear_warns(uid, message.chat.id)
        except Exception:
            pass
    else:
        await message.reply(box("User Warned ⚠️", lines), parse_mode=ParseMode.HTML)


@router.message(Command("warns"), AllowedFilter())
async def check_warns(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Warns 📋", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    warns = db.get_warns(uid, message.chat.id)
    if not warns:
        await message.reply(
            box("Warnings 📋", [
                row("User",  link(name, uid), "👤"),
                row("Count", bold("0"),        "✅"),
                sep(),
                quote(sc("No warnings on record.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    lines = [row("User", link(name, uid), "👤"), row("Count", bold(f"{len(warns)}/{MAX_WARNS}"), "⚠️"), sep()]
    for i, w in enumerate(warns, 1):
        lines.append(f"  <b>{i}.</b> {w['reason']} — {italic(w['warned_at'][:10])}")
    await message.reply(box("Warning History ⚠️", lines), parse_mode=ParseMode.HTML)


@router.message(Command("resetwarns"), AllowedFilter())
async def reset_warns(message: Message, bot: Bot):
    db.inc_stat("commands")
    uid, name = await _target(message, bot)
    if not uid:
        await message.reply(box("Reset Warns 🔄", [f"  {sc('Reply to a user or provide ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    db.clear_warns(uid, message.chat.id)
    await message.reply(
        box("Warns Reset 🔄", [
            row("User", link(name, uid), "🔄"),
            sep(),
            quote(sc("All warnings cleared.")),
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("pin"), AllowedFilter(), _GRP)
async def pin_msg(message: Message, bot: Bot):
    db.inc_stat("commands")
    if not message.reply_to_message:
        await message.reply(box("Pin 📌", [f"  {sc('Reply to a message to pin it')}"]), parse_mode=ParseMode.HTML)
        return
    try:
        await bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await message.reply(box("Pinned 📌", [f"  {quote(sc('Message has been pinned.'))}"]), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply(box("Pin Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("unpin"), AllowedFilter(), _GRP)
async def unpin_msg(message: Message, bot: Bot):
    db.inc_stat("commands")
    try:
        mid = message.reply_to_message.message_id if message.reply_to_message else None
        await bot.unpin_chat_message(message.chat.id, mid)
        await message.reply(box("Unpinned 📍", [f"  {quote(sc('Message unpinned.'))}"]), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply(box("Unpin Failed ❌", [f"  {mono(str(e)[:120])}"]), parse_mode=ParseMode.HTML)


@router.message(Command("setwelcome"), AllowedFilter(), _GRP)
async def set_welcome(message: Message):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            box("Set Welcome 👋", [
                row("Usage",       "/setwelcome &lt;text&gt;",            "📖"),
                sep(),
                row("{name}",      sc("user mention"),                    "▸"),
                row("{group}",     sc("group name"),                      "▸"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.ensure_group(message.chat.id, message.chat.title or "")
    db.set_welcome_text(message.chat.id, parts[1])
    db.toggle_welcome(message.chat.id, True)
    await message.reply(
        box("Welcome Set ✅", [
            quote(parts[1][:120] + ("…" if len(parts[1]) > 120 else "")),
            sep(),
            f"  ✅ {sc('Welcome messages enabled')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("welcome"), AllowedFilter(), _GRP)
async def toggle_welcome_cmd(message: Message):
    db.inc_stat("commands")
    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        await message.reply(box("Welcome 🔔", [f"  {sc('Usage:')} /welcome on | off"]), parse_mode=ParseMode.HTML)
        return
    on = args[1].lower() == "on"
    db.ensure_group(message.chat.id, message.chat.title or "")
    db.toggle_welcome(message.chat.id, on)
    state = f"✅ {sc('Enabled')}" if on else f"❌ {sc('Disabled')}"
    await message.reply(
        box("Welcome 🔔", [
            f"  {sc('Welcome messages')} — {bold(state)}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.new_chat_members)
async def welcome_member(message: Message):
    db.ensure_group(message.chat.id, message.chat.title or "")
    group = db.get_group(message.chat.id)
    if not group or not group["welcome_enabled"] or not group["welcome_text"]:
        return
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        text = group["welcome_text"]
        text = text.replace("{name}", link(member.full_name, member.id))
        text = text.replace("{group}", message.chat.title or "")
        await message.answer(text, parse_mode=ParseMode.HTML)
