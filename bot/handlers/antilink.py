import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_settings, update_setting, add_whitelist_link, remove_whitelist_link, get_whitelisted_links
from bot.utils.helpers import is_admin as check_is_admin, get_user_from_message

router = Router()

LINK_RE = re.compile(
    r"(https?://[^\s]+|t\.me/[^\s]+|telegram\.me/[^\s]+)",
    re.IGNORECASE
)

async def _apply_action(message: Message, action: str):
    uid = message.from_user.id
    name = message.from_user.full_name
    try:
        await message.delete()
    except Exception:
        pass
    if action == "warn":
        from bot.database import add_warning, get_settings
        s = await get_settings(message.chat.id)
        count = await add_warning(message.chat.id, uid, "Sent a link")
        if count >= s["warn_limit"]:
            await message.answer(f"⚠️ {message.from_user.mention_html()} has been kicked for exceeding warn limit.")
            try:
                await message.bot.ban_chat_member(message.chat.id, uid)
                await message.bot.unban_chat_member(message.chat.id, uid)
            except Exception:
                pass
        else:
            await message.answer(
                f"🔗 Link removed! ⚠️ <b>{name}</b> warned ({count}/{s['warn_limit']})\nReason: Sent a link"
            )
    elif action == "kick":
        await message.answer(f"🚪 <b>{name}</b> was kicked for sending a link.")
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
            await message.bot.unban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    elif action == "ban":
        await message.answer(f"🔨 <b>{name}</b> was banned for sending a link.")
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    else:
        await message.answer(f"🔗 Link removed from <b>{name}</b>.")

@router.message(Command("antilink"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_antilink(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = "✅ ON" if s["antilink"] else "❌ OFF"
        await message.answer(
            f"🔗 <b>Anti-Link:</b> {status}\n"
            f"Action: <b>{s['antilink_action'].upper()}</b>\n\n"
            "Usage: /antilink on|off|whitelist|unwhitelist [link]"
        )
        return
    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "antilink", 1)
        await message.answer("✅ Anti-link <b>enabled</b>.")
    elif cmd == "off":
        await update_setting(message.chat.id, "antilink", 0)
        await message.answer("❌ Anti-link <b>disabled</b>.")
    elif cmd in ("whitelist", "wl") and len(parts) > 2:
        await add_whitelist_link(message.chat.id, parts[2])
        await message.answer(f"✅ Whitelisted: <code>{parts[2]}</code>")
    elif cmd in ("unwhitelist", "unwl") and len(parts) > 2:
        await remove_whitelist_link(message.chat.id, parts[2])
        await message.answer(f"✅ Removed from whitelist: <code>{parts[2]}</code>")
    elif cmd == "action" and len(parts) > 2:
        action = parts[2].lower()
        if action not in ("delete", "warn", "kick", "ban"):
            await message.answer("❌ Valid actions: delete, warn, kick, ban")
            return
        await update_setting(message.chat.id, "antilink_action", action)
        await message.answer(f"✅ Anti-link action set to <b>{action.upper()}</b>.")
    else:
        await message.answer("Usage: /antilink on|off|action [delete/warn/kick/ban]|whitelist [link]")


# Registered AFTER the command handler above and explicitly excludes
# text that starts with "/" so it never swallows commands meant for
# other routers (this router is included before antiword/antispam/filters
# in bot.py, so this guard is what protects those).
@router.message(F.chat.type.in_({"group", "supergroup"}), F.text, ~F.text.startswith("/"))
async def check_links(message: Message):
    if not message.from_user:
        return
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    s = await get_settings(message.chat.id)
    if not s["antilink"]:
        return
    links = LINK_RE.findall(message.text or "")
    if not links:
        return
    whitelist = await get_whitelisted_links(message.chat.id)
    for link in links:
        if not any(w in link for w in whitelist):
            await _apply_action(message, s["antilink_action"])
            return
