from __future__ import annotations

import re

from aiogram import Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import get_settings
from bot.handlers.chat_tracker import refresh_chat_index
from bot.core.logger import get_logger
from bot.utils.helpers import get_bot_username
from bot.utils.ui import box, kb, quote, sc, ubtn

router = Router()
log = get_logger('CHANNEL_GUARD')

# A raw @username inside a message body. The lookbehind avoids matching
# email addresses such as "mail@example.com".
_MENTION_RE = re.compile('(?<![\\w.])@[A-Za-z][A-Za-z0-9_]{2,}')


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


@router.channel_post(Command('antitag'))
async def cmd_antitag(message: Message):
    """Anti-Tag channel guard. Only channel admins can post in a channel,
    so anyone able to run this command here is by definition an admin."""
    from bot.database import update_setting

    parts = (message.text or '').split(maxsplit=1)
    arg = parts[1].strip().casefold() if len(parts) > 1 else ''
    if arg in {'on', 'off'}:
        await update_setting(message.chat.id, 'antitag', arg == 'on')
    settings = await get_settings(message.chat.id)
    enabled = bool(settings.get('antitag'))
    username = await get_bot_username(message.bot)
    markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')]) if username else None
    await message.answer(box('Channel Guard 🛡️', [
        f"{'🟢' if enabled else '🔴'} <b>{sc('On') if enabled else sc('Off')}</b>",
        '',
        quote(sc('When ON, every message posted by any bot in this channel that tries to tag a user is deleted instantly. Human posts are never touched.')),
    ]), reply_markup=markup)


@router.channel_post()
async def guard_channel_posts(message: Message):
    """Index the channel for the private panel, then apply the guard."""
    await refresh_chat_index(message.bot, message.chat.id, message.chat.title or 'Untitled', 'channel')
    if not _is_from_bot(message):
        raise SkipHandler
    settings = await get_settings(message.chat.id)
    if not settings.get('antitag'):
        raise SkipHandler
    if not _has_mentions(message):
        raise SkipHandler
    try:
        await message.delete()
        log.info('Anti-Tag removed bot message %s in channel %s', message.message_id, message.chat.id)
    except Exception as error:
        log.warning('Anti-Tag could not delete %s in channel %s: %s', message.message_id, message.chat.id, error)
        raise SkipHandler
    # Message is gone; stop the chain so nothing reacts to a deleted post.
    return
