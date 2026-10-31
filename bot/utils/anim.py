from __future__ import annotations

import asyncio
import random

from aiogram.exceptions import TelegramBadRequest

from bot.core.config import ANIMATIONS

# Every kind has several DIFFERENT animation sets. A random set is picked each
# time, so consecutive events never repeat the same animation.
FRAME_SETS: dict[str, list[list[str]]] = {
    'welcome': [
        ['✨', '✨ 🌟', '🌟 ✨ 🌟', '✨ 🎉 ✨ 🎉 ✨', '🎉 ✨ 👋 ✨ 🎉'],
        ['▁', '▃', '▅', '▆', '▇', '█ Wᴇʟᴄᴏᴍᴇ █'],
        ['W', 'We', 'Wel', 'Welc', 'Welco', 'Welcome', 'Wᴇʟᴄᴏᴍᴇ ✨'],
        ['🚪', '🚪 🚶', '🚶 🏃', '🏃 🎊', '🎊 🎉 👋 🎉 🎊'],
        ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦ Wᴇʟᴄᴏᴍᴇ ⠖'],
        ['◦', '○', '◌', '◎', '◉ 🎉', '🎉 🎉'],
    ],
    'goodbye': [
        ['👋', '👋 💨', '🚶 💨', '🚶‍♂️ 💨 💨', '🚪 😢 🚪'],
        ['▇', '▆', '▄', '▂', '▁', 'Gᴏᴏᴅʙʏᴇ 💫'],
        ['G', 'Go', 'Goo', 'Good', 'Goodb', 'Goodbye', 'Gᴏᴏᴅʙʏᴇ 👋'],
        ['● ● ●', '● ● ○', '● ○ ○', '○ ○ ○', '○ ○ ◌'],
        ['⠋', '⠙', '⠹', '⠸', '⠼ Gᴏᴏᴅʙʏᴇ ⠴'],
    ],
    'tag': [
        ['📣', '📣 📣', '📢 📣 📣', '📣 📣 📣 📣', '📢 📣 🫵 📣 📢'],
        ['░░░░', '▓░░░', '▓▓░░', '▓▓▓░', '▓▓▓▓', '🫵'],
        ['T', 'Ta', 'Tag', 'Tagg', 'Taggi', 'Taggin', 'Tagging…', 'Tᴀɢɢɪɴɢ 🫵'],
        ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦ 🫵 ⠖'],
        ['👉', '👉 👉', '🫵 👉 👉', '👉 🫵 🫵 🫵 👉'],
    ],
    'success': [
        ['✅', '✅ ✅', '🎉 ✅ 🎉'],
        ['░', '▒', '▓', '█', '✅'],
        ['.', '..', '...', '✅'],
        ['⠋', '⠙', '⠹', '⠸', '⠼ ✅ ⠴'],
        ['✨', '✨ ✔', '✔ ✅ ✔'],
    ],
    'ban': [
        ['🔨', '🔨 🔨', '💥 🔨 🔨 💥', '🚫 💥 🚫'],
        ['B', 'Ba', 'Ban', 'Bann', 'Banned', 'Bᴀɴɴᴇᴅ 🚫'],
        ['▓▓▓', '▓▓░', '▓░░', '░░░', '🚫'],
        ['⠋', '⠙', '⠹', '⠸ 🚫 ⠼'],
    ],
    'kick': [
        ['👟', '💨 👟', '💨 👟 💨', '🚪 💨 👟 💨'],
        ['K', 'Ki', 'Kic', 'Kick', 'Kicked', 'Kɪᴄᴋᴇᴅ 🥾'],
        ['→', '→ →', '👟 → →', '🚪 → 👟 →'],
    ],
    'mute': [
        ['🔇', '🔇 🔇', '🤐 🔇 🤐', '🔇 🤐 🔇'],
        ['M', 'Mu', 'Mut', 'Mute', 'Muted', 'Mᴜᴛᴇᴅ 🔇'],
        ['🔊', '🔉', '🔈', '🔇'],
    ],
    'warn': [
        ['⚠️', '⚠️ ⚠️', '⚡ ⚠️ ⚠️ ⚡'],
        ['W', 'Wa', 'War', 'Warn', 'Warned', 'Wᴀʀɴᴇᴅ ⚠️'],
        ['▓', '▓▓', '▓▓▓', '⚠️'],
    ],
    'loading': [
        ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        ['⏳', '🕐', '🕑', '🕒', '🕓', '⌛'],
        ['◐', '◓', '◑', '◒'],
        ['░░░', '▓░░', '▓▓░', '▓▓▓'],
    ],
    'sparkle': [
        ['✨', '✨ ✨', '✨ 🌟 ✨', '🌟 ✨ ✨ 🌟'],
        ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴'],
        ['˖', '˖ ✦', '✦ ˖ ✦', '✦ ✧ ✦ ✧ ✦'],
        ['◦', '○', '◎', '◉', '✨'],
        ['▁', '▃', '▅', '▆', '▇'],
    ],
}

DEFAULT_DELAY = 0.45
FAST_DELAY = 0.35

# Remember which set was shown last for each kind so two consecutive events
# never repeat the same animation.
_last_pick: dict[str, int] = {}


def animations_enabled() -> bool:
    return ANIMATIONS


def get_frames(kind: str) -> list[str]:
    """Return a randomly chosen animation set for the given kind.

    The previous set of this kind is excluded, so back-to-back events (two
    welcomes in a row, two bans in a row...) always look different.
    """
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
    """Send `text` to the message's chat with a random animated intro.

    The intro frames are edited in place; any Telegram error degrades to a
    plain, non-animated send so a message is never lost.
    """
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
    """Same as play(), but for a raw chat id (welcome, goodbye, tag headers)."""
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
