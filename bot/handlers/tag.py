from __future__ import annotations

import asyncio

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import get_seen_members
from bot.utils import anim
from bot.utils.helpers import mention_by_name
from bot.utils.ui import bold, box, italic, mono, progress_bar, quote, row, sc, sep

router = Router()

_GROUP_TYPES = {'group', 'supergroup'}
CHUNK_SIZE = 25
MAX_CHUNKS = 8
CHUNK_DELAY = 0.5


def _split_command(message: Message) -> tuple[str, str]:
    text = message.text or ''
    parts = text.split(maxsplit=1)
    rest = parts[1].strip() if len(parts) > 1 else ''
    tokens = rest.split(maxsplit=1)
    mode = ''
    if tokens and tokens[0].casefold() in {'admin', 'admins', 'all', 'everyone'}:
        mode = tokens[0].casefold()
        rest = tokens[1].strip() if len(tokens) > 1 else ''
    return mode, rest


async def _admin_targets(message: Message):
    try:
        members = await message.bot.get_chat_administrators(message.chat.id)
    except Exception as error:
        return None, str(error)
    users = [m.user for m in members if not m.user.is_bot]
    return users, ''


async def _all_targets(message: Message):
    admins, error = await _admin_targets(message)
    if admins is None:
        return None, error
    merged: dict[int, tuple] = {}
    for user in admins:
        merged[user.id] = (user.id, user.full_name)
    for member in await get_seen_members(message.chat.id):
        if member['user_id'] not in merged:
            merged[member['user_id']] = (member['user_id'], member['name'])
    users = [(uid, name) for uid, name in merged.values() if name]
    return users, ''


def _chunks(items: list):
    chunks = [items[i:i + CHUNK_SIZE] for i in range(0, len(items), CHUNK_SIZE)]
    return chunks[:MAX_CHUNKS], len(chunks)


async def _tag_everyone(message: Message, custom_msg: str, targets) -> None:
    chat_title = message.chat.title or 'this group'
    total_members = 0
    try:
        total_members = int(await message.bot.get_chat_member_count(message.chat.id))
    except Exception:
        pass
    chunks, total_chunks = _chunks(targets)
    note = ''
    if total_members and len(targets) < total_members:
        note = f"\n  ℹ️ {italic(sc(f'I can only tag members I have seen here ({len(targets)}/{total_members})'))}"
    header = box('Tagging Everyone', [
        row('Group', bold(escape(chat_title)[:40]), '👥'),
        row('Members', bold(f'{len(targets)}' + (f' / {total_members}' if total_members else '')), '📣'),
        row('Progress', mono(progress_bar(0, len(chunks))), '⏳'),
        sep(),
        (f"  💬 {quote(escape(custom_msg))}" if custom_msg else f"  💬 {italic(sc('Attention everyone!'))}"),
        note,
    ])
    header_msg = await anim.play_in_chat(
        message.bot, message.chat.id, header, kind='tag', parse_mode='HTML'
    )
    sent_count = 0
    for index, chunk in enumerate(chunks, 1):
        lines = [f'➤ {mention_by_name(uid, name)}' for uid, name in chunk]
        try:
            await message.bot.send_message(message.chat.id, '\n'.join(lines))
            sent_count += len(chunk)
        except Exception:
            pass
        if header_msg is not None:
            progress_text = box('Tagging Everyone', [
                row('Group', bold(escape(chat_title)[:40]), '👥'),
                row('Members', bold(f'{len(targets)}' + (f' / {total_members}' if total_members else '')), '📣'),
                row('Progress', mono(progress_bar(index, len(chunks))), '⏳'),
                sep(),
                (f"  💬 {quote(escape(custom_msg))}" if custom_msg else f"  💬 {italic(sc('Attention everyone!'))}"),
                note,
            ])
            await anim.edit_safe(header_msg, progress_text, parse_mode='HTML')
        if index < len(chunks):
            await asyncio.sleep(CHUNK_DELAY)
    done = box('Everyone Tagged', [
        row('Tagged', bold(str(sent_count)), '👥'),
        row('Messages', bold(str(len(chunks))), '📨'),
        sep(),
        quote(sc('Everyone has been notified.')),
    ])
    if header_msg is not None:
        await anim.edit_safe(header_msg, done, parse_mode='HTML')


async def _tag_admins(message: Message, custom_msg: str, targets) -> None:
    items = [(user.id, user.full_name) for user in targets]
    message_line = f"  💬 {quote(escape(custom_msg))}" if custom_msg else f"  💬 {italic(sc('Attention admins!'))}"
    if len(items) <= 20:
        lines = [f'➤ {mention_by_name(uid, name)}' for uid, name in items]
        text = box('Admin Tag', [
            row('Admins', bold(str(len(items))), '👑'),
            sep(),
            message_line,
            sep(),
            *lines,
        ])
        await anim.play(message, text, kind='tag', parse_mode='HTML')
        return
    chunks, _ = _chunks(items)
    header = box('Admin Tag', [
        row('Admins', bold(str(len(items))), '👑'),
        row('Progress', mono(progress_bar(0, len(chunks))), '⏳'),
        sep(),
        message_line,
    ])
    header_msg = await anim.play(message, header, kind='tag', parse_mode='HTML')
    for index, chunk in enumerate(chunks, 1):
        lines = [f'➤ {mention_by_name(uid, name)}' for uid, name in chunk]
        try:
            await message.bot.send_message(message.chat.id, '\n'.join(lines))
        except Exception:
            pass
        if header_msg is not None:
            await anim.edit_safe(
                header_msg,
                box('Admin Tag', [
                    row('Admins', bold(str(len(items))), '👑'),
                    row('Progress', mono(progress_bar(index, len(chunks))), '⏳'),
                    sep(),
                    message_line,
                ]),
                parse_mode='HTML',
            )
        if index < len(chunks):
            await asyncio.sleep(CHUNK_DELAY)


@router.message(Command('tag'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_tag(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    mode, custom_msg = _split_command(message)
    if mode in {'all', 'everyone'}:
        targets, error = await _all_targets(message)
        if targets is None:
            await message.answer(f'❌ Failed to fetch members: {escape(error)}')
            return
        if not targets:
            await message.answer('No members found to tag.')
            return
        await _tag_everyone(message, custom_msg, targets)
        return
    targets, error = await _admin_targets(message)
    if targets is None:
        await message.answer(f'❌ Failed to fetch admins: {escape(error)}')
        return
    if not targets:
        await message.answer('No admins found to tag.')
        return
    await _tag_admins(message, custom_msg, targets)


@router.message(Command('everyone', 'all', 'tagall'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_everyone(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    custom_msg = parts[1].strip() if len(parts) > 1 else ''
    targets, error = await _all_targets(message)
    if targets is None:
        await message.answer(f'❌ Failed to fetch members: {escape(error)}')
        return
    if not targets:
        await message.answer('No members found to tag.')
        return
    await _tag_everyone(message, custom_msg, targets)
