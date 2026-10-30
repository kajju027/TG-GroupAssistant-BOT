from __future__ import annotations

import time

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.core import database as db
from bot.database import note_seen_member

_SEEN_TTL = 600.0
_seen_cache: dict[tuple[int, int], tuple[str, float]] = {}


class GroupTrackingMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]) -> Any:
        try:
            if isinstance(event, Message):
                if event.chat.type in ('group', 'supergroup'):
                    db.ensure_group(event.chat.id, event.chat.title or '')
                    if not event.new_chat_members and (not event.left_chat_member):
                        db.inc_stat('messages')
                    user = event.from_user
                    if user is not None and not user.is_bot:
                        key = (event.chat.id, user.id)
                        now = time.monotonic()
                        cached = _seen_cache.get(key)
                        if cached is None or cached[0] != user.full_name or now - cached[1] > _SEEN_TTL:
                            try:
                                await note_seen_member(event.chat.id, user.id, user.full_name, user.is_bot)
                                _seen_cache[key] = (user.full_name, now)
                            except Exception:
                                pass
        except Exception:
            pass
        return await handler(event, data)
