from __future__ import annotations
import time
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from bot.database import note_chat_admin_seen
_CACHE_SECONDS = 60
_admin_cache: dict[tuple[int, int], tuple[float, bool]] = {}
_bot_admin_cache: dict[int, tuple[float, bool]] = {}

def _fresh(cache: dict, key: Any) -> bool | None:
    item = cache.get(key)
    if item and time.monotonic() - item[0] < _CACHE_SECONDS:
        return item[1]
    return None

class AdminCheckMiddleware(BaseMiddleware):

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
            cached_bot_admin = _fresh(_bot_admin_cache, event.chat.id)
            if cached_bot_admin is None:
                try:
                    me = await event.bot.get_me()
                    bot_member = await event.bot.get_chat_member(event.chat.id, me.id)
                    cached_bot_admin = bot_member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
                except Exception:
                    cached_bot_admin = False
                _bot_admin_cache[event.chat.id] = (time.monotonic(), cached_bot_admin)
            await note_chat_admin_seen(event.chat.id, event.chat.title or 'Untitled', event.chat.type, actor_id, True, cached_bot_admin)
        return await handler(event, data)
