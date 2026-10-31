from __future__ import annotations

import asyncio
import random
import time

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReactionTypeEmoji

from bot.core.config import REACTION_EMOJIS, REACT_POOL
from bot.core.logger import get_logger
from bot.database import get_settings, update_setting
from bot.utils.helpers import is_message_sender_admin
from bot.utils.ui import box, dot, kb, row, sc, tbtn

router = Router()
log = get_logger('REACTIONS')

MIN_DELAY = 0.20
MAX_DELAY = 0.55

MODE_LABELS = {'random': '🎲', 'cycle': '🔄', 'fixed': '📌'}


# ------------------------------------------------------- rate limiting ----
class _ReactionGate:
    """Reactions look best when they land fast, but Telegram rate-limits
   setMessageReaction. This gate spaces them ~1s apart and drops the
    backlog instead of flooding (and getting the bot limited)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last = 0.0
        self._pending = 0

    async def run(self, action) -> None:
        if self._pending >= 12:
            return
        self._pending += 1
        try:
            async with self._lock:
                wait = self._last + 1.0 - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last = time.monotonic()
                await action()
        finally:
            self._pending -= 1


_gate = _ReactionGate()
# in-memory rotation cursor for cycle mode (no disk writes needed)
_cycle_cursor: dict[int, int] = {}


def _is_service_message(message: Message) -> bool:
    for field in (
        'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo',
        'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created',
        'channel_chat_created', 'message_auto_delete_timer_changed', 'pinned_message',
    ):
        if getattr(message, field, None):
            return True
    return False


def _pick_emoji(chat_id: int, settings: dict) -> str:
    mode = settings.get('reaction_mode') or 'random'
    emojis = [e for e in (settings.get('reaction_emojis') or []) if e in REACTION_EMOJIS]
    if not emojis:
        emojis = ['🔥', '❤', '👏', '🎉', '💯']
    if mode == 'fixed':
        return emojis[0]
    if mode == 'cycle':
        index = _cycle_cursor.get(chat_id, 0)
        _cycle_cursor[chat_id] = index + 1
        return emojis[index % len(emojis)]
    if emojis and len(emojis) > 1 and random.random() < 0.75:
        return random.choice(emojis)
    return random.choice(REACT_POOL)


async def react_to_message(message: Message, settings: dict | None = None) -> None:
    try:
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        if settings is None:
            settings = await get_settings(message.chat.id)
        if not settings.get('reaction_enabled'):
            return
        emoji = _pick_emoji(message.chat.id, settings)

        async def _do() -> None:
            await message.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
                is_big=True,
            )

        await _gate.run(_do)
    except Exception as error:
        log.warn('Could not react in %s: %s', message.chat.id, error)


def maybe_react(message: Message, settings: dict) -> None:
    """Fire-and-forget: schedules a reaction without blocking the update."""
    if not settings.get('reaction_enabled'):
        return
    user = message.from_user
    if user is not None and user.is_bot and message.sender_chat is None:
        return
    asyncio.create_task(react_to_message(message, settings))


# ------------------------------------------------------------ command -----
async def _reaction_status_text(chat_id: int) -> str:
    s = await get_settings(chat_id)
    mode = s.get('reaction_mode') or 'random'
    emojis = ' '.join(s.get('reaction_emojis') or []) or '(ᴅᴇꜰᴀᴜʟᴛ ꜱᴇᴛ)'
    return box('Super Reactions 🎭', [
        row('Status', f'{dot(bool(s.get("reaction_enabled")))} <b>{sc("On") if s.get("reaction_enabled") else sc("Off")}</b>'),
        row('Mode', f'{MODE_LABELS.get(mode, "🎲")} <b>{sc(mode)}</b>'),
        row('Set', emojis),
        '',
        '<blockquote>💡 ' + sc('Full emoji picker + presets live in my private chat — Settings → this chat → Reactions.') + '</blockquote>',
    ])


async def _handle_reaction_command(message: Message):
    if not await is_message_sender_admin(message):
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    parts = (message.text or '').split(maxsplit=1)
    arg = parts[1].strip().casefold() if len(parts) > 1 else ''
    if arg in {'on', 'off'}:
        await update_setting(message.chat.id, 'reaction_enabled', arg == 'on')
    s = await get_settings(message.chat.id)
    markup = kb([tbtn('Reactions', bool(s.get('reaction_enabled')), f'tgl:rx:{message.chat.id}')])
    await message.answer(await _reaction_status_text(message.chat.id), reply_markup=markup)


@router.message(Command('reaction'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_reaction_group(message: Message):
    await _handle_reaction_command(message)


@router.channel_post(Command('reaction'))
async def cmd_reaction_channel(message: Message):
    await _handle_reaction_command(message)


@router.callback_query(F.data.startswith('rxq:'))
async def cb_reaction_quick(callback: CallbackQuery):
    """Quick on/off flip from the /reaction card inside a group."""
    try:
        chat_id = int(callback.data.split(':')[1])
    except (IndexError, ValueError):
        await callback.answer('Invalid request.', show_alert=True)
        return
    from bot.utils.helpers import is_admin, safe_edit

    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer('Admins only.', show_alert=True)
        return
    s = await get_settings(chat_id)
    new_state = not bool(s.get('reaction_enabled'))
    await update_setting(chat_id, 'reaction_enabled', new_state)
    await callback.answer(f"{'✅' if new_state else '❌'} {'On' if new_state else 'Off'}")
    await safe_edit(callback.message, await _reaction_status_text(chat_id), kb([tbtn('Reactions', new_state, f'tgl:rx:{chat_id}')]))


# ------------------------------------------------------------- engines ----
@router.message(F.chat.type.in_({'group', 'supergroup'}), ~F.text.startswith('/'))
async def on_new_group_message(message: Message):
    if _is_service_message(message):
        raise SkipHandler
    settings = await get_settings(message.chat.id)
    if settings.get('reaction_enabled'):
        maybe_react(message, settings)
    raise SkipHandler


@router.channel_post(~F.text.startswith('/'))
async def on_new_channel_post(message: Message):
    settings = await get_settings(message.chat.id)
    if settings.get('reaction_enabled'):
        maybe_react(message, settings)
    raise SkipHandler
