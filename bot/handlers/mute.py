from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import get_warnings
from bot.utils import anim
from bot.utils.helpers import (
    DEFAULT_MEMBER_PERMS,
    MUTE_PERMS_OFF,
    find_duration,
    future,
    get_user_from_message,
    is_admin as check_is_admin,
    mention_by_name,
)
from bot.utils.ui import bold, box, mono, row, sc

router = Router()

_GROUP = F.chat.type.in_({'group', 'supergroup'})


async def _default_group_permissions(message: Message):
    try:
        chat = await message.bot.get_chat(message.chat.id)
        if chat.permissions is not None:
            return chat.permissions
    except Exception:
        pass
    return DEFAULT_MEMBER_PERMS


# ----------------------------------------------------------------- mute ----
@router.message(Command('mute'), _GROUP)
async def cmd_mute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, MUTE_PERMS_OFF)
            await anim.play(message, f"🔇 <b>{sc('Group muted.')}</b> {sc('Only admins can speak now.')}", kind='mute', delay=anim.FAST_DELAY)
        except Exception as e:
            await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer(f"❌ <b>{sc('Cannot mute an admin.')}</b>")
        return
    duration, time_str = find_duration(message.text.split(), 1)
    try:
        await message.bot.restrict_chat_member(message.chat.id, uid, permissions=MUTE_PERMS_OFF, until_date=future(duration))
        dur_text = f" {sc('for')} <b>{time_str}</b>" if time_str else ''
        await anim.play(message, f'🔇 {mention} {sc("has been")} <b>{sc("muted")}</b>{dur_text}.', kind='mute', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed to mute')}:</b> {escape(str(e)[:120])}")


@router.message(Command('unmute'), _GROUP)
async def cmd_unmute(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        try:
            await message.bot.set_chat_permissions(message.chat.id, await _default_group_permissions(message))
            await anim.play(message, f"🔊 <b>{sc('Group unmuted.')}</b> {sc('Everyone can speak now.')}", kind='success', delay=anim.FAST_DELAY)
        except Exception as e:
            await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")
        return
    try:
        await message.bot.restrict_chat_member(message.chat.id, uid, permissions=await _default_group_permissions(message))
        await anim.play(message, f'🔊 {mention} {sc("has been")} <b>{sc("unmuted")}</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


# ----------------------------------------------------------------- kick ----
@router.message(Command('kick'), _GROUP)
async def cmd_kick(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer(f"❌ <b>{sc('Cannot kick an admin.')}</b>")
        return
    try:
        await message.bot.ban_chat_member(message.chat.id, uid)
        await message.bot.unban_chat_member(message.chat.id, uid)
        await anim.play(message, f'🚪 {mention} {sc("was")} <b>{sc("kicked")}</b>.', kind='kick', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


@router.message(Command('ban'), _GROUP)
async def cmd_ban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer(f"❌ <b>{sc('Cannot ban an admin.')}</b>")
        return
    duration, time_str = find_duration(message.text.split(), 1)
    try:
        await message.bot.ban_chat_member(message.chat.id, uid, until_date=future(duration))
        dur_text = f" {sc('for')} <b>{time_str}</b>" if time_str else ''
        await anim.play(message, f'🔨 {mention} {sc("was")} <b>{sc("banned")}</b>{dur_text}.', kind='ban', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


@router.message(Command('unban'), _GROUP)
async def cmd_unban(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
        return
    try:
        await message.bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
        await anim.play(message, f'✅ {mention} {sc("has been")} <b>{sc("unbanned")}</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


# -------------------------------------------------------------- promote ----
@router.message(Command('promote'), _GROUP)
async def cmd_promote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
            can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True,
        )
        await anim.play(message, f'👑 {mention} {sc("has been")} <b>{sc("promoted")}</b>.', kind='sparkle', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


@router.message(Command('demote'), _GROUP)
async def cmd_demote(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
        return
    try:
        await message.bot.promote_chat_member(
            message.chat.id, uid,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False, can_manage_video_chats=False,
        )
        await anim.play(message, f'📉 {mention} {sc("has been")} <b>{sc("demoted")}</b>.', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


# ------------------------------------------------------------------ pin ----
@router.message(Command('pin'), _GROUP)
async def cmd_pin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    if not message.reply_to_message:
        await message.answer(f"❌ {sc('Reply to the message you want to pin.')}")
        return
    try:
        await message.bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id, disable_notification=True)
        await anim.play(message, f'📌 <b>{sc('Message pinned.')}</b>', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


@router.message(Command('unpin'), _GROUP)
async def cmd_unpin(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    try:
        if message.reply_to_message:
            await message.bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
        else:
            await message.bot.unpin_chat_message(message.chat.id)
        await anim.play(message, f'📌 <b>{sc('Message unpinned.')}</b>', kind='success', delay=anim.FAST_DELAY)
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


# ---------------------------------------------------------------- purge ----
@router.message(Command('purge'), _GROUP)
async def cmd_purge(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    if not message.reply_to_message:
        await message.answer(f"❌ {sc('Reply to the first message of the range you want to purge.')}")
        return
    start = message.reply_to_message.message_id
    end = message.message_id
    if end - start > 3000:
        end = start + 3000
    ids = list(range(start, end + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        try:
            result = await message.bot.delete_messages(message.chat.id, batch)
            deleted += sum(1 for ok in result if ok)
        except Exception:
            for mid in batch:
                try:
                    await message.bot.delete_message(message.chat.id, mid)
                    deleted += 1
                except Exception:
                    pass
    try:
        await message.delete()
    except Exception:
        pass
    note = await message.answer(f"🧹 <b>{sc('Purged')}</b> {bold(str(deleted))} {sc('messages')}.")
    from bot.utils.autodelete import schedule_auto_delete

    schedule_auto_delete(note, delay=10)


@router.message(Command('del'), _GROUP)
async def cmd_del(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    if not message.reply_to_message:
        await message.answer(f"❌ {sc('Reply to the message you want to delete.')}")
        return
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.answer(f"❌ <b>{sc('Failed')}:</b> {escape(str(e)[:120])}")


# ----------------------------------------------------------------- info ----
@router.message(Command('adminlist'), _GROUP)
async def cmd_adminlist(message: Message):
    try:
        members = await message.bot.get_chat_administrators(message.chat.id)
    except Exception as e:
        await message.answer(f"❌ {escape(str(e)[:120])}")
        return
    lines = []
    for m in members:
        name = escape(m.user.full_name or str(m.user.id))
        tag = f"@{m.user.username}" if m.user.username else mono(str(m.user.id))
        crown = '👑' if m.status == 'creator' else '⚡️'
        lines.append(f'  {crown} {mention_by_name(m.user.id, name)} — {tag}')
    await message.answer(box('Admins 👑', lines))


@router.message(Command('id'))
async def cmd_id(message: Message):
    if message.chat.type in {'group', 'supergroup'}:
        await message.answer(box('Ids 🆔', [
            row('Chat', mono(str(message.chat.id))),
            row('Title', escape(message.chat.title or '')),
            row('Your Id', mono(str(message.from_user.id if message.from_user else '—'))),
        ]))
        return
    await message.answer(box('Your Id 🆔', [
        row('User', mono(str(message.from_user.id if message.from_user else '—'))),
    ]))


@router.message(Command('info'), _GROUP)
async def cmd_info(message: Message):
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        if message.from_user:
            uid, name, mention = message.from_user.id, message.from_user.full_name, mention_by_name(message.from_user.id, message.from_user.full_name)
        else:
            await message.answer(f"❌ {sc('Reply to a user or mention them.')}")
            return
    user = message.reply_to_message.from_user if message.reply_to_message and message.reply_to_message.from_user else message.from_user
    lines = [
        row('User', mention),
        row('Id', mono(str(uid))),
        row('Name', escape(name or '—')),
    ]
    if user and getattr(user, 'username', None):
        lines.append(row('Username', mono('@' + user.username)))
    try:
        member = await message.bot.get_chat_member(message.chat.id, uid)
        lines.append(row('Status', bold(sc(str(member.status)))))
    except Exception:
        pass
    warns = await get_warnings(message.chat.id, uid)
    lines.append(row('Warns', bold(f'{len(warns)}')))
    await message.answer(box('User Info 👤', lines))
