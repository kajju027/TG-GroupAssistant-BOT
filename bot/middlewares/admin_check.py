from __future__ import annotations

import time

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message

from bot.database import note_chat_admin_seen

_CACHE_SECONDS = 120.0
_INDEX_TTL = 900.0
_admin_cache: dict[tuple[int, int], tuple[float, bool]] = {}
_bot_admin_cache: dict[int, tuple[float, bool]] = {}
_index_touch: dict[tuple[int, int], float] = {}


def _fresh(cache: dict, key: Any) -> bool | None:
    item = cache.get(key)
    if item and time.monotonic() - item[0] < _CACHE_SECONDS:
        return item[1]
    return None


class AdminCheckMiddleware(BaseMiddleware):
    """Injects `is_admin` into message handlers, with caching so the hot
    path never waits on an extra Telegram call."""

    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]) -> Any:
        if event.chat.type not in {'group', 'supergroup'}:
            data['is_admin'] = True
            data['is_creator'] = True
            return await handler(event, data)
        actor_id = event.from_user.id if event.from_user else None
        is_admin = bool(event.sender_chat and event.sender_chat.id == event.chat.id)
        if actor_id is not None:
            cached = _fresh(_admin_cache, (event.chat.id, actor_id))
            if cached is None:
                try:
                    member = await event.bot.get_chat_member(event.chat.id, actor_id)
                    cached = member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
                except Exception:
                    cached = False
                _admin_cache[event.chat.id, actor_id] = (time.monotonic(), cached)
            is_admin = cached
        data['is_admin'] = is_admin
        data['is_creator'] = is_admin
        if actor_id is not None and is_admin:
            now = time.monotonic()
            key = (event.chat.id, actor_id)
            if now - _index_touch.get(key, 0.0) > _INDEX_TTL:
                _index_touch[key] = now
                try:
                    bot_admin = _fresh(_bot_admin_cache, event.chat.id)
                    if bot_admin is None:
                        try:
                            me = await event.bot.get_me()
                            member = await event.bot.get_chat_member(event.chat.id, me.id)
                            bot_admin = member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
                        except Exception:
                            bot_admin = False
                        _bot_admin_cache[event.chat.id] = (time.monotonic(), bot_admin)
                    await note_chat_admin_seen(event.chat.id, event.chat.title or 'Untitled', event.chat.type, actor_id, True, bot_admin)
                except Exception:
                    pass
        return await handler(event, data)
