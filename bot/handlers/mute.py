import re
import datetime
from aiogram import Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command
from bot.utils.helpers import is_admin as check_is_admin, get_user_from_message

router = Router()

# ─── aiogram v3 compatible permissions ───────────────────────
ALL_PERMS_OFF = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
)

ALL_PERMS_ON = ChatPermissions(
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
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)


def _parse_time(time_str: str):
    match = re.match(r"^(\d+)([smhd])$", time_str.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return {
        "s": datetime.timedelta(seconds=value),
        "m": datetime.timedelta(minutes=value),
        "h": datetime.timedelta(hours=value),
        "d": datetime.timedelta(days=value),
    }.get(unit)


@router.message(Command("mute"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_mute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, ALL_PERMS_OFF)
            await message.answer("🔇 Group <b>muted</b>. Only admins can speak.")
        except Exception as e:
            await message.answer(f"❌ Failed: {e}")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer("❌ Cannot mute an admin.")
        return
    parts = message.text.split()
    duration = None
    time_str = None
    for p in parts[2:]:
        td = _parse_time(p)
        if td:
            duration = td
            time_str = p
            break
    until = datetime.datetime.now() + duration if duration else None
    try:
        await message.bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ALL_PERMS_OFF,
            until_date=until,
        )
        dur_text = f" for <b>{time_str}</b>" if time_str else " indefinitely"
        await message.answer(f"🔇 {mention} has been muted{dur_text}.")
    except Exception as e:
        await message.answer(f"❌ Failed to mute: {e}")


@router.message(Command("unmute"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unmute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, ALL_PERMS_ON)
            await message.answer("🔊 Group <b>unmuted</b>. Everyone can speak now.")
        except Exception as e:
            await message.answer(f"❌ Failed: {e}")
        return
    try:
        await message.bot.restrict_chat_member(message.chat.id, uid, permissions=ALL_PERMS_ON)
        await message.answer(f"🔊 {mention} has been unmuted.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("kick"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_kick(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer("❌ Cannot kick an admin.")
        return
    try:
        await message.bot.ban_chat_member(message.chat.id, uid)
        await message.bot.unban_chat_member(message.chat.id, uid)
        await message.answer(f"🚪 {mention} was kicked.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("ban"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_ban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer("❌ Cannot ban an admin.")
        return
    parts = message.text.split()
    duration = None
    time_str = None
    for p in parts[2:]:
        td = _parse_time(p)
        if td:
            duration = td
            time_str = p
            break
    until = datetime.datetime.now() + duration if duration else None
    try:
        await message.bot.ban_chat_member(message.chat.id, uid, until_date=until)
        dur_text = f" for <b>{time_str}</b>" if time_str else " permanently"
        await message.answer(f"🔨 {mention} was banned{dur_text}.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("unban"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    try:
        await message.bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
        await message.answer(f"✅ {mention} has been unbanned.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("promote"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_promote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True,
        )
        await message.answer(f"👑 {mention} has been promoted to admin.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("demote"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_demote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer("❌ Reply to a user or mention them.")
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_video_chats=False,
        )
        await message.answer(f"📉 {mention} has been demoted.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("pin"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_pin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Reply to the message you want to pin.")
        return
    try:
        await message.bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await message.answer("📌 Message pinned.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@router.message(Command("unpin"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unpin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    try:
        if message.reply_to_message:
            await message.bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
        else:
            await message.bot.unpin_chat_message(message.chat.id)
        await message.answer("📌 Message unpinned.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")
