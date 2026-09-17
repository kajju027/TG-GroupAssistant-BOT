from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.chat.type in ("group", "supergroup"):
            try:
                member = await event.bot.get_chat_member(event.chat.id, event.from_user.id)
                data["is_admin"] = member.status in ("administrator", "creator")
                data["is_creator"] = member.status == "creator"
            except Exception:
                data["is_admin"] = False
                data["is_creator"] = False
        else:
            data["is_admin"] = True
            data["is_creator"] = True
        return await handler(event, data)
