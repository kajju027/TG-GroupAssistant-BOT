from __future__ import annotations

import time

from html import escape

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import ChatMemberUpdatedFilter, Command, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import ChatMemberUpdated, Message

from bot.database import get_settings, note_seen_member, remove_seen_member, update_setting
from bot.utils import anim
from bot.utils.helpers import mention_by_name
from bot.utils.ui import box, bold, mono, quote, row, sc, sep

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


def _format_msg(template: str, user, chat, member_count: int) -> str:
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


async def _send_welcome(bot, chat, user, template: str, count: int) -> None:
    text = _format_msg(template, user, chat, count)
    try:
        await anim.play_in_chat(bot, chat.id, text, kind='welcome', parse_mode='HTML')
    except Exception:
        pass


async def _send_goodbye(bot, chat, user, template: str, count: int) -> None:
    text = _format_msg(template, user, chat, count)
    try:
        await anim.play_in_chat(bot, chat.id, text, kind='goodbye', parse_mode='HTML')
    except Exception:
        pass


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    if user.is_bot:
        raise SkipHandler
    try:
        await note_seen_member(event.chat.id, user.id, user.full_name, user.is_bot)
    except Exception:
        pass
    key = (event.chat.id, user.id, 'join')
    if _seen_recently(key):
        raise SkipHandler
    _mark(key)
    settings = await get_settings(event.chat.id)
    if settings['welcome']:
        count = await _member_count(event.bot, event.chat.id)
        await _send_welcome(event.bot, event.chat, user, settings['welcome_msg'], count)
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
    key = (event.chat.id, user.id, 'leave')
    if _seen_recently(key):
        raise SkipHandler
    _mark(key)
    settings = await get_settings(event.chat.id)
    if settings['goodbye']:
        count = await _member_count(event.bot, event.chat.id)
        await _send_goodbye(event.bot, event.chat, user, settings['goodbye_msg'], count)
    raise SkipHandler


@router.message(F.new_chat_members)
async def on_new_members(message: Message):
    settings = await get_settings(message.chat.id)
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        try:
            await note_seen_member(message.chat.id, member.id, member.full_name, member.is_bot)
        except Exception:
            pass
        key = (message.chat.id, member.id, 'join')
        if _seen_recently(key):
            continue
        if not settings['welcome']:
            continue
        _mark(key)
        count = await _member_count(message.bot, message.chat.id)
        await _send_welcome(message.bot, message.chat, member, settings['welcome_msg'], count)


@router.message(F.left_chat_member)
async def on_left_member(message: Message):
    member = message.left_chat_member
    if member is None or member.is_bot:
        return
    try:
        await remove_seen_member(message.chat.id, member.id)
    except Exception:
        pass
    key = (message.chat.id, member.id, 'leave')
    if _seen_recently(key):
        return
    settings = await get_settings(message.chat.id)
    if not settings['goodbye']:
        return
    _mark(key)
    count = await _member_count(message.bot, message.chat.id)
    await _send_goodbye(message.bot, message.chat, member, settings['goodbye_msg'], count)


@router.message(Command('welcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_welcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        settings = await get_settings(message.chat.id)
        status = '✅ ON' if settings['welcome'] else '❌ OFF'
        await message.answer(
            box('Welcome Settings', [
                row('Status', status, '👋'),
                row('Message', mono(settings['welcome_msg'][:120]), '📝'),
                sep(),
                row('Toggle', '/welcome on | off', '⚙️'),
                row('Custom', '/setwelcome &lt;text&gt;', '✏️'),
            ]),
            parse_mode='HTML',
        )
    elif parts[1].casefold() in {'on', 'off'}:
        enabled = parts[1].casefold() == 'on'
        await update_setting(message.chat.id, 'welcome', enabled)
        text = box('Welcome', [
            f"  {'✅' if enabled else '❌'} {sc('Welcome messages')} — {bold(sc('Enabled') if enabled else sc('Disabled'))}",
            sep(),
            quote(sc('New members will be greeted with an animation.') if enabled else sc('Welcome messages turned off.')),
        ])
        await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')
    else:
        await message.answer('<b>Usage:</b> /welcome on|off')


@router.message(Command('goodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_goodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        settings = await get_settings(message.chat.id)
        status = '✅ ON' if settings['goodbye'] else '❌ OFF'
        await message.answer(
            box('Goodbye Settings', [
                row('Status', status, '👋'),
                row('Message', mono(settings['goodbye_msg'][:120]), '📝'),
                sep(),
                row('Toggle', '/goodbye on | off', '⚙️'),
                row('Custom', '/setgoodbye &lt;text&gt;', '✏️'),
            ]),
            parse_mode='HTML',
        )
    elif parts[1].casefold() in {'on', 'off'}:
        enabled = parts[1].casefold() == 'on'
        await update_setting(message.chat.id, 'goodbye', enabled)
        text = box('Goodbye', [
            f"  {'✅' if enabled else '❌'} {sc('Goodbye messages')} — {bold(sc('Enabled') if enabled else sc('Disabled'))}",
            sep(),
            quote(sc('Leaving members will get a stylish farewell.') if enabled else sc('Goodbye messages turned off.')),
        ])
        await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')
    else:
        await message.answer('<b>Usage:</b> /goodbye on|off')


@router.message(Command('setwelcome'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setwelcome(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            box('Set Welcome', [
                row('Usage', '/setwelcome &lt;text&gt;', '✏️'),
                sep(),
                row('{mention}', sc('user mention'), '👤'),
                row('{name}', sc('full name'), '📛'),
                row('{username}', sc('@username'), '🔗'),
                row('{group}', sc('group name'), '👥'),
                row('{count}', sc('member count'), '🔢'),
                row('{id}', sc('user id'), '🆔'),
            ]),
            parse_mode='HTML',
        )
        return
    await update_setting(message.chat.id, 'welcome_msg', parts[1][:4000])
    preview = escape(parts[1][:120]) + ('…' if len(parts[1]) > 120 else '')
    text = box('Welcome Updated', [
        quote(preview),
        sep(),
        f"  ✅ {sc('Saved successfully')}",
    ])
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')


@router.message(Command('setgoodbye'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_setgoodbye(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            box('Set Goodbye', [
                row('Usage', '/setgoodbye &lt;text&gt;', '✏️'),
                sep(),
                row('{mention}', sc('user mention'), '👤'),
                row('{name}', sc('full name'), '📛'),
                row('{username}', sc('@username'), '🔗'),
                row('{group}', sc('group name'), '👥'),
                row('{count}', sc('member count'), '🔢'),
                row('{id}', sc('user id'), '🆔'),
            ]),
            parse_mode='HTML',
        )
        return
    await update_setting(message.chat.id, 'goodbye_msg', parts[1][:4000])
    preview = escape(parts[1][:120]) + ('…' if len(parts[1]) > 120 else '')
    text = box('Goodbye Updated', [
        quote(preview),
        sep(),
        f"  ✅ {sc('Saved successfully')}",
    ])
    await anim.play(message, text, kind='success', delay=anim.FAST_DELAY, parse_mode='HTML')
