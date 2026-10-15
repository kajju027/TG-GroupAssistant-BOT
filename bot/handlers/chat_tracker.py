from aiogram import Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from bot.database import drop_chat_from_index, sync_chat_index
router = Router()
_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}

async def _collect_admin_ids(bot, chat_id: int) -> list[int]:
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except Exception:
        return []
    return [admin.user.id for admin in admins if not admin.user.is_bot]

async def _refresh_chat_index(bot, chat_id: int, chat_title: str, chat_type: str) -> None:
    try:
        me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id, me.id)
        bot_is_admin = bot_member.status in _ADMIN_STATUSES
    except Exception:
        bot_is_admin = False
    admin_ids = await _collect_admin_ids(bot, chat_id) if bot_is_admin else []
    await sync_chat_index(chat_id, chat_title, chat_type, bot_is_admin, admin_ids)

@router.my_chat_member()
async def on_bot_membership_changed(event: ChatMemberUpdated):
    if event.chat.type not in {'group', 'supergroup', 'channel'}:
        return
    if event.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        await drop_chat_from_index(event.chat.id)
        return
    await _refresh_chat_index(event.bot, event.chat.id, event.chat.title or 'Untitled', event.chat.type)

@router.chat_member()
async def on_member_status_changed(event: ChatMemberUpdated):
    if event.chat.type in {'group', 'supergroup'} and (not event.new_chat_member.user.is_bot):
        old_admin = event.old_chat_member.status in _ADMIN_STATUSES
        new_admin = event.new_chat_member.status in _ADMIN_STATUSES
        if old_admin != new_admin:
            await _refresh_chat_index(event.bot, event.chat.id, event.chat.title or 'Untitled', event.chat.type)
    raise SkipHandler
