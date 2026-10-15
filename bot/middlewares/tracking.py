from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.core import database as db


class GroupTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            if event.chat.type in ("group", "supergroup"):
                db.ensure_group(event.chat.id, event.chat.title or "")
                if not event.new_chat_members and not event.left_chat_member:
                    db.inc_stat("messages")
        return await handler(event, data)
