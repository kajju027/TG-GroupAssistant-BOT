from __future__ import annotations

import asyncio

from aiogram.exceptions import TelegramBadRequest

from bot.core.config import ANIMATIONS

FRAMES: dict[str, list[str]] = {
    "welcome": ["👋", "👋 ✨", "✨ 👋 ✨", "🎉 ✨ 👋 ✨ 🎉"],
    "goodbye": ["🚶", "🚶 🚶", "👋 🚶 👋", "😢 👋 🚶 😢"],
    "tag": ["📣", "📣 📣", "📣 📣 📣", "📢 📣 📣 📢"],
    "loading": ["⏳", "🕐", "🕒", "⌛"],
    "success": ["✨", "✨ ✅", "🎉 ✅ 🎉"],
    "ban": ["🔨", "🔨 🔨", "💥 🔨 🔨 💥"],
    "kick": ["👢", "💨 👟", "🚪 💨 👟"],
    "mute": ["🔇", "🔇 🔇", "🤐 🔇 🤐"],
    "warn": ["⚠️", "⚠️ ⚠️", "⚡ ⚠️ ⚠️ ⚡"],
    "sparkle": ["✨", "✨ ✨", "✨ 🌟 ✨", "🌟 ✨ ✨ 🌟"],
}

DEFAULT_DELAY = 0.45
FAST_DELAY = 0.35


def animations_enabled() -> bool:
    return ANIMATIONS


def get_frames(kind: str) -> list[str]:
    return FRAMES.get(kind, FRAMES["sparkle"])


async def play(
    message,
    text: str,
    kind: str = "sparkle",
    delay: float = DEFAULT_DELAY,
    **kwargs,
):
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


async def play_in_chat(
    bot,
    chat_id: int,
    text: str,
    kind: str = "sparkle",
    delay: float = DEFAULT_DELAY,
    **kwargs,
):
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
