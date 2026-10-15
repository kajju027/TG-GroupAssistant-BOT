import asyncio
from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from bot.core import database as db
from bot.utils.filters import OwnerFilter
from bot.utils.ui import sc, box, row, sep, bold, mono, italic, link, quote
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
        await message.reply(box('Allow User', [f"  {sc('Reply to a user or pass ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    if uid == message.from_user.id:
        await message.reply(box('Allow User', [f"  {sc('You are the owner — no need!')}"]), parse_mode=ParseMode.HTML)
        return
    db.add_allowed(uid, uname, name)
    await message.reply(box('User Allowed ✅', [row('Name', link(name or str(uid), uid), '👤'), row('ID', mono(str(uid)), '🆔'), sep(), quote(sc('Access granted successfully.'))]), parse_mode=ParseMode.HTML)

@router.message(Command('disallow'), OwnerFilter())
async def disallow_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, name = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Disallow', [f"  {sc('Reply to a user or pass ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    db.del_allowed(uid)
    await message.reply(box('Access Revoked 🚫', [row('ID', mono(str(uid)), '🆔'), sep(), quote(sc('User no longer has access.'))]), parse_mode=ParseMode.HTML)

@router.message(Command('block'), OwnerFilter())
async def block_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, name = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Block User', [f"  {sc('Reply to a user or pass ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    db.block_user(uid)
    db.del_allowed(uid)
    await message.reply(box('User Blocked 🔒', [row('ID', mono(str(uid)), '🔒'), row('Name', name or sc('unknown'), '👤'), sep(), quote(sc('User is blocked from this bot.'))]), parse_mode=ParseMode.HTML)

@router.message(Command('unblock'), OwnerFilter())
async def unblock_user(message: Message, bot: Bot):
    db.inc_stat('commands')
    uid, _, _ = await _resolve(message, bot)
    if not uid:
        await message.reply(box('Unblock', [f"  {sc('Reply to a user or pass ID / @username')}"]), parse_mode=ParseMode.HTML)
        return
    db.unblock_user(uid)
    await message.reply(box('User Unblocked 🔓', [row('ID', mono(str(uid)), '🔓'), sep(), quote(sc('User can access the bot again.'))]), parse_mode=ParseMode.HTML)

@router.message(Command('users'), OwnerFilter())
async def list_users(message: Message):
    db.inc_stat('commands')
    users = db.get_allowed()
    if not users:
        await message.reply(box('Allowed Users', [f"  {italic(sc('No users allowed yet.'))}"]), parse_mode=ParseMode.HTML)
        return
    lines = [row('Total', bold(str(len(users))), '📋'), sep()]
    for i, u in enumerate(users, 1):
        n = u['first_name'] or sc('unknown')
        uid = u['user_id']
        tag = f"@{u['username']}" if u['username'] else mono(str(uid))
        lines.append(f'  <b>{i}.</b> {link(n, uid)} — {tag}')
    await message.reply(box('Allowed Users 👥', lines), parse_mode=ParseMode.HTML)

@router.message(Command('stats'), OwnerFilter())
async def show_stats(message: Message):
    db.inc_stat('commands')
    groups = db.all_groups()
    allowed = db.get_allowed()
    await message.reply(box('Bot Statistics 📊', [row('Allowed Users', bold(str(len(allowed))), '👤'), row('Groups Active', bold(str(len(groups))), '👥'), row('Messages', bold(str(db.get_stat('messages'))), '💬'), row('Reactions', bold(str(db.get_stat('reactions'))), '⚡'), row('Downloads', bold(str(db.get_stat('downloads'))), '⬇️'), row('Commands', bold(str(db.get_stat('commands'))), '📊')]), parse_mode=ParseMode.HTML)

@router.message(Command('broadcast'), OwnerFilter())
async def start_broadcast(message: Message, state: FSMContext, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) > 1:
        await _do_broadcast(message, parts[1], bot)
        return
    await message.reply(box('Broadcast 📢', [f"  {sc('Send the message to broadcast:')} ⬇️"]), parse_mode=ParseMode.HTML)
    await state.set_state(BcastState.waiting)

@router.message(BcastState.waiting, OwnerFilter())
async def recv_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await _do_broadcast(message, message.html_text or '', bot)

async def _do_broadcast(message: Message, text: str, bot: Bot):
    groups = db.all_groups()
    sent = 0
    failed = 0
    status = await message.reply(box('Broadcasting 📢', [f"  ⏳ {sc('Sending to')} {bold(str(len(groups)))} {sc('groups...')}"]), parse_mode=ParseMode.HTML)
    for g in groups:
        try:
            await bot.send_message(g['chat_id'], text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(box('Broadcast Complete ✅', [row('Sent', bold(str(sent)), '✅'), row('Failed', bold(str(failed)), '❌'), sep(), quote(sc('Broadcast finished.'))]), parse_mode=ParseMode.HTML)
