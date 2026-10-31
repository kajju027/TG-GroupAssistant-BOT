from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import add_warning, get_banned_words, get_settings
from bot.utils.autodelete import answer_and_autodelete
from bot.utils.helpers import get_bot_username, is_admin as check_is_admin, mention_by_name
from bot.utils.ui import box, kb, quote, sc, ubtn

router = Router()

_pattern_cache: dict[str, re.Pattern] = {}


def _compile(word: str) -> re.Pattern:
    pattern = _pattern_cache.get(word)
    if pattern is None:
        pattern = re.compile(r'(?<!\w)' + re.escape(word) + r'(?!\w)', re.IGNORECASE | re.UNICODE)
        _pattern_cache[word] = pattern
    return pattern


def matches_banned_word(words: list[str], text: str) -> str | None:
    lowered = (text or '').casefold()
    for word in words:
        if word and _compile(word.strip().casefold()).search(lowered):
            return word
    return None


@router.message(Command('antiword'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antiword(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    username = await get_bot_username(message.bot)
    markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')]) if username else None
    await message.answer(box('Anti Word 🔤', [quote(sc('Anti-Word settings now live in my private chat — tap below.'))]), reply_markup=markup)


@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text | F.caption)
async def check_words(message: Message):
    if not message.from_user:
        raise SkipHandler
    if message.text and message.text.startswith('/'):
        raise SkipHandler
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        raise SkipHandler
    if message.sender_chat is not None:
        raise SkipHandler
    settings = await get_settings(message.chat.id)
    if not settings.get('antiword'):
        raise SkipHandler
    banned = await get_banned_words(message.chat.id)
    if not banned:
        raise SkipHandler
    text = message.text or message.caption or ''
    word = matches_banned_word(banned, text)
    if not word:
        raise SkipHandler
    user_id = message.from_user.id
    mention = mention_by_name(user_id, message.from_user.full_name)
    try:
        await message.delete()
    except Exception:
        pass
    action = settings.get('antiword_action', 'delete')
    if action == 'warn':
        count = await add_warning(message.chat.id, user_id, f'Used banned word: {word}')
        if count >= settings.get('warn_limit', 3):
            await answer_and_autodelete(message, f'⚠️ {mention} {sc("kicked — warn limit reached.")}')
            try:
                await message.bot.ban_chat_member(message.chat.id, user_id)
                await message.bot.unban_chat_member(message.chat.id, user_id)
            except Exception:
                pass
        else:
            await answer_and_autodelete(message, f"🔤 {sc('Banned word removed.')}\n⚠️ {mention} {sc('warned')} ({count}/{settings.get('warn_limit', 3)})")
    elif action == 'kick':
        await answer_and_autodelete(message, f'🚪 {mention} {sc("was kicked for using a banned word.")}')
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
            await message.bot.unban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    elif action == 'ban':
        await answer_and_autodelete(message, f'🔨 {mention} {sc("was banned for using a banned word.")}')
        try:
            await message.bot.ban_chat_member(message.chat.id, user_id)
        except Exception:
            pass
    else:
        await answer_and_autodelete(message, f"🔤 {sc('Message deleted')} — {mention}.")
