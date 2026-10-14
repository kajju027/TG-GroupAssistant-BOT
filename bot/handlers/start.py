from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.core.config import OWNER_ID
from bot.core import database as db
from bot.utils.ui import sc, box, row, sep, bold, link, kb, btn, ubtn, status_icon
from bot.utils.filters import NotBlockedFilter

router = Router()

_HELP_OWNER = box("Owner Panel", [
    row("Allow User",   "/allow &lt;id/@user&gt;",  "👤"),
    row("Disallow",     "/disallow &lt;id/@user&gt;", "🚫"),
    row("Block",        "/block &lt;id/@user&gt;",  "🔒"),
    row("Unblock",      "/unblock &lt;id/@user&gt;","🔓"),
    row("Users List",   "/users",                   "📋"),
    row("Broadcast",    "/broadcast &lt;text&gt;",  "📢"),
    row("Stats",        "/stats",                   "📊"),
])

_HELP_GROUP = box("Group Management", [
    row("Ban",          "/ban [reason]",    "🔨"),
    row("Unban",        "/unban",           "✅"),
    row("Kick",         "/kick",            "👢"),
    row("Mute",         "/mute [min]",      "🔇"),
    row("Unmute",       "/unmute",          "🔊"),
    row("Warn",         "/warn [reason]",   "⚠️"),
    row("Warns",        "/warns",           "📋"),
    row("Reset Warns",  "/resetwarns",      "🔄"),
    row("Pin",          "/pin",             "📌"),
    row("Unpin",        "/unpin",           "📍"),
])

_HELP_FEATURES = box("Bot Features", [
    row("Set Welcome",  "/setwelcome &lt;text&gt;",  "👋"),
    row("Welcome",      "/welcome on | off",          "🔔"),
    row("Auto React",   "/react on | off",            "⚡"),
    row("Set Emoji",    "/setreact &lt;emoji&gt;",    "🎯"),
    row("Play Music",   "/play &lt;song/url&gt;",     "🎵"),
])


@router.message(CommandStart(), NotBlockedFilter())
async def cmd_start(message: Message):
    db.inc_stat("commands")
    uid = message.from_user.id
    name = message.from_user.full_name

    if uid == OWNER_ID:
        text = box("Group Assistant Bot", [
            f"  👑 {bold(sc('Owner'))} — {link(name, uid)}",
            sep(),
            f"  ⚡ {sc('All systems online')}",
            f"  🔥 {sc('Full access granted')}",
            sep(),
            f"  {sc('Use /help to see all commands')}",
        ])
        markup = kb([btn("📋 Help", "help_owner"), btn("📊 Stats", "show_stats")])
    elif db.is_allowed(uid):
        text = box("Group Assistant Bot", [
            f"  ✅ {bold(sc('Access Granted'))} — {link(name, uid)}",
            sep(),
            f"  {sc('Welcome back! You have access to use this bot.')}",
            sep(),
            f"  {sc('Use /help to see available commands')}",
        ])
        markup = kb([btn("📋 Help", "help_user")])
    else:
        text = box("Private Bot", [
            f"  🔒 {bold(sc('Access Denied'))}",
            sep(),
            f"  {sc('This is a private bot.')}",
            f"  {sc('Contact the owner for access.')}",
        ])
        markup = None

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=markup)


@router.message(Command("help"), NotBlockedFilter())
async def cmd_help(message: Message):
    db.inc_stat("commands")
    uid = message.from_user.id

    if uid == OWNER_ID:
        await message.answer(_HELP_OWNER, parse_mode=ParseMode.HTML)
        await message.answer(_HELP_GROUP, parse_mode=ParseMode.HTML)
        await message.answer(_HELP_FEATURES, parse_mode=ParseMode.HTML)
    elif db.is_allowed(uid):
        await message.answer(_HELP_GROUP, parse_mode=ParseMode.HTML)
        await message.answer(_HELP_FEATURES, parse_mode=ParseMode.HTML)
    else:
        await message.answer(
            box("Access Denied", [
                f"  🔒 {sc('This is a private bot.')}",
                f"  {sc('You do not have access.')}",
            ]),
            parse_mode=ParseMode.HTML,
        )
