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
# Telegram hard limit is 4096 characters per message; stay safely below it.
CHUNK_TEXT_LIMIT = 3200
CHUNK_DELAY = 0.6


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
    """Every human the bot knows in this chat: current admins plus every
    member it has seen talking or joining. Telegram does not let bots list
    all members of a group, so this is the widest possible tag list."""
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


def _mention_chunks(targets) -> list[str]:
    """Pack every mention into as few messages as possible.

    All tagged names live together inside one pointing-finger block, e.g.
        🫵 Name1 • Name2 • Name3 ...
    instead of one line per member.
    """
    chunks: list[str] = []
    current = '🫵 '
    for uid, name in targets:
        mention = mention_by_name(uid, name)
        addition = mention if current.endswith(' ') else f' • {mention}'
        if len(current) + len(addition) > CHUNK_TEXT_LIMIT:
            chunks.append(current)
            current = f'🫵 {mention}'
        else:
            current += addition
    if current.strip():
        chunks.append(current)
    return chunks


def _header(chat_title: str, count: int, total_members: int, custom_msg: str, progress: tuple[int, int] | None = None) -> str:
    lines = [
        row('Group', bold(escape(chat_title)[:40])),
        row('Tagging', bold(f'{count}' + (f' / {total_members}' if total_members else '')) + ' members'),
    ]
    if progress is not None:
        done, total = progress
        lines.append(row('Progress', mono(progress_bar(done, total))))
    lines.append(sep())
    if custom_msg:
        lines.append(quote(escape(custom_msg)))
    else:
        lines.append(f'{italic(sc("Attention everyone!"))}')
    return box('Tagging Everyone', lines, icon='📣')


async def _tag_everyone(message: Message, custom_msg: str, targets) -> None:
    chat_title = message.chat.title or 'this group'
    total_members = 0
    try:
        total_members = int(await message.bot.get_chat_member_count(message.chat.id))
    except Exception:
        pass
    chunks = _mention_chunks(targets)
    note = ''
    if total_members and len(targets) < total_members:
        note = f"\n{italic(sc(f'I tag everyone I have seen here ({len(targets)}/{total_members}). New faces join the list once they talk.'))}"
    header = _header(chat_title, len(targets), total_members, custom_msg, (0, len(chunks)))
    header_msg = await anim.play_in_chat(message.bot, message.chat.id, header + note, kind='tag', parse_mode='HTML')
    sent = 0
    for index, chunk in enumerate(chunks, 1):
        try:
            await message.bot.send_message(message.chat.id, chunk, parse_mode='HTML')
            sent += 1
        except Exception:
            pass
        if header_msg is not None and len(chunks) > 1:
            await anim.edit_safe(header_msg, _header(chat_title, len(targets), total_members, custom_msg, (index, len(chunks))) + note, parse_mode='HTML')
        if index < len(chunks):
            await asyncio.sleep(CHUNK_DELAY)
    done = box('Everyone Tagged', [
        row('Tagged', bold(str(len(targets))) + ' members'),
        row('Messages', bold(str(sent))),
        sep(),
        quote(sc('Everyone has been notified.')),
    ], icon='📣')
    if header_msg is not None:
        await anim.edit_safe(header_msg, done, parse_mode='HTML')


async def _tag_admins(message: Message, custom_msg: str, targets) -> None:
    items = [(user.id, user.full_name) for user in targets]
    chunks = _mention_chunks(items)
    message_line = quote(escape(custom_msg)) if custom_msg else italic(sc('Attention admins!'))
    header = box('Admin Tag', [
        row('Admins', bold(str(len(items)))),
        sep(),
        message_line,
    ], icon='👑')
    header_msg = await anim.play(message, header, kind='tag', parse_mode='HTML')
    for chunk in chunks:
        try:
            await message.bot.send_message(message.chat.id, chunk, parse_mode='HTML')
        except Exception:
            pass
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
