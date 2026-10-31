"""Auto reactions — legacy /react + /setreact command surface.

The bot's modern super-reactions engine lives in `reactions.py` and is the
recommended path: random/cycle/fixed modes, big emoji pool, full picker in
the private settings panel.

This module keeps the old /react and /setreact commands working for users
who already use them. It is fully compatible with the new engine:

  • When the new engine (`reaction_enabled`) is ON for a chat, the legacy
    engine silently stands down so the chat never gets double-reacted.
  • When the new engine is OFF but the legacy toggle (`legacy_react_enabled`)
    is ON, this engine handles both groups and channels.
  • Reactions are always sent with `is_big=True` so they render as big
    animated reactions on every Telegram client.

The legacy engine also rotates through a small pool of "big" emojis even
when a single fixed emoji was configured, so reactions look animated and
varied instead of always being the same one.
"""
from __future__ import annotations

import random

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

from bot.core import database as core_db
from bot.database import get_settings, update_setting
from bot.utils.filters import AllowedFilter
from bot.utils.ui import bold, box, italic, quote, row, sc, sep, status_icon

router = Router()

_GRP = F.chat.type.in_({"group", "supergroup"})

# Default pool when "random" is picked. Chosen for visual variety — each
# one renders as a big animated reaction on Telegram clients.
_LEGACY_POOL = ['🔥', '❤', '🎉', '👏', '💯', '⚡', '🤩', '🥰', '🏆', '😍']


async def _set_reaction(bot: Bot, chat_id: int, message_id: int, emoji: str) -> None:
    try:
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
            is_big=True,
        )
        core_db.inc_stat("reactions")
    except Exception:
        pass


def _pick_emoji(stored: str | None) -> str:
    """`random` rotates through the pool; anything else is honoured as a
    fixed emoji (still applied as a big animation)."""
    raw = (stored or '').strip()
    if raw.lower() == 'random' or not raw:
        return random.choice(_LEGACY_POOL)
    return raw.split()[0] or '🔥'


@router.message(Command("react"), AllowedFilter(), _GRP)
async def toggle_react_cmd(message: Message):
    core_db.inc_stat("commands")
    args = message.text.split()
    settings = await get_settings(message.chat.id)

    # If the modern engine is on, /react doesn't fight it — show the modern
    # status instead.
    if settings.get('reaction_enabled'):
        await message.reply(
            box("Auto Reactions ⚡", [
                row("Engine", bold(sc("Super Reactions (new)"))),
                row("Status", bold("🟢 " + sc("On"))),
                sep(),
                italic(sc('Use /reaction for the modern engine, or disable Super Reactions in Settings to use the legacy /setreact emoji.')),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        enabled = bool(settings.get('legacy_react_enabled'))
        emoji = settings.get('legacy_react_emoji') or '🔥'
        await message.reply(
            box("Auto Reactions ⚡", [
                row("Status", bold(status_icon(enabled) + " " + (sc("On") if enabled else sc("Off"))), "⚡"),
                row("Emoji", bold(emoji), "🎯"),
                sep(),
                row("Toggle", "/react on | off", "📖"),
                row("Emoji", "/setreact &lt;emoji&gt; | random", "🎲"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    on = args[1].lower() == "on"
    await update_setting(message.chat.id, 'legacy_react_enabled', on)
    state = f"✅ {sc('Enabled')}" if on else f"❌ {sc('Disabled')}"
    await message.reply(
        box("Auto Reactions ⚡", [
            f"  ⚡ {sc('Auto reactions')} — {bold(state)}",
            sep(),
            quote(sc("I will react to every message with a big animation.") if on
                  else sc("Auto reactions turned off.")),
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("setreact"), AllowedFilter(), _GRP)
async def set_react_cmd(message: Message, bot: Bot):
    core_db.inc_stat("commands")
    args = message.text.split(None, 1)

    if len(args) < 2:
        await message.reply(
            box("Set Reaction Emoji 🎯", [
                row("Usage", "/setreact &lt;emoji&gt;", "📖"),
                row("Example", "/setreact 🔥", "🎯"),
                row("Random", "/setreact random", "🎲"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    emoji = args[1].strip()
    await update_setting(message.chat.id, 'legacy_react_emoji', emoji)

    if emoji.lower() == "random":
        await message.reply(
            box("Reaction Emoji Set 🎲", [
                f"  🎲 {sc('Will pick a random emoji each time')}",
                sep(),
                quote(sc("Randomised reactions enabled.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
    else:
        pick = emoji.split()[0]
        await message.reply(
            box("Reaction Emoji Set ✅", [
                f"  {sc('Emoji')} — {bold(pick)}",
                sep(),
                quote(sc("Saved successfully.")),
            ]),
            parse_mode=ParseMode.HTML,
        )
        await _set_reaction(bot, message.chat.id, message.message_id, pick)


@router.message(_GRP, ~F.text.startswith("/"))
async def auto_react_group(message: Message, bot: Bot):
    if not message.from_user or message.from_user.is_bot:
        return
    settings = await get_settings(message.chat.id)
    # Modern engine takes priority.
    if settings.get('reaction_enabled'):
        return
    if not settings.get('legacy_react_enabled'):
        return
    stored = settings.get('legacy_react_emoji') or '🔥'
    emoji = _pick_emoji(stored)
    await _set_reaction(bot, message.chat.id, message.message_id, emoji)


@router.channel_post()
async def auto_react_channel(message: Message, bot: Bot):
    settings = await get_settings(message.chat.id)
    # Modern engine takes priority.
    if settings.get('reaction_enabled'):
        return
    if not settings.get('legacy_react_enabled'):
        return
    stored = settings.get('legacy_react_emoji') or '🔥'
    emoji = _pick_emoji(stored)
    await _set_reaction(bot, message.chat.id, message.message_id, emoji)
