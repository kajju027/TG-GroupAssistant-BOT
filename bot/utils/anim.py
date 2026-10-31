from __future__ import annotations

import asyncio
import random

from aiogram.exceptions import TelegramBadRequest

from bot.core.config import ANIMATIONS

# Short intro animations — a couple of frames, fast pacing. When
# ANIMATIONS=false (default) every message is sent instantly instead.
FRAME_SETS: dict[str, list[list[str]]] = {
    'welcome': [
        ['✨', '🎉 ✨ 👋 ✨ 🎉'],
        ['▁', '▄', '█ Wᴇʟᴄᴏᴍᴇ █'],
        ['⠋', '⠙', '⠹ Wᴇʟᴄᴏᴍᴇ ⠸'],
    ],
    'goodbye': [
        ['👋', '🚶 💨', '🚪 👋'],
        ['▇', '▄', '▁ Gᴏᴏᴅʙʏᴇ'],
        ['⠋', '⠙ Gᴏᴏᴅʙʏᴇ ⠸'],
    ],
    'tag': [
        ['📣', '📢 📣 📣', '📢 📣 🫵 📣 📢'],
        ['░░░░', '▓▓░░', '▓▓▓▓ 🫵'],
        ['⠋', '⠙', '⠹ 🫵 ⠸'],
    ],
    'success': [
        ['✅', '🎉 ✅ 🎉'],
        ['░', '▓', '█ ✅'],
        ['⠋', '⠙ ✅ ⠸'],
    ],
    'ban': [
        ['🔨', '💥 🔨 🔨 💥', '🚫 💥 🚫'],
        ['B', 'Ban', 'Bᴀɴɴᴇᴅ 🚫'],
    ],
    'kick': [
        ['👟', '💨 👟 💫', '🚪 👟 💨'],
        ['K', 'Kick', 'Kɪᴄᴋᴇᴅ 🥾'],
    ],
    'mute': [
        ['🔊', '🔉', '🔇'],
        ['M', 'Mute', 'Mᴜᴛᴇᴅ 🔇'],
    ],
    'warn': [
        ['⚠️', '⚡ ⚠️ ⚡'],
        ['W', 'Warn', 'Wᴀʀɴᴇᴅ ⚠️'],
    ],
    'sparkle': [
        ['✨', '✨ 🌟 ✨', '🌟 ✨ ✨ 🌟'],
        ['⠋', '⠙', '⠹ ✨ ⠸'],
    ],
}

DEFAULT_DELAY = 0.18
FAST_DELAY = 0.18

_last_pick: dict[str, int] = {}


def animations_enabled() -> bool:
    return ANIMATIONS


def get_frames(kind: str) -> list[str]:
    """A random animation set; the previous pick is excluded so two events
    in a row never repeat the same animation."""
    sets = FRAME_SETS.get(kind) or FRAME_SETS['sparkle']
    if len(sets) > 1:
        last = _last_pick.get(kind)
        candidates = [index for index in range(len(sets)) if index != last]
        pick = random.choice(candidates)
    else:
        pick = 0
    _last_pick[kind] = pick
    return sets[pick]


async def play(message, text: str, kind: str = 'sparkle', delay: float = DEFAULT_DELAY, **kwargs):
    """Send text with a short animated intro. Any Telegram error degrades
    to a plain send, so a message is never lost."""
    frames = get_frames(kind)
    if not ANIMATIONS:
        return await message.answer(text, **kwargs)

    sent = None
    try:
        sent = await message.answer(frames[0], **kwargs)
    except TelegramBadRequest:
        return await message.answer(text, **kwargs)

    for frame in frames[1:]:
        await asyncio.sleep(delay)
        try:
            await sent.edit_text(frame, **kwargs)
        except TelegramBadRequest:
            pass

    await asyncio.sleep(delay)
    try:
        await sent.edit_text(text, **kwargs)
        return sent
    except TelegramBadRequest:
        try:
            return await message.answer(text, **kwargs)
        except TelegramBadRequest:
            return sent


async def play_in_chat(bot, chat_id: int, text: str, kind: str = 'sparkle', delay: float = DEFAULT_DELAY, **kwargs):
    frames = get_frames(kind)
    if not ANIMATIONS:
        return await bot.send_message(chat_id, text, **kwargs)

    sent = None
    try:
        sent = await bot.send_message(chat_id, frames[0], **kwargs)
    except TelegramBadRequest:
        return await bot.send_message(chat_id, text, **kwargs)

    for frame in frames[1:]:
        await asyncio.sleep(delay)
        try:
            await sent.edit_text(frame, **kwargs)
        except TelegramBadRequest:
            pass

    await asyncio.sleep(delay)
    try:
        await sent.edit_text(text, **kwargs)
        return sent
    except TelegramBadRequest:
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except TelegramBadRequest:
            return sent


async def edit_safe(message, text: str, **kwargs) -> bool:
    try:
        await message.edit_text(text, **kwargs)
        return True
    except TelegramBadRequest:
        return False
