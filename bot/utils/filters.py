from aiogram.filters import BaseFilter
from aiogram.types import Message, TelegramObject

from bot.core.config import OWNER_ID, SUDO_IDS
from bot.core import database as db


def is_privileged_id(user_id: int | None) -> bool:
    """Bot owner + sudo users."""
    return user_id is not None and (user_id == OWNER_ID or user_id in SUDO_IDS)


class OwnerFilter(BaseFilter):
    """Owner or sudo user."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, 'from_user', None)
        return is_privileged_id(user.id if user else None)


class AllowedFilter(BaseFilter):
    """Owner, sudo user or an explicitly allowed user."""

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return False
        uid = message.from_user.id
        return is_privileged_id(uid) or db.is_allowed(uid)


class NotBlockedFilter(BaseFilter):
    """Everything except blocked users."""

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None:
            return True
        return not db.is_blocked(message.from_user.id)
