from __future__ import annotations

import time

from html import escape

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import ChatMemberUpdatedFilter, Command, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import ChatMemberUpdated, Message

from bot.database import (
    get_settings,
    note_seen_member,
    remove_seen_member,
)
from bot.utils.helpers import get_bot_username, mention_by_name
from bot.utils.ui import box, kb, quote, sc, ubtn

router = Router()

_DEDUPE_TTL = 90.0
_recent_events: dict[tuple, float] = {}


def _seen_recently(key: tuple) -> bool:
    stamp = _recent_events.get(key)
    if stamp is None:
        return False
    if time.monotonic() - stamp > _DEDUPE_TTL:
        _recent_events.pop(key, None)
        return False
    return True


def _mark(key: tuple) -> None:
    if len(_recent_events) > 4096:
        now = time.monotonic()
        for stale in [k for k, v in _recent_events.items() if now - v > _DEDUPE_TTL]:
            _recent_events.pop(stale, None)
    _recent_events[key] = time.monotonic()


def format_template(template: str, user, chat, member_count: int) -> str:
    values = {
        '{mention}': mention_by_name(user.id, user.full_name),
        '{name}': escape(user.full_name),
        '{username}': '@' + escape(user.username) if user.username else escape(user.full_name),
        '{group}': escape(chat.title or 'this group'),
        '{count}': str(member_count) if member_count > 0 else 'N/A',
        '{id}': str(user.id),
    }
    for placeholder, value in values.items():
        template = template.replace(placeholder, value)
    return template


async def _member_count(bot, chat_id: int) -> int:
    try:
        return int(await bot.get_chat_member_count(chat_id))
    except Exception:
        return 0


async def _send_greeting(bot, chat, user, template: str, count: int, kind: str) -> None:
    from bot.utils import anim

    text = format_template(template, user, chat, count)
    try:
        await anim.play_in_chat(bot, chat.id, text, kind=kind)
    except Exception:
        pass


async def _maybe_greet(event_chat, bot, user, event_key: str) -> None:
    settings = await get_settings(event_chat.id)
    enabled = settings.get('welcome') and settings.get('welcome_msg')
    if not enabled or _seen_recently((event_chat.id, user.id, event_key)):
        return
    _mark((event_chat.id, user.id, event_key))
    count = await _member_count(bot, event_chat.id)
    await _send_greeting(bot, event_chat, user, settings['welcome_msg'], count, 'welcome')


async def _maybe_farewell(event_chat, bot, user, event_key: str) -> None:
    settings = await get_settings(event_chat.id)
    enabled = settings.get('goodbye') and settings.get('goodbye_msg')
    if not enabled or _seen_recently((event_chat.id, user.id, event_key)):
        return
    _mark((event_chat.id, user.id, event_key))
    count = await _member_count(bot, event_chat.id)
    await _send_greeting(bot, event_chat, user, settings['goodbye_msg'], count, 'goodbye')


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        raise SkipHandler
    try:
        await note_seen_member(event.chat.id, user.id, user.full_name, False)
    except Exception:
        pass
    await _maybe_greet(event.chat, event.bot, user, 'join')
    raise SkipHandler


@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_leave(event: ChatMemberUpdated):
    user = event.old_chat_member.user
    if user.is_bot:
        raise SkipHandler
    try:
        await remove_seen_member(event.chat.id, user.id)
    except Exception:
        pass
    await _maybe_farewell(event.chat, event.bot, user, 'leave')
    raise SkipHandler


@router.message(F.new_chat_members)
async def on_new_members(message: Message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        try:
            await note_seen_member(message.chat.id, member.id, member.full_name, False)
        except Exception:
            pass
        await _maybe_greet(message.chat, message.bot, member, 'join')


@router.message(F.left_chat_member)
async def on_left_member(message: Message):
    member = message.left_chat_member
    if member is None or member.is_bot:
        return
    try:
        await remove_seen_member(message.chat.id, member.id)
    except Exception:
        pass
    await _maybe_farewell(message.chat, message.bot, member, 'leave')


# --------------------------------------------------- group commands → PM --
async def _settings_redirect(message: Message, title: str, hint: str) -> None:
    """Group-side config commands now point to the private panel."""
    username = await get_bot_username(message.bot)
    markup = None
    if username:
        markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')])
    await message.answer(box(title, [
        quote(sc(hint)),
    ]), reply_markup=markup)


@router.message(Command('welcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_welcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    await _settings_redirect(message, 'Welcome 👋', 'Welcome settings now live in my private chat — tap the button below.')


@router.message(Command('goodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_goodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    await _settings_redirect(message, 'Goodbye 🚪', 'Goodbye settings now live in my private chat — tap the button below.')


@router.message(Command('setwelcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setwelcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    await _settings_redirect(message, 'Welcome 👋', 'Welcome settings now live in my private chat — tap the button below.')


@router.message(Command('setgoodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setgoodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    await _settings_redirect(message, 'Goodbye 🚪', 'Goodbye settings now live in my private chat — tap the button below.')
