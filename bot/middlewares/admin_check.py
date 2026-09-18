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
            # Anonymous admins (Telegram's "remain anonymous" toggle) and
            # messages auto-posted from a linked channel arrive with
            # event.from_user == None and event.sender_chat set instead.
            # Telegram only lets an ADMIN post as the group/channel itself,
            # so treat sender_chat == this chat as a full admin/creator.
            if event.from_user is None:
                if event.sender_chat is not None and event.sender_chat.id == event.chat.id:
                    data["is_admin"] = True
                    data["is_creator"] = True
                else:
                    # Posted anonymously from a *different* linked channel,
                    # or some other edge case with no identifiable user —
                    # can't verify admin status, so default to "not admin"
                    # instead of crashing.
                    data["is_admin"] = False
                    data["is_creator"] = False
            else:
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
