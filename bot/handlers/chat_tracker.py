from __future__ import annotations

import time

from aiogram import Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated

from bot.database import drop_chat_from_index, sync_chat_index

router = Router()
_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
_refresh_ttl: dict[int, float] = {}


async def _collect_admin_ids(bot, chat_id: int) -> list[int]:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return [admin.user.id for admin in admins if not admin.user.is_bot]
    except Exception:
        return []


async def refresh_chat_index(bot, chat_id: int, chat_title: str, chat_type: str, *, force: bool = False) -> None:
    """(Re)index a chat — groups AND channels — for the private panel."""
    if not force:
        now = time.monotonic()
        if now - _refresh_ttl.get(chat_id, 0.0) < 300.0:
            return
        _refresh_ttl[chat_id] = now
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        bot_is_admin = member.status in _ADMIN_STATUSES
    except Exception:
        bot_is_admin = False
    # If the admin list call fails (rate limit, hiccup) we retry next time
    # instead of storing an empty list that would hide the chat.
    admin_ids = await _collect_admin_ids(bot, chat_id) if bot_is_admin else []
    try:
        await sync_chat_index(chat_id, chat_title or 'Untitled', chat_type, bot_is_admin, admin_ids)
    except Exception:
        pass


@router.my_chat_member()
async def on_bot_membership_changed(event: ChatMemberUpdated):
    """The bot was added / promoted / removed. Channels are indexed the
    same way as groups, so channel options always show up in the panel."""
    if event.chat.type not in {'group', 'supergroup', 'channel'}:
        return
    if event.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        # Keep every setting — the chat comes back exactly as it was.
        await drop_chat_from_index(event.chat.id)
        return
    await refresh_chat_index(event.bot, event.chat.id, event.chat.title or 'Untitled', event.chat.type, force=True)


@router.chat_member()
async def on_member_status_changed(event: ChatMemberUpdated):
    if event.chat.type in {'group', 'supergroup'} and not event.new_chat_member.user.is_bot:
        old_admin = event.old_chat_member.status in _ADMIN_STATUSES
        new_admin = event.new_chat_member.status in _ADMIN_STATUSES
        if old_admin != new_admin:
            await refresh_chat_index(event.bot, event.chat.id, event.chat.title or 'Untitled', event.chat.type, force=True)
    raise SkipHandler
