from __future__ import annotations

import re
import time

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import get_settings, sync_chat_index, update_setting
from bot.core.logger import get_logger

router = Router()
log = get_logger('CHANNEL_GUARD')

# A raw @username inside a message body. The lookbehind avoids matching
# email addresses such as "mail@example.com".
_MENTION_RE = re.compile('(?<![\\w.])@[A-Za-z][A-Za-z0-9_]{2,}')

# Refreshing the channel index (so it shows up in the private /settings list)
# costs one API call, so it is cached for a while.
_INDEX_TTL = 600.0
_index_cache: dict[int, float] = {}


def _has_mentions(message: Message) -> bool:
    """True when the message tags someone: an @username entity, a hidden
    text_mention, or a plain @username written in the text or caption."""
    entities = list(message.entities or []) + list(message.caption_entities or [])
    for entity in entities:
        if entity.type in {MessageEntityType.MENTION, MessageEntityType.TEXT_MENTION}:
            return True
    text = message.text or message.caption or ''
    return bool(_MENTION_RE.search(text))


def _is_from_bot(message: Message) -> bool:
    user = message.from_user
    return user is not None and user.is_bot


async def _index_channel(message: Message) -> None:
    """Remember the channel (and its admins) so it appears in /settings."""
    chat_id = message.chat.id
    now = time.monotonic()
    if now - _index_cache.get(chat_id, 0.0) < _INDEX_TTL:
        return
    _index_cache[chat_id] = now
    try:
        admins = await message.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
    except Exception:
        admin_ids = []
    try:
        await sync_chat_index(chat_id, message.chat.title or 'Untitled', 'channel', True, admin_ids)
    except Exception:
        pass


def _status_line(enabled: bool) -> str:
    return '🟢 <b>ON</b>' if enabled else '🔴 <b>OFF</b>'


@router.channel_post(Command('antitag'))
async def cmd_antitag(message: Message):
    """Toggle the Anti-Tag channel mode.

    Only channel admins can post in a channel, so anyone able to run this
    command here is by definition an administrator.
    """
    parts = (message.text or '').split(maxsplit=1)
    settings = await get_settings(message.chat.id)
    arg = parts[1].strip().casefold() if len(parts) > 1 else ''
    if arg in {'on', 'off'}:
        enabled = arg == 'on'
        await update_setting(message.chat.id, 'antitag', enabled)
    else:
        enabled = bool(settings.get('antitag'))
    await _index_channel(message)
    await message.answer(
        f'🛡️ <b>Anti-Tag — Channel Guard</b>\n\n'
        f'Status: {_status_line(enabled)}\n\n'
        f'When this mode is <b>ON</b>, every message posted by <b>any bot</b> in this channel '
        f'that tries to tag or mention a user is deleted instantly.\n\n'
        f'Messages written by real humans — including you and the other admins — are never touched.\n\n'
        f'<b>Usage:</b> <code>/antitag on</code> · <code>/antitag off</code>'
    )


@router.channel_post()
async def guard_channel_posts(message: Message):
    """Delete bot messages that contain mentions while Anti-Tag is ON.

    Human posts (anonymous channel posts have no from_user, signed posts have
    a human from_user) always pass through untouched.
    """
    await _index_channel(message)
    if not _is_from_bot(message):
        raise SkipHandler
    settings = await get_settings(message.chat.id)
    if not settings.get('antitag'):
        raise SkipHandler
    if not _has_mentions(message):
        raise SkipHandler
    try:
        await message.delete()
        log.info('Anti-Tag removed a mentioning bot message %s in channel %s', message.message_id, message.chat.id)
    except Exception as error:
        log.warning('Anti-Tag could not delete message %s in channel %s: %s', message.message_id, message.chat.id, error)
        raise SkipHandler
    # Message is gone; stop the chain so nobody reacts to a deleted post.
    return
