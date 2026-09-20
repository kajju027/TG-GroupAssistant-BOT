import asyncio
import random

from aiogram import Router, F
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.dispatcher.event.bases import SkipHandler

from bot.database import get_settings, update_setting, next_reaction_index
from bot.utils.helpers import is_message_sender_admin
from bot.core.logger import get_logger

router = Router()
log = get_logger("REACTIONS")

MIN_DELAY = 3
MAX_DELAY = 7

ALLOWED_EMOJI = {
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱",
    "🤬", "😢", "🎉", "🤩", "🤮", "💩", "🙏", "👌", "🕊", "🤡",
    "🥱", "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🌭", "💯", "🤣", "⚡",
    "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈",
    "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇", "😨",
    "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿",
    "🆒", "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂",
    "🤷", "🤷‍♀", "😡",
}

AUTOMATIC_POOL = [
    "👍", "🔥", "❤", "🎉", "🤩", "👏", "😁", "🥰", "💯", "⚡",
]


async def _is_authorized(message: Message) -> bool:
    if message.chat.type == "channel":
        return True
    return await is_message_sender_admin(message)


def _status_text(s: dict) -> str:
    status = "✅ ON" if s.get("reaction_enabled") else "❌ OFF"
    mode = s.get("reaction_mode", "automatic")
    emojis = s.get("reaction_emojis") or ["👍"]
    emoji_line = " ".join(emojis) if mode == "custom" else "(auto-picked)"
    return (
        "🎭 <b>Auto-Reaction Settings</b>\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Mode:</b> {mode.upper()}\n"
        f"<b>Emojis:</b> {emoji_line}\n\n"
        "Every new post gets a reaction a few seconds after it arrives, "
        "no matter who posted it.\n\n"
        "<b>Usage:</b>\n"
        "/reaction on — enable\n"
        "/reaction off — disable\n"
        "/reaction mode automatic|custom — choose mode\n"
        "/reaction emoji [emoji1, emoji2, ...] — set custom emojis\n\n"
        "Works in both groups and channels."
    )


async def _handle_reaction_command(message: Message):
    if not await _is_authorized(message):
        await message.answer("❌ <b>Admins only.</b>")
        return

    parts = (message.text or "").split(maxsplit=2)
    s = await get_settings(message.chat.id)

    if len(parts) < 2:
        await message.answer(_status_text(s))
        return

    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "reaction_enabled", True)
        await message.answer(f"✅ <b>Auto-reaction enabled.</b>\nMode: {s.get('reaction_mode', 'automatic').upper()}")
    elif cmd == "off":
        await update_setting(message.chat.id, "reaction_enabled", False)
        await message.answer("❌ <b>Auto-reaction disabled.</b>")
    elif cmd == "mode":
        if len(parts) < 3 or parts[2].strip().lower() not in ("automatic", "custom"):
            await message.answer("<b>Usage:</b> /reaction mode automatic|custom")
            return
        mode = parts[2].strip().lower()
        await update_setting(message.chat.id, "reaction_mode", mode)
        await message.answer(f"✅ Mode set to <b>{mode.upper()}</b>.")
    elif cmd == "emoji":
        if len(parts) < 3 or not parts[2].strip():
            await message.answer(
                "<b>Usage:</b> /reaction emoji [emoji1, emoji2, ...]\n\n"
                "<b>Example:</b> /reaction emoji 🔥, ☘️, 🌚"
            )
            return
        raw = parts[2].strip()
        candidates = [e.strip() for e in raw.replace(",", " ").split() if e.strip()]
        valid = [e for e in candidates if e in ALLOWED_EMOJI]
        invalid = [e for e in candidates if e not in ALLOWED_EMOJI]
        if not valid:
            sample = " ".join(list(ALLOWED_EMOJI)[:12])
            await message.answer(
                "❌ None of those are supported as Telegram reactions.\n"
                f"Try some of: {sample} ..."
            )
            return
        await update_setting(message.chat.id, "reaction_emojis", valid)
        await update_setting(message.chat.id, "reaction_mode", "custom")
        await update_setting(message.chat.id, "_reaction_index", 0)
        msg = f"✅ Custom emojis set: {' '.join(valid)}\nMode switched to CUSTOM."
        if invalid:
            msg += f"\n⚠️ Skipped unsupported: {' '.join(invalid)}"
        await message.answer(msg)
    else:
        await message.answer(_status_text(s))


@router.message(Command("reaction"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_reaction_group(message: Message):
    await _handle_reaction_command(message)


@router.channel_post(Command("reaction"))
async def cmd_reaction_channel(message: Message):
    await _handle_reaction_command(message)


async def _react_after_delay(message: Message):
    try:
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        s = await get_settings(message.chat.id)
        if not s.get("reaction_enabled"):
            return

        mode = s.get("reaction_mode", "automatic")
        if mode == "custom":
            emojis = s.get("reaction_emojis") or ["👍"]
            if len(emojis) == 1:
                emoji = emojis[0]
            else:
                idx = await next_reaction_index(message.chat.id)
                emoji = emojis[idx % len(emojis)]
        else:
            emoji = random.choice(AUTOMATIC_POOL)

        await message.bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
        )
    except TelegramBadRequest as e:
        log.warn(f"Could not react in {message.chat.id}: {e}")
    except Exception as e:
        log.warn(f"Unexpected error reacting in {message.chat.id}: {e}")


@router.message(F.chat.type.in_({"group", "supergroup"}), ~F.text.startswith("/"))
async def on_new_group_message(message: Message):
    s = await get_settings(message.chat.id)
    if s.get("reaction_enabled"):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler


@router.channel_post(~F.text.startswith("/"))
async def on_new_channel_post(message: Message):
    s = await get_settings(message.chat.id)
    if s.get("reaction_enabled"):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler
