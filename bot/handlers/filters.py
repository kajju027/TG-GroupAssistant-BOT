from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.dispatcher.event.bases import SkipHandler
from bot.database import get_filters, add_filter, remove_filter
from bot.utils import anim
from bot.utils.ui import bold, box, italic, mono, quote, row, sc, sep

router = Router()

_GROUP_TYPES = {'group', 'supergroup'}


def _body_text(message: Message) -> str:
    """Text used for keyword matching: the message text or, for media, the caption."""
    return message.text or message.caption or ''


@router.message(Command('filter'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_filter(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=2)
    if len(parts) < 3:
        text = box('Add Filter', [
            row('Usage', mono('/filter [keyword] [reply]')),
            row('Example', mono('/filter hello Hello there!')),
            sep(),
            quote(sc('When someone types the keyword, the bot replies with your text.')),
            f"{italic(sc('Tip: /settings has a filter manager for multi-word keywords.'))}",
        ], icon='🔎')
        await message.answer(text, parse_mode='HTML')
        return
    keyword = parts[1].casefold()
    reply = parts[2]
    await add_filter(message.chat.id, keyword, reply)
    text = box('Filter Added', [
        row('Keyword', mono(keyword)),
        row('Reply', reply[:200] + ('…' if len(reply) > 200 else '')),
        sep(),
        quote(sc('Saved and active from now on.')),
    ], icon='✅')
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')


@router.message(Command('filters'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_filters(message: Message):
    filters = await get_filters(message.chat.id)
    if not filters:
        await message.answer(quote(sc('No filters set in this group yet.')), parse_mode='HTML')
        return
    lines = [row(mono(f['keyword']), f['reply'][:40] + ('…' if len(f['reply']) > 40 else '')) for f in filters[:25]]
    if len(filters) > 25:
        lines.append(italic(sc(f'…and {len(filters) - 25} more')))
    text = box('Active Filters', [row('Total', bold(str(len(filters))))] + [sep()] + lines, icon='🔎')
    await message.answer(text, parse_mode='HTML')


@router.message(Command('stop'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_stop(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(f"<b>Usage:</b> <code>/stop [keyword]</code>")
        return
    keyword = parts[1].casefold()
    await remove_filter(message.chat.id, keyword)
    text = box('Filter Removed', [row('Keyword', mono(keyword))], icon='✅')
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')


@router.message(F.chat.type.in_(_GROUP_TYPES), F.text | F.caption)
async def check_filters(message: Message):
    text = _body_text(message)
    # Commands are handled by their own handlers; media captions never are.
    if not text or (message.text and message.text.startswith('/')):
        raise SkipHandler
    filters = await get_filters(message.chat.id)
    text_lower = text.casefold()
    for item in filters:
        if item['keyword'] and item['keyword'].casefold() in text_lower:
            await message.answer(item['reply'])
            return
    raise SkipHandler
