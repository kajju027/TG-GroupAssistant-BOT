from __future__ import annotations

import datetime
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from bot.utils import anim
from bot.utils.helpers import get_user_from_message, is_admin as check_is_admin

router = Router()

ALL_PERMS_OFF = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_video_notes=False, can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False, can_change_info=False, can_invite_users=False, can_pin_messages=False)
ALL_PERMS_ON = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=False, can_invite_users=True, can_pin_messages=False)

_TIME_RE = re.compile(r'^(\d{1,4})([smhd])$')


def _parse_time(value: str):
    match = _TIME_RE.match((value or '').strip().lower())
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0 or amount > 366:
        return None
    unit = match.group(2)
    table = {
        's': datetime.timedelta(seconds=amount),
        'm': datetime.timedelta(minutes=amount),
        'h': datetime.timedelta(hours=amount),
        'd': datetime.timedelta(days=amount),
    }
    return table[unit]


def _find_duration(parts, start: int = 1):
    for part in parts[start:]:
        parsed = _parse_time(part)
        if parsed is not None:
            return parsed, part
    return None, None


def _future(delta) -> datetime.datetime | None:
    if delta is None:
        return None
    return datetime.datetime.now(datetime.timezone.utc) + delta


async def _default_group_permissions(message: Message) -> ChatPermissions:
    try:
        chat = await message.bot.get_chat(message.chat.id)
        if chat.permissions is not None:
            return chat.permissions
    except Exception:
        pass
    return ALL_PERMS_ON


@router.message(Command('mute'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_mute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, ALL_PERMS_OFF)
            await anim.play(message, '🔇 <b>Group muted.</b> Only admins can speak now.', kind='mute', delay=anim.FAST_DELAY)
        except Exception as e:
            await message.answer(f'❌ <b>Failed:</b> {e}')
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer('❌ <b>Cannot mute an admin.</b>')
        return
    duration, time_str = _find_duration(message.text.split(), 1)
    try:
        await message.bot.restrict_chat_member(message.chat.id, uid, permissions=ALL_PERMS_OFF, until_date=_future(duration))
        dur_text = f' for <b>{time_str}</b>' if time_str else ' indefinitely'
        await anim.play(message, f'🔇 {mention} has been <b>muted</b>{dur_text}.', kind='mute', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed to mute:</b> {e}')


@router.message(Command('unmute'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_unmute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, await _default_group_permissions(message))
            await anim.play(message, '🔊 <b>Group unmuted.</b> Everyone can speak now.', kind='success', delay=anim.FAST_DELAY)
        except Exception as e:
            await message.answer(f'❌ <b>Failed:</b> {e}')
        return
    try:
        await message.bot.restrict_chat_member(message.chat.id, uid, permissions=await _default_group_permissions(message))
        await anim.play(message, f'🔊 {mention} has been <b>unmuted</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('kick'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_kick(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer('❌ <b>Cannot kick an admin.</b>')
        return
    try:
        await message.bot.ban_chat_member(message.chat.id, uid)
        await message.bot.unban_chat_member(message.chat.id, uid)
        await anim.play(message, f'🚪 {mention} was <b>kicked</b>.', kind='kick', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('ban'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_ban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer('❌ <b>Cannot ban an admin.</b>')
        return
    duration, time_str = _find_duration(message.text.split(), 1)
    try:
        await message.bot.ban_chat_member(message.chat.id, uid, until_date=_future(duration))
        dur_text = f' for <b>{time_str}</b>' if time_str else ' permanently'
        await anim.play(message, f'🔨 {mention} was <b>banned</b>{dur_text}.', kind='ban', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('unban'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_unban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    try:
        await message.bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
        await anim.play(message, f'✅ {mention} has been <b>unbanned</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('promote'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_promote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    try:
        await message.bot.promote_chat_member(message.chat.id, uid, can_manage_chat=True, can_delete_messages=True, can_restrict_members=True, can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True)
        await anim.play(message, f'👑 {mention} has been <b>promoted</b> to admin.', kind='sparkle', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('demote'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_demote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    try:
        await message.bot.promote_chat_member(message.chat.id, uid, can_manage_chat=False, can_delete_messages=False, can_restrict_members=False, can_invite_users=False, can_pin_messages=False, can_manage_video_chats=False)
        await anim.play(message, f'📉 {mention} has been <b>demoted</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('pin'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_pin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    if not message.reply_to_message:
        await message.answer('❌ Reply to the message you want to pin.')
        return
    try:
        await message.bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await anim.play(message, '📌 <b>Message pinned.</b>', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')


@router.message(Command('unpin'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_unpin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    try:
        if message.reply_to_message:
            await message.bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
        else:
            await message.bot.unpin_chat_message(message.chat.id)
        await anim.play(message, '📌 <b>Message unpinned.</b>', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f'❌ <b>Failed:</b> {e}')
