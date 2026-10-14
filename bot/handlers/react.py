import random
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji
from bot.core import database as db
from bot.utils.filters import AllowedFilter
from bot.utils.ui import sc, box, row, sep, bold, mono, rand_emoji, status_icon

router = Router()

_VALID_EMOJIS = {
    "👍","👎","❤️","🔥","🥰","👏","😁","🤔","🤯","😱","🤬","😢","🎉","🤩",
    "🤮","💩","🙏","👌","🕊","🤡","🥱","🥴","😍","🐳","❤️‍🔥","🌚","🌭","💯",
    "🤣","⚡","🍌","🏆","💔","🤨","😐","🍓","🍾","💋","🖕","😈","😴","😭",
    "🤓","👻","👨‍💻","👀","🎃","🙈","😇","😨","🤝","✍️","🤗","🫡","🎅",
    "🎄","☃️","💅","🤪","🗿","🆒","💘","🙉","🦄","😘","💊","🙊","😎",
    "👾","🤷","🤷‍♂️","🤷‍♀️","😡","🥶","🌴","🤑","🎰","🤙","🦾","🤏","🫶",
    "🔥","✨","🎊","🥳","💫","🌟","💥","👑","⚡","💎","🏅","🌈",
}


async def _react(bot: Bot, chat_id: int, message_id: int, emoji: str):
    try:
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
            is_big=True,
        )
        db.inc_stat("reactions")
    except Exception:
        pass


@router.message(Command("react"), AllowedFilter(), F.chat.type.in_({"group", "supergroup"}))
async def toggle_react_cmd(message: Message):
    db.inc_stat("commands")
    args = message.text.split()
    db.ensure_group(message.chat.id, message.chat.title or "")
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        group = db.get_group(message.chat.id)
        current = status_icon(bool(group and group["react_enabled"])) if group else "❌"
        await message.reply(
            box("Auto Reactions", [
                row("Current", current,                    "⚡"),
                row("Usage",   "/react on | off",          "📖"),
                row("Emoji",   "/setreact &lt;emoji&gt;",  "🎯"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    on = args[1].lower() == "on"
    db.toggle_react(message.chat.id, on)
    state = "✅ Enabled" if on else "❌ Disabled"
    await message.reply(
        box("Auto Reactions", [
            f"  ⚡ {sc('Auto Reactions')} — {bold(state)}",
            sep(),
            f"  {sc('Use /setreact <emoji> to change the emoji')}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("setreact"), AllowedFilter(), F.chat.type.in_({"group", "supergroup"}))
async def set_react_cmd(message: Message, bot: Bot):
    db.inc_stat("commands")
    args = message.text.split(None, 1)
    db.ensure_group(message.chat.id, message.chat.title or "")
    if len(args) < 2:
        await message.reply(
            box("Set Reaction Emoji", [
                row("Usage",    "/setreact &lt;emoji&gt;",        "📖"),
                row("Example",  "/setreact 🔥",                   "🎯"),
                row("Random",   "/setreact random",               "🎲"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    emoji = args[1].strip()
    if emoji.lower() == "random":
        emoji = "random"
        db.set_react_emoji(message.chat.id, emoji)
        await message.reply(
            box("Reaction Emoji Set", [f"  🎲 {sc('Will use a random emoji each time')}"]),
            parse_mode=ParseMode.HTML,
        )
        return
    db.set_react_emoji(message.chat.id, emoji)
    await message.reply(
        box("Reaction Emoji Set", [
            f"  {sc('Reaction emoji')} — {bold(emoji)}",
            sep(),
            f"  ✅ {sc('Saved successfully')}",
        ]),
        parse_mode=ParseMode.HTML,
    )
    await _react(bot, message.chat.id, message.message_id, emoji if emoji != "random" else rand_emoji())


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def auto_react_group(message: Message, bot: Bot):
    if not message.from_user or message.from_user.is_bot:
        return
    group = db.get_group(message.chat.id)
    if not group or not group["react_enabled"]:
        return
    stored = group["react_emoji"] or "🔥"
    emoji = rand_emoji() if stored == "random" else stored
    await _react(bot, message.chat.id, message.message_id, emoji)


@router.channel_post()
async def auto_react_channel(message: Message, bot: Bot):
    db.ensure_group(message.chat.id, message.chat.title or "")
    group = db.get_group(message.chat.id)
    if not group or not group["react_enabled"]:
        return
    stored = group["react_emoji"] or "🔥"
    emoji = rand_emoji() if stored == "random" else stored
    await _react(bot, message.chat.id, message.message_id, emoji)
