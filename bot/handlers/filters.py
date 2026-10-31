from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from bot.core import database as db
from bot.database import get_filters, remove_filter
from bot.utils import anim
from bot.utils.ui import bold, box, italic, mono, quote, row, sc

router = Router()

_match_cache: dict[str, re.Pattern] = {}


def _compile(keyword: str) -> re.Pattern:
    pattern = _match_cache.get(keyword)
    if pattern is None:
        # Word-boundary matching: "hi" matches "hi there" and "#hi" but
        # never "this" or "shopping". Phrases (with spaces) match whole.
        pattern = re.compile(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', re.IGNORECASE | re.UNICODE)
        _match_cache[keyword] = pattern
    return pattern


def matches_filter(keyword: str, text: str) -> bool:
    return bool(text) and bool(_compile(keyword.strip().casefold()).search(text))


def body_text(message: Message) -> str:
    return message.text or message.caption or ''


@router.message(Command('filter'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_filter(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    parts = (message.text or '').split(maxsplit=2)
    if len(parts) < 3:
        text = box('Add Filter 🔎', [
            row('Usage', mono('/filter [keyword] [reply]')),
            row('Example', mono('/filter hello Hello there!')),
            '',
            quote(sc('When someone types the keyword, the bot replies with your text.')),
            f"💡 {italic(sc('Multi-word keywords and a full manager live in Settings → this chat → Filters.'))}",
        ])
        await message.answer(text)
        return
    keyword = parts[1].casefold()[:60]
    reply = parts[2][:4000]
    await db.add_filter(message.chat.id, keyword, reply)
    text = box('Filter Added ✅', [
        row('Keyword', mono(keyword)),
        row('Reply', reply[:180] + ('…' if len(reply) > 180 else '')),
    ])
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY)


@router.message(Command('filters'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_filters(message: Message):
    filters = await get_filters(message.chat.id)
    if not filters:
        await message.answer(quote(sc('No filters set in this group yet.')))
        return
    lines = [row(mono(item['keyword'][:30]), item['reply'][:40] + ('…' if len(item['reply']) > 40 else '')) for item in filters[:25]]
    if len(filters) > 25:
        lines.append(italic(sc(f'…and {len(filters) - 25} more')))
    text = box('Active Filters 🔎', [row('Total', bold(str(len(filters))))] + [''] + lines)
    await message.answer(text)


@router.message(Command('stop'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_stop(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(f"<b>{sc('Usage')}:</b> <code>/stop [keyword]</code>")
        return
    keyword = parts[1].casefold().strip()
    await remove_filter(message.chat.id, keyword)
    text = box('Filter Removed ✅', [row('Keyword', mono(keyword))])
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY)


@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text | F.caption)
async def check_filters(message: Message):
    text = body_text(message)
    if not text or (message.text and message.text.startswith('/')):
        raise SkipHandler
    # Other bots' messages never trigger filters (no reply loops, no noise).
    user = message.from_user
    if user is not None and user.is_bot:
        raise SkipHandler
    filters = await get_filters(message.chat.id)
    if not filters:
        raise SkipHandler
    for item in filters:
        if item['keyword'] and matches_filter(item['keyword'], text):
            try:
                await message.answer(item['reply'])
            except TelegramBadRequest:
                try:
                    await message.answer(item['reply'][:4000], parse_mode=None)
                except TelegramBadRequest:
                    pass
            return  # handled — stop the chain
    raise SkipHandler
