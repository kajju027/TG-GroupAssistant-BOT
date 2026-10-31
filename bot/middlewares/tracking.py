from __future__ import annotations

import time

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.core import database as db
from bot.database import note_seen_member, sync_chat_index
from bot.utils.helpers import is_bot_admin

_SEEN_TTL = 600.0
_INDEX_TTL = 900.0
_seen_cache: dict[tuple[int, int], tuple[str, float]] = {}
_index_touch: dict[int, float] = {}
_title_cache: dict[int, str] = {}


class GroupTrackingMiddleware(BaseMiddleware):
    """Outer middleware: remembers chats, titles and seen members so the
    private-chat panel (and /tag all) always has fresh data. No SQLite on
    the hot path — only an in-memory counter plus TTL'd JSON touches."""

    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]) -> Any:
        try:
            if not isinstance(event, Message):
                return await handler(event, data)
            chat_type = event.chat.type
            if chat_type not in ('group', 'supergroup', 'channel'):
                return await handler(event, data)

            title = event.chat.title or ''
            chat_id = event.chat.id
            now = time.monotonic()

            # Re-sync the chat index when the title changed or every 15 min.
            if _title_cache.get(chat_id) != title or now - _index_touch.get(chat_id, 0.0) > _INDEX_TTL:
                _title_cache[chat_id] = title
                _index_touch[chat_id] = now
                bot_admin = await is_bot_admin(event.bot, chat_id)
                admin_ids: list[int] = []
                if bot_admin:
                    try:
                        admins = await event.bot.get_chat_administrators(chat_id)
                        admin_ids = [a.user.id for a in admins if not a.user.is_bot]
                    except Exception:
                        admin_ids = []
                try:
                    await sync_chat_index(chat_id, title or 'Untitled', chat_type, bot_admin, admin_ids)
                except Exception:
                    pass

            if chat_type == 'channel':
                return await handler(event, data)

            if not event.new_chat_members and not event.left_chat_member:
                db.inc_stat('messages')

            user = event.from_user
            if user is not None and not user.is_bot:
                key = (chat_id, user.id)
                cached = _seen_cache.get(key)
                if cached is None or cached[0] != user.full_name or now - cached[1] > _SEEN_TTL:
                    try:
                        await note_seen_member(chat_id, user.id, user.full_name, False)
                        _seen_cache[key] = (user.full_name, now)
                    except Exception:
                        pass
        except Exception:
            pass
        return await handler(event, data)
