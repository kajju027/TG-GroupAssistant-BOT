from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_settings, update_setting, get_banned_words, add_banned_word, remove_banned_word
from bot.utils.helpers import is_admin

router = Router()

@router.message(Command("antiword"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_antiword(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer("❌ Admins only.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        s = await get_settings(message.chat.id)
        status = "✅ ON" if s["antiword"] else "❌ OFF"
        words = await get_banned_words(message.chat.id)
        await message.answer(
            f"🔤 <b>Anti-Word:</b> {status}\n"
            f"Action: <b>{s['antiword_action'].upper()}</b>\n"
            f"Words: {', '.join(words) if words else 'None'}\n\n"
            "Usage: /antiword on|off|add|remove|list|action [word]"
        )
        return
    cmd = parts[1].lower()
    if cmd == "on":
        await update_setting(message.chat.id, "antiword", 1)
        await message.answer("✅ Anti-word <b>enabled</b>.")
    elif cmd == "off":
        await update_setting(message.chat.id, "antiword", 0)
        await message.answer("❌ Anti-word <b>disabled</b>.")
    elif cmd == "add" and len(parts) > 2:
        word = parts[2].strip().lower()
        await add_banned_word(message.chat.id, word)
        await message.answer(f"✅ Added banned word: <code>{word}</code>")
    elif cmd == "remove" and len(parts) > 2:
        word = parts[2].strip().lower()
        await remove_banned_word(message.chat.id, word)
        await message.answer(f"✅ Removed banned word: <code>{word}</code>")
    elif cmd == "list":
        words = await get_banned_words(message.chat.id)
        if words:
            await message.answer("🔤 <b>Banned words:</b>\n" + "\n".join(f"• <code>{w}</code>" for w in words))
        else:
            await message.answer("No banned words set.")
    elif cmd == "action" and len(parts) > 2:
        action = parts[2].lower()
        if action not in ("delete", "warn", "kick", "ban"):
            await message.answer("❌ Valid actions: delete, warn, kick, ban")
            return
        await update_setting(message.chat.id, "antiword_action", action)
        await message.answer(f"✅ Anti-word action set to <b>{action.upper()}</b>.")
    else:
        await message.answer("Usage: /antiword on|off|add [word]|remove [word]|list|action [delete/warn/kick/ban]")


# Registered AFTER the command handler above and explicitly excludes
# text starting with "/" so it never swallows commands meant for
# other routers (see ordering note in bot.py).
@router.message(F.chat.type.in_({"group", "supergroup"}), F.text, ~F.text.startswith("/"))
async def check_words(message: Message):
    if not message.from_user:
        return
    if await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    s = await get_settings(message.chat.id)
    if not s["antiword"]:
        return
    banned = await get_banned_words(message.chat.id)
    if not banned:
        return
    text_lower = (message.text or "").lower()
    for word in banned:
        if word in text_lower:
            try:
                await message.delete()
            except Exception:
                pass
            action = s["antiword_action"]
            name = message.from_user.full_name
            uid = message.from_user.id
            if action == "warn":
                from bot.database import add_warning
                count = await add_warning(message.chat.id, uid, f"Used banned word: {word}")
                if count >= s["warn_limit"]:
                    await message.answer(f"⚠️ {message.from_user.mention_html()} kicked for exceeding warn limit.")
                    try:
                        await message.bot.ban_chat_member(message.chat.id, uid)
                        await message.bot.unban_chat_member(message.chat.id, uid)
                    except Exception:
                        pass
                else:
                    await message.answer(f"🔤 Banned word removed! ⚠️ <b>{name}</b> warned ({count}/{s['warn_limit']})")
            elif action == "kick":
                await message.answer(f"🚪 <b>{name}</b> kicked for using a banned word.")
                try:
                    await message.bot.ban_chat_member(message.chat.id, uid)
                    await message.bot.unban_chat_member(message.chat.id, uid)
                except Exception:
                    pass
            elif action == "ban":
                await message.answer(f"🔨 <b>{name}</b> banned for using a banned word.")
                try:
                    await message.bot.ban_chat_member(message.chat.id, uid)
                except Exception:
                    pass
            else:
                await message.answer(f"🔤 Message deleted: banned word used by <b>{name}</b>.")
            return
