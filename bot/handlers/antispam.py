from __future__ import annotations

import datetime
import time

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from bot.database import get_settings
from bot.utils.autodelete import answer_and_autodelete
from bot.utils.helpers import get_bot_username, is_admin as check_is_admin, mention_by_name
from bot.utils.ui import box, kb, quote, sc, ubtn

router = Router()

# Sliding-window flood counters — pure memory: fast, and flood state is
# transient anyway (no reason to persist it across restarts).
_windows: dict[tuple[int, int], list[float]] = {}
_muted_until: dict[tuple[int, int], float] = {}


def _prune(chat_id: int, user_id: int, window: int, now: float) -> list[float]:
    key = (chat_id, user_id)
    stamps = [t for t in _windows.get(key, []) if now - t <= window]
    if stamps:
        _windows[key] = stamps
    else:
        _windows.pop(key, None)
    return stamps


@router.message(Command('antispam'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antispam(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    username = await get_bot_username(message.bot)
    markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')]) if username else None
    await message.answer(box('Anti Spam 🚫', [quote(sc('Anti-Spam settings now live in my private chat — tap below.'))]), reply_markup=markup)


@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text | F.caption)
async def check_spam(message: Message):
    if not message.from_user:
        raise SkipHandler
    if message.text and message.text.startswith('/'):
        raise SkipHandler
    if message.sender_chat is not None:
        raise SkipHandler
    user_id = message.from_user.id
    chat_id = message.chat.id
    if await check_is_admin(message.bot, chat_id, user_id):
        raise SkipHandler
    settings = await get_settings(chat_id)
    if not settings.get('antispam'):
        raise SkipHandler
    now = time.monotonic()
    key = (chat_id, user_id)
    if now < _muted_until.get(key, 0.0):
        raise SkipHandler
    window = int(settings.get('antispam_window', 10))
    limit = int(settings.get('antispam_limit', 5))
    stamps = _prune(chat_id, user_id, window, now)
    stamps.append(now)
    _windows[key] = stamps
    if len(stamps) < limit:
        raise SkipHandler
    _windows.pop(key, None)
    _muted_until[key] = now + 300.0
    mention = mention_by_name(user_id, message.from_user.full_name)
    try:
        await message.delete()
    except Exception:
        pass
    await answer_and_autodelete(message, f'🚫 {mention} {sc("is spamming! Muted for 5 minutes.")}')
    try:
        await message.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5),
        )
    except Exception:
        pass
