from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji
from bot.core import database as db
from bot.utils.filters import AllowedFilter
from bot.utils.ui import sc, box, row, sep, bold, italic, quote, rand_emoji, status_icon

router = Router()

_GRP = F.chat.type.in_({"group", "supergroup"})


async def _set_reaction(bot: Bot, chat_id: int, message_id: int, emoji: str):
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


@router.message(Command("react"), AllowedFilter(), _GRP)
async def toggle_react_cmd(message: Message):
    db.inc_stat("commands")
    args = message.text.split()
    db.ensure_group(message.chat.id, message.chat.title or "")

    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        group   = db.get_group(message.chat.id)
        enabled = bool(group and group["react_enabled"]) if group else False
        emoji   = group["react_emoji"] if group else "🔥"
        await message.reply(
            box("Auto Reactions ⚡", [
                row("Status",  bold(status_icon(enabled) + " " + (sc("On") if enabled else sc("Off"))), "⚡"),
                row("Emoji",   bold(emoji),                                                              "🎯"),
                sep(),
                row("Toggle",  "/react on | off",                "📖"),
                row("Emoji",   "/setreact &lt;emoji&gt; | random", "🎲"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    on = args[1].lower() == "on"
    db.toggle_react(message.chat.id, on)
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
    db.inc_stat("commands")
    args = message.text.split(None, 1)
    db.ensure_group(message.chat.id, message.chat.title or "")

    if len(args) < 2:
        await message.reply(
            box("Set Reaction Emoji 🎯", [
                row("Usage",   "/setreact &lt;emoji&gt;", "📖"),
                row("Example", "/setreact 🔥",            "🎯"),
                row("Random",  "/setreact random",        "🎲"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    emoji = args[1].strip()
    db.set_react_emoji(message.chat.id, emoji)

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
    group = db.get_group(message.chat.id)
    if not group or not group["react_enabled"]:
        return
    stored = group["react_emoji"] or "🔥"
    emoji  = rand_emoji() if stored.lower() == "random" else stored.split()[0]
    await _set_reaction(bot, message.chat.id, message.message_id, emoji)


@router.channel_post()
async def auto_react_channel(message: Message, bot: Bot):
    db.ensure_group(message.chat.id, message.chat.title or "")
    group = db.get_group(message.chat.id)
    if not group or not group["react_enabled"]:
        return
    stored = group["react_emoji"] or "🔥"
    emoji  = rand_emoji() if stored.lower() == "random" else stored.split()[0]
    await _set_reaction(bot, message.chat.id, message.message_id, emoji)
