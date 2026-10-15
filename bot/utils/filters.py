from aiogram.filters import BaseFilter
from aiogram.types import Message
from bot.core.config import OWNER_ID
from bot.core import database as db


class OwnerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == OWNER_ID


class AllowedFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        uid = message.from_user.id
        return uid == OWNER_ID or db.is_allowed(uid)


class NotBlockedFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return True
        return not db.is_blocked(message.from_user.id)
