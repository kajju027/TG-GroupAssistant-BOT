from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from bot.core.config import OWNER_ID, HEART_FX
from bot.core import database as db
from bot.utils.ui import sc, box, row, sep, bold, italic, link, kb, btn, quote
from bot.utils.filters import NotBlockedFilter

router = Router()

_DL_CMDS = box("Downloads", [
    row("YouTube Audio",  "/play &lt;song/url&gt;",     "🎧"),
    row("YouTube Video",  "/video &lt;query/url&gt;",   "🎬"),
    row("X / Twitter",   "/tw &lt;url&gt;",             "𝕏 "),
    row("Instagram",     "/ig &lt;url&gt;",              "📸"),
    row("Facebook",      "/fb &lt;url&gt;",              "📘"),
    row("TeraBox",       "/tb &lt;url&gt;",              "📦"),
    row("Pinterest",     "/pin &lt;url&gt;",             "📌"),
    sep(),
    f"  💡 {italic(sc('Paste any URL in DM for auto-detect'))}",
])

_GROUP_CMDS = box("Group Management", [
    row("Ban",         "/ban [reason]",          "🔨"),
    row("Unban",       "/unban",                 "✅"),
    row("Kick",        "/kick",                  "👢"),
    row("Mute",        "/mute [minutes]",        "🔇"),
    row("Unmute",      "/unmute",                "🔊"),
    row("Warn",        "/warn [reason]",         "⚠️"),
    row("Warns",       "/warns",                 "📋"),
    row("Reset Warns", "/resetwarns",            "🔄"),
    row("Pin",         "/pin",                   "📌"),
    row("Unpin",       "/unpin",                 "📍"),
    sep(),
    row("Set Welcome", "/setwelcome &lt;text&gt;", "👋"),
    row("Welcome",     "/welcome on | off",        "🔔"),
    row("Auto React",  "/react on | off",          "⚡"),
    row("Set Emoji",   "/setreact &lt;emoji&gt;",  "🎯"),
])

_OWNER_CMDS = box("Owner Panel", [
    row("Allow User",   "/allow &lt;id/@user&gt;",    "👤"),
    row("Disallow",     "/disallow &lt;id/@user&gt;", "🚫"),
    row("Block",        "/block &lt;id/@user&gt;",    "🔒"),
    row("Unblock",      "/unblock &lt;id/@user&gt;",  "🔓"),
    row("Users List",   "/users",                     "📋"),
    row("Broadcast",    "/broadcast &lt;text&gt;",    "📢"),
    row("Stats",        "/stats",                     "📊"),
])


@router.message(CommandStart(), NotBlockedFilter())
async def cmd_start(message: Message):
    db.inc_stat("commands")
    uid  = message.from_user.id
    name = message.from_user.full_name

    if uid == OWNER_ID:
        text = box("Group Assistant Bot", [
            f"  👑 {bold(sc('Owner'))} — {link(name, uid)}",
            sep(),
            quote(sc("All systems nominal. Full access granted.")),
            sep(),
            f"  {sc('Use /help to view all commands')}",
        ])
        markup = kb(
            [btn("📋 Commands", "help_cmds"), btn("📊 Stats", "show_stats")],
        )
    elif db.is_allowed(uid):
        text = box("Group Assistant Bot", [
            f"  ✅ {bold(sc('Access Granted'))} — {link(name, uid)}",
            sep(),
            quote(sc("Welcome! You have access to this bot.")),
            sep(),
            f"  {sc('Use /help to view available commands')}",
        ])
        markup = kb([btn("📋 Commands", "help_cmds")])
    else:
        text = box("Private Bot", [
            f"  🔒 {bold(sc('Access Denied'))}",
            sep(),
            quote(sc("This is a private bot. Contact the owner for access.")),
        ])
        markup = None

    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
        message_effect_id=HEART_FX if uid == OWNER_ID else None,
    )


@router.callback_query(lambda c: c.data in ("help_cmds", "show_stats"))
async def cb_help(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    if callback.data == "show_stats":
        groups  = db.all_groups()
        allowed = db.get_allowed()
        await callback.message.answer(
            box("Bot Statistics", [
                row("Allowed Users",  bold(str(len(allowed))),               "👤"),
                row("Groups Active",  bold(str(len(groups))),                "👥"),
                row("Messages",       bold(str(db.get_stat("messages"))),    "💬"),
                row("Reactions",      bold(str(db.get_stat("reactions"))),   "⚡"),
                row("Downloads",      bold(str(db.get_stat("downloads"))),   "⬇️"),
                row("Commands Used",  bold(str(db.get_stat("commands"))),    "📊"),
            ]),
            parse_mode=ParseMode.HTML,
        )
    else:
        if uid == OWNER_ID:
            await callback.message.answer(_OWNER_CMDS, parse_mode=ParseMode.HTML)
        await callback.message.answer(_GROUP_CMDS, parse_mode=ParseMode.HTML)
        await callback.message.answer(_DL_CMDS, parse_mode=ParseMode.HTML)


@router.message(Command("help"), NotBlockedFilter())
async def cmd_help(message: Message):
    db.inc_stat("commands")
    uid = message.from_user.id
    if uid == OWNER_ID:
        await message.answer(_OWNER_CMDS, parse_mode=ParseMode.HTML)
    if uid == OWNER_ID or db.is_allowed(uid):
        await message.answer(_GROUP_CMDS, parse_mode=ParseMode.HTML)
        await message.answer(_DL_CMDS, parse_mode=ParseMode.HTML)
    else:
        await message.answer(
            box("Access Denied", [
                f"  🔒 {sc('Private bot — no public access')}",
            ]),
            parse_mode=ParseMode.HTML,
        )
