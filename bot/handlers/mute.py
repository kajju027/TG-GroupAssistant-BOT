from __future__ import annotations

import asyncio
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
        await anim.play(message, f'📌 <b>{sc("Message pinned.")}</b>', kind='success', delay=anim.FAST_DELAY)
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
        await anim.play(message, f'📌 <b>{sc("Message unpinned.")}</b>', kind='success', delay=anim.FAST_DELAY)
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


# ------------------------------------------------------------ purgeall ----
# One-tap "delete everything in this group" — a confirmation step keeps it
# safe, and the actual wipe walks id ranges in batches so it stays gentle
# on Telegram's flood limits. Owner/sudo OR group admins can use it.
_PURGEALL_CHUNK = 100
_PURGEALL_PROBE = 100
_PURGEALL_MAX_IDS = 5000  # safety ceiling so a single tap can't nuke huge histories
_PURGEALL_SLEEP = 0.4


@router.message(Command('purgeall'), _GROUP)
async def cmd_purgeall(message: Message, is_admin: bool = False):
    """Send the confirm card. Wiping only happens after the button is tapped."""
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    from bot.utils.ui import quote, kb, btn

    markup = kb(
        [btn('🗑 Yes, Delete Everything', f'purgeall:go:{message.chat.id}')],
        [btn('❌ Cancel', 'purgeall:no')],
    )
    await message.answer(box('Delete All Messages 🧹', [
        quote(sc('This deletes every message the bot can reach in this group — there is no undo. Tap the button below to confirm.')),
    ]), reply_markup=markup)


@router.callback_query(F.data == 'purgeall:no')
async def cb_purgeall_cancel(callback):
    await callback.answer('Cancelled')
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith('purgeall:go:'))
async def cb_purgeall_go(callback):
    from bot.utils.helpers import is_admin as check_admin

    try:
        chat_id = int(callback.data.split(':')[2])
    except (IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    if not await check_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer('Admins only.', show_alert=True)
        return
    await callback.answer('Wiping…')

    # Edit the card so the user gets feedback the wipe is in flight.
    try:
        await callback.message.edit_text(box('Wiping 🧹', [quote(sc('Deleting every message the bot can reach. This may take a while — please don\'t spam this group while it runs.'))]))
    except Exception:
        pass

    bot = callback.bot
    deleted = 0
    cursor = 1
    failed_streak = 0

    while deleted < _PURGEALL_MAX_IDS:
        ids = list(range(cursor, cursor + _PURGEALL_PROBE))
        try:
            messages = await bot.get_messages(chat_id, ids)
        except Exception:
            messages = None
        batch = []
        next_cursor = cursor
        found_any = False
        for msg in (messages or []):
            if msg is None:
                continue
            found_any = True
            batch.append(msg.message_id)
            if msg.message_id > next_cursor:
                next_cursor = msg.message_id
        if not found_any:
            # No messages in this window; advance and try the next chunk,
            # but if we keep hitting empty windows, the history ended.
            failed_streak += 1
            if failed_streak >= 3:
                break
            cursor = next_cursor + 1
            continue
        failed_streak = 0
        if batch:
            try:
                result = await bot.delete_messages(chat_id, batch[:_PURGEALL_CHUNK])
                deleted += sum(1 for ok in result if ok)
            except Exception as error:
                # Fall back to one-by-one for resilience.
                for mid in batch[:_PURGEALL_CHUNK]:
                    try:
                        await bot.delete_message(chat_id, mid)
                        deleted += 1
                    except Exception:
                        pass
                    await asyncio.sleep(_PURGEALL_SLEEP)
        cursor = next_cursor + 1
        await asyncio.sleep(_PURGEALL_SLEEP)

    try:
        await callback.message.edit_text(box('Wipe Complete 🧹', [
            row('Deleted', bold(str(deleted))),
            '',
            quote(sc('Everything the bot could see has been removed.')),
        ]))
    except Exception:
        try:
            await callback.message.answer(box('Wipe Complete 🧹', [bold(f"🧹 {deleted}")]))
        except Exception:
            pass


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
