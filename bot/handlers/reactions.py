"""
bot/handlers/reactions.py — delayed emoji auto-reaction on new posts.

Works in BOTH groups/supergroups (normal messages) and channels
(channel posts). When enabled for a chat, every new message/post gets
an emoji reaction a few seconds after it arrives (a small delay so the
bot doesn't hammer Telegram's reaction-rate-limit when a chat is busy).

Commands (admin-only in groups, channel-admin-only in channels — see
_is_authorized below):
    /reaction on|off            — toggle the feature for this chat
    /reaction emoji <emoji>     — change which emoji is used
    /reaction                   — show current status/emoji
"""

import asyncio
import random

from aiogram import Router, F
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.dispatcher.event.bases import SkipHandler

from bot.database import get_settings, update_setting
from bot.utils.helpers import is_message_sender_admin
from bot.core.logger import get_logger

router = Router()
log = get_logger("REACTIONS")

# Small random delay window (seconds) before reacting, so a burst of
# messages doesn't fire a burst of setMessageReaction calls at once
# and trip Telegram's per-chat rate limit.
_MIN_DELAY = 3
_MAX_DELAY = 7

# Telegram only accepts a fixed set of "standard" reaction emoji via
# the Bot API. This is not the complete list, just a safe, commonly
# supported subset for validating /reaction emoji input up front
# instead of only finding out from a failed API call.
_ALLOWED_EMOJI = {
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱",
    "🎉", "🤩", "😢", "😡", "🤝", "🙏", "👌", "🕊", "🤡", "🥱",
    "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🎁", "💯", "🤣", "⚡", "☘️",
    "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴",
    "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇", "😨", "🤝",
    "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒",
    "💘", "🙉", "👀", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷",
    "🤷‍♀", "😡",
}


async def _is_authorized(message: Message) -> bool:
    """Admin in a group/supergroup. In a channel, Telegram only lets
    admins post at all, so any channel_post is inherently from an
    admin (there's no per-post user identity to check)."""
    if message.chat.type == "channel":
        return True
    return await is_message_sender_admin(message)


def _status_text(s: dict) -> str:
    status = "✅ ON" if s.get("reaction_enabled") else "❌ OFF"
    emoji = s.get("reaction_emoji") or "👍"
    return (
        "🎭 <b>Auto-Reaction Settings</b>\n\n"
        f"Status: {status}\n"
        f"Emoji: {emoji}\n\n"
        "Usage:\n"
        "/reaction on — enable\n"
        "/reaction off — disable\n"
        "/reaction emoji [emoji] — change emoji\n\n"
        "Works in both groups and channels."
    )


async def _handle_reaction_command(message: Message):
    if not await _is_authorized(message):
        await message.answer("❌ Admins only.")
        return

    parts = (message.text or "").split(maxsplit=2)
    s = await get_settings(message.chat.id)

    if len(parts) < 2:
        await message.answer(_status_text(s))
        return

    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "reaction_enabled", 1)
        await message.answer(f"✅ Auto-reaction <b>enabled</b>. Emoji: {s.get('reaction_emoji') or '👍'}")
    elif cmd == "off":
        await update_setting(message.chat.id, "reaction_enabled", 0)
        await message.answer("❌ Auto-reaction <b>disabled</b>.")
    elif cmd == "emoji":
        if len(parts) < 3 or not parts[2].strip():
            await message.answer("Usage: /reaction emoji [emoji]\n\nExample: /reaction emoji 🔥")
            return
        emoji = parts[2].strip().split()[0]
        if emoji not in _ALLOWED_EMOJI:
            sample = " ".join(list(_ALLOWED_EMOJI)[:12])
            await message.answer(
                "❌ That emoji isn't supported as a Telegram reaction.\n"
                f"Try one of: {sample} ..."
            )
            return
        await update_setting(message.chat.id, "reaction_emoji", emoji)
        await message.answer(f"✅ Reaction emoji set to {emoji}")
    else:
        await message.answer(_status_text(s))


# ── Group/supergroup: /reaction command ──────────────────────────
@router.message(Command("reaction"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_reaction_group(message: Message):
    await _handle_reaction_command(message)


# ── Channel: /reaction command sent as a channel post ────────────
@router.channel_post(Command("reaction"))
async def cmd_reaction_channel(message: Message):
    await _handle_reaction_command(message)


async def _react_after_delay(message: Message):
    try:
        await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))
        s = await get_settings(message.chat.id)
        if not s.get("reaction_enabled"):
            return
        emoji = s.get("reaction_emoji") or "👍"
        await message.bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
        )
    except TelegramBadRequest as e:
        # E.g. the message was deleted before we got to react to it,
        # or the emoji became invalid — not worth crashing the bot over.
        log.warn(f"Could not react in {message.chat.id}: {e}")
    except Exception as e:
        log.warn(f"Unexpected error reacting in {message.chat.id}: {e}")


# ── New posts in a GROUP/SUPERGROUP ──────────────────────────────
# Registered with no Command filter of its own, but explicitly skips
# text starting with "/" so it never competes with any command router.
# Always raises SkipHandler so this NEVER "claims" the update — other
# feature routers (antilink/antiword/antispam/filters) still get to
# process the very same message regardless of where this router sits
# in main.py's include_router order.
@router.message(F.chat.type.in_({"group", "supergroup"}), ~F.text.startswith("/"))
async def on_new_group_message(message: Message):
    s = await get_settings(message.chat.id)
    if s.get("reaction_enabled"):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler


# ── New posts in a CHANNEL ────────────────────────────────────────
@router.channel_post(~F.text.startswith("/"))
async def on_new_channel_post(message: Message):
    s = await get_settings(message.chat.id)
    if s.get("reaction_enabled"):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler
