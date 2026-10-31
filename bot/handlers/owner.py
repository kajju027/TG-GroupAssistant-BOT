from __future__ import annotations

import asyncio
import time

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.core import database as db
from bot.core.config import START_TIME
from bot.database import list_broadcast_chats
from bot.utils.filters import OwnerFilter
from bot.utils.ui import bold, box, fmt_uptime, italic, link, mono, quote, row, sc

router = Router()


class BcastState(StatesGroup):
    waiting = State()


async def _resolve(message: Message, bot: Bot):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return (u.id, u.username or '', u.full_name)
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        return (None, None, None)
    t = parts[1].strip().split()[0]
    if t.lstrip('-').isdigit():
        uid = int(t)
        try:
            chat = await bot.get_chat(uid)
            return (uid, getattr(chat, 'username', '') or '', getattr(chat, 'full_name', str(uid)))
        except Exception:
            return (uid, '', str(uid))
    if t.startswith('@'):
        try:
            chat = await bot.get_chat(t)
            return (chat.id, getattr(chat, 'username', '') or '', getattr(chat, 'full_name', t))
        except Exception:
            return (None, None, None)
    return (None, None, None)


@router.message(Command('allow'), OwnerFilter())
async def allow_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, uname, name = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Allow User 👤', [f"  {sc('Reply to a user or pass ID / @username')}"]))
        return
    if uid == message.from_user.id:
        await message.reply(box('Allow User 👤', [f"  {sc('You are the owner — no need!')}"]))
        return
    db.add_allowed(uid, uname, name)
    await message.reply(box('User Allowed ✅', [
        row('Name', link(name or str(uid), uid)),
        row('Id', mono(str(uid))),
        '',
        quote(sc('Access granted successfully.')),
    ]))


@router.message(Command('disallow'), OwnerFilter())
async def disallow_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, name = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Disallow 🚫', [f"  {sc('Reply to a user or pass ID / @username')}"]))
        return
    db.del_allowed(uid)
    await message.reply(box('Access Revoked 🚫', [
        row('Id', mono(str(uid))),
        '',
        quote(sc('User no longer has access.')),
    ]))


@router.message(Command('block'), OwnerFilter())
async def block_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, name = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Block User 🔒', [f"  {sc('Reply to a user or pass ID / @username')}"]))
        return
    db.block_user(uid)
    db.del_allowed(uid)
    await message.reply(box('User Blocked 🔒', [
        row('Id', mono(str(uid))),
        row('Name', name or sc('unknown')),
        '',
        quote(sc('User is blocked from this bot.')),
    ]))


@router.message(Command('unblock'), OwnerFilter())
async def unblock_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, _ = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Unblock 🔓', [f"  {sc('Reply to a user or pass ID / @username')}"]))
        return
    db.unblock_user(uid)
    await message.reply(box('User Unblocked 🔓', [
        row('Id', mono(str(uid))),
        '',
        quote(sc('User can access the bot again.')),
    ]))


@router.message(Command('users'), OwnerFilter())
async def list_users(message: Message):
    db.inc_stat('commands')
    users = db.get_allowed()
    if not users:
        await message.reply(box('Allowed Users 👥', [f"  {italic(sc('No users allowed yet.'))}"]))
        return
    lines = [row('Total', bold(str(len(users)))), '']
    for i, u in enumerate(users, 1):
        n = u['first_name'] or sc('unknown')
        uid = u['user_id']
        tag = f"@{u['username']}" if u['username'] else mono(str(uid))
        lines.append(f'  <b>{i}.</b> {link(n, uid)} — {tag}')
    await message.reply(box('Allowed Users 👥', lines))


@router.message(Command('stats'), OwnerFilter())
async def show_stats(message: Message):
    db.inc_stat('commands')
    chats = await list_broadcast_chats()
    groups = [c for c in chats if c.get('type') != 'channel']
    channels = [c for c in chats if c.get('type') == 'channel']
    allowed = db.get_allowed()
    stats = db.get_all_stats()
    await message.reply(box('Bot Statistics 📊', [
        row('Uptime', bold(fmt_uptime(time.time() - START_TIME))),
        row('Groups', bold(str(len(groups)))),
        row('Channels', bold(str(len(channels)))),
        row('Allowed Users', bold(str(len(allowed)))),
        row('Messages', bold(str(stats.get('messages', 0)))),
        row('Reactions', bold(str(stats.get('reactions', 0)))),
        row('Commands', bold(str(stats.get('commands', 0)))),
        row('Downloads', bold(str(stats.get('downloads', 0)))),
    ]))


@router.message(Command('broadcast'), OwnerFilter())
async def start_broadcast(message: Message, state: FSMContext, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) > 1:
        await _do_broadcast(message, parts[1], bot)
        return
    await message.reply(box('Broadcast 📢', [f"  {sc('Send the message to broadcast:')} ⬇️"]))
    await state.set_state(BcastState.waiting)


@router.message(BcastState.waiting, OwnerFilter())
async def recv_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await _do_broadcast(message, message.html_text or '', bot)


async def _do_broadcast(message: Message, text: str, bot: Bot):
    chats = await list_broadcast_chats()
    sent = 0
    failed = 0
    status = await message.reply(box('Broadcasting 📢', [
        f"  ⏳ {sc('Sending to')} {bold(str(len(chats)))} {sc('chats...')}"]))
    for chat in chats:
        try:
            await bot.send_message(chat['chat_id'], text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(box('Broadcast Complete ✅', [
        row('Sent', bold(str(sent))),
        row('Failed', bold(str(failed))),
        '',
        quote(sc('Broadcast finished.')),
    ]))
