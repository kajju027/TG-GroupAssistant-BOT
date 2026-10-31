from __future__ import annotations

import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from bot.database import get_settings, get_warnings, add_warning, reset_warnings, remove_last_warning
from bot.utils import anim
from bot.utils.helpers import get_user_from_message, is_admin as check_is_admin, mention_by_name
from bot.utils.autodelete import answer_and_autodelete

router = Router()

_GROUP = F.chat.type.in_({'group', 'supergroup'})


async def _apply_warn_action(message: Message, user_id: int, action: str, mention: str):
    if action == 'kick':
        await answer_and_autodelete(message, f'🚪 {mention} was kicked for exceeding the warn limit.')
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
            await message.bot.unban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    elif action == 'ban':
        await answer_and_autodelete(message, f'🔨 {mention} was banned for exceeding the warn limit.')
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    elif action == 'mute':
        await answer_and_autodelete(message, f'🔇 {mention} was muted for exceeding the warn limit.')
        try:
            await message.bot.restrict_chat_member(
                message.chat.id, user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
            )
        except Exception:
            pass


@router.message(Command('warn'), _GROUP)
async def cmd_warn(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    if await check_is_admin(message.bot, message.chat.id, uid):
        await message.answer('❌ Cannot warn an admin.')
        return
    parts = message.text.split(maxsplit=2)
    reason = parts[-1] if len(parts) > 2 and not parts[-1].startswith('@') else 'No reason given'
    s = await get_settings(message.chat.id)
    count = await add_warning(message.chat.id, uid, reason)
    limit = s['warn_limit']
    if count >= limit:
        text = f'⚠️ {mention} reached the warn limit ({count}/{limit})!\n<b>Action:</b> {s["warn_action"].upper()}'
        await anim.play(message, text, kind='warn', delay=anim.FAST_DELAY)
        await _apply_warn_action(message, uid, s['warn_action'], mention)
        await reset_warnings(message.chat.id, uid)
    else:
        text = f'⚠️ <b>Warning {count}/{limit}</b>\n<b>User:</b> {mention}\n<b>Reason:</b> {reason}'
        await anim.play(message, text, kind='warn', delay=anim.FAST_DELAY)


@router.message(Command('unwarn'), _GROUP)
async def cmd_unwarn(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    warns = await get_warnings(message.chat.id, uid)
    if not warns:
        await message.answer(f'✅ {mention} has no warnings.')
        return
    remaining = await remove_last_warning(message.chat.id, uid)
    await anim.play(message, f'✅ Removed 1 warning from {mention}. Remaining: <b>{remaining}</b>', kind='success', delay=anim.FAST_DELAY)


@router.message(Command('warns'), _GROUP)
async def cmd_warns(message: Message):
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        if message.from_user is None:
            await message.answer('❌ Reply to a user or mention them.')
            return
        uid = message.from_user.id
        mention = mention_by_name(uid, message.from_user.full_name)
    s = await get_settings(message.chat.id)
    warns = await get_warnings(message.chat.id, uid)
    if not warns:
        await message.answer(f'✅ {mention} has no warnings.')
        return
    warn_limit = s['warn_limit']
    text = f'⚠️ <b>Warnings for {mention}: {len(warns)}/{warn_limit}</b>\n\n'
    for i, w in enumerate(warns, 1):
        text += f'{i}. {w["reason"]} — <i>{w["created_at"][:16]}</i>\n'
    await message.answer(text)


@router.message(Command('resetwarns'), _GROUP)
async def cmd_resetwarns(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    uid, name, mention = await get_user_from_message(message)
    if not uid:
        await message.answer('❌ Reply to a user or mention them.')
        return
    await reset_warnings(message.chat.id, uid)
    await anim.play(message, f'✅ All warnings reset for {mention}.', kind='success', delay=anim.FAST_DELAY)
