from typing import Callable, Dict, Any, Awaitable
import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.database import note_chat_admin_seen
_SYNC_INTERVAL_SECONDS = 600
_last_synced: Dict[tuple, float] = {}

def _should_sync(chat_id: int, user_id: int) -> bool:
    key = (chat_id, user_id)
    now = time.monotonic()
    last = _last_synced.get(key, 0)
    if now - last < _SYNC_INTERVAL_SECONDS:
        return False
    _last_synced[key] = now
    return True

class AdminCheckMiddleware(BaseMiddleware):

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]) -> Any:
        if event.chat.type in ('group', 'supergroup'):
            is_admin = False
            is_creator = False
            actor_id = None
            if event.from_user is None:
                if event.sender_chat is not None and event.sender_chat.id == event.chat.id:
                    is_admin = True
                    is_creator = True
            else:
                actor_id = event.from_user.id
                try:
                    member = await event.bot.get_chat_member(event.chat.id, actor_id)
                    is_admin = member.status in ('administrator', 'creator')
                    is_creator = member.status == 'creator'
                except Exception:
                    pass
            data['is_admin'] = is_admin
            data['is_creator'] = is_creator
            if actor_id is not None and (is_admin or is_creator) and _should_sync(event.chat.id, actor_id):
                try:
                    me = await event.bot.get_me()
                    bot_member = await event.bot.get_chat_member(event.chat.id, me.id)
                    bot_is_admin = bot_member.status in ('administrator', 'creator')
                except Exception:
                    bot_is_admin = False
                await note_chat_admin_seen(event.chat.id, event.chat.title or 'Untitled', event.chat.type, actor_id, True, bot_is_admin)
        else:
            data['is_admin'] = True
            data['is_creator'] = True
        return await handler(event, data)
