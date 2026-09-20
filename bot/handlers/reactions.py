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
log = get_logger('REACTIONS')
_MIN_DELAY = 3
_MAX_DELAY = 7
_ALLOWED_EMOJI = {'👍', '👎', '❤', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱', '🎉', '🤩', '😢', '😡', '🤝', '🙏', '👌', '🕊', '🤡', '🥱', '🥴', '😍', '🐳', '❤\u200d🔥', '🌚', '🌭', '💯', '🤣', '⚡', '🍌', '🏆', '💔', '🤨', '😐', '🍓', '🍾', '💋', '🖕', '😈', '😴', '😭', '🤓', '👻', '👨\u200d💻', '👀', '🎃', '🙈', '😇', '😨', '✍', '🤗', '🫡', '🎅', '🎄', '☃', '💅', '🤪', '🗿', '🆒', '💘', '🙉', '🦄', '😘', '💊', '🙊', '😎', '👾', '🤷\u200d♂', '🤷', '🤷\u200d♀', '☘️', '🌚'}

async def _is_authorized(message: Message) -> bool:
    if message.chat.type == 'channel':
        return True
    return await is_message_sender_admin(message)

def _status_text(s: dict) -> str:
    status = '✅ ON' if s.get('reaction_enabled') else '❌ OFF'
    emojis = s.get('reaction_emojis') or ['👍']
    return f"🎭 <b>Auto-Reaction Settings</b>\n\n<b>Status:</b> {status}\n<b>Emojis:</b> {' '.join(emojis)}\n\nEvery new post gets one of these emojis a few seconds after it arrives. With more than one emoji set, each new post cycles to the next one in order.\n\n<b>Usage:</b>\n/reaction on — enable\n/reaction off — disable\n/reaction emoji [emoji1 emoji2 ...] — set one or more emojis\n\nWorks in both groups and channels."

async def _handle_reaction_command(message: Message):
    if not await _is_authorized(message):
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = (message.text or '').split(maxsplit=2)
    s = await get_settings(message.chat.id)
    if len(parts) < 2:
        await message.answer(_status_text(s))
        return
    cmd = parts[1].lower()
    if cmd == 'on':
        await update_setting(message.chat.id, 'reaction_enabled', True)
        emojis = ' '.join(s.get('reaction_emojis') or ['👍'])
        await message.answer(f'✅ <b>Auto-reaction enabled.</b>\nEmojis: {emojis}')
    elif cmd == 'off':
        await update_setting(message.chat.id, 'reaction_enabled', False)
        await message.answer('❌ <b>Auto-reaction disabled.</b>')
    elif cmd == 'emoji':
        if len(parts) < 3 or not parts[2].strip():
            await message.answer('<b>Usage:</b> /reaction emoji [emoji1 emoji2 ...]\n\n<b>Example:</b> /reaction emoji 🔥 ☘️ 🌚')
            return
        candidates = parts[2].strip().split()
        valid = [e for e in candidates if e in _ALLOWED_EMOJI]
        invalid = [e for e in candidates if e not in _ALLOWED_EMOJI]
        if not valid:
            sample = ' '.join(list(_ALLOWED_EMOJI)[:12])
            await message.answer(f'❌ None of those are supported as Telegram reactions.\nTry some of: {sample} ...')
            return
        await update_setting(message.chat.id, 'reaction_emojis', valid)
        await update_setting(message.chat.id, '_reaction_index', 0)
        msg = f"✅ Reaction emojis set to: {' '.join(valid)}"
        if invalid:
            msg += f"\n⚠️ Skipped unsupported: {' '.join(invalid)}"
        await message.answer(msg)
    else:
        await message.answer(_status_text(s))

@router.message(Command('reaction'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_reaction_group(message: Message):
    await _handle_reaction_command(message)

@router.channel_post(Command('reaction'))
async def cmd_reaction_channel(message: Message):
    await _handle_reaction_command(message)

async def _react_after_delay(message: Message):
    try:
        await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))
        s = await get_settings(message.chat.id)
        if not s.get('reaction_enabled'):
            return
        emojis = s.get('reaction_emojis') or ['👍']
        if len(emojis) == 1:
            emoji = emojis[0]
        else:
            idx = await next_reaction_index(message.chat.id)
            emoji = emojis[idx % len(emojis)]
        await message.bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id, reaction=[ReactionTypeEmoji(emoji=emoji)])
    except TelegramBadRequest as e:
        log.warn(f'Could not react in {message.chat.id}: {e}')
    except Exception as e:
        log.warn(f'Unexpected error reacting in {message.chat.id}: {e}')

@router.message(F.chat.type.in_({'group', 'supergroup'}), ~F.text.startswith('/'))
async def on_new_group_message(message: Message):
    s = await get_settings(message.chat.id)
    if s.get('reaction_enabled'):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler

@router.channel_post(~F.text.startswith('/'))
async def on_new_channel_post(message: Message):
    s = await get_settings(message.chat.id)
    if s.get('reaction_enabled'):
        asyncio.create_task(_react_after_delay(message))
    raise SkipHandler
