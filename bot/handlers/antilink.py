from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import add_warning, get_settings
from bot.utils.autodelete import answer_and_autodelete
from bot.utils.helpers import (
    is_admin as check_is_admin,
    is_domain_whitelisted,
    mention_by_name,
)
from bot.utils.ui import box, kb, quote, sc, ubtn
from bot.utils.helpers import get_bot_username

router = Router()

LINK_RE = re.compile('(https?://[^\\s]+|www\\.[^\\s]+|t\\.me/[^\\s]+|telegram\\.me/[^\\s]+|telegram\\.dog/[^\\s]+)', re.IGNORECASE)


def collect_links(message: Message) -> list[str]:
    """Links from entities (including hidden text_link URLs), text and caption."""
    links: list[str] = []
    for entity in list(message.entities or []) + list(message.caption_entities or []):
        if entity.type in {MessageEntityType.URL, MessageEntityType.TEXT_LINK}:
            value = getattr(entity, 'url', None) or ''
            offset, length = entity.offset, entity.length
            source = message.text or message.caption or ''
            if not value and source:
                value = source[offset:offset + length]
            if value:
                links.append(value)
    text = message.text or message.caption or ''
    links.extend(LINK_RE.findall(text))
    # bare @usernames are not links — drop them
    return [link for link in links if not link.startswith('@')]


async def _apply_action(message: Message, action: str):
    uid = message.from_user.id
    mention = mention_by_name(uid, message.from_user.full_name)
    try:
        await message.delete()
    except Exception:
        pass
    if action == 'warn':
        s = await get_settings(message.chat.id)
        count = await add_warning(message.chat.id, uid, 'Sent a link')
        if count >= s['warn_limit']:
            await answer_and_autodelete(message, f'⚠️ {mention} {sc("kicked — warn limit reached.")}')
            try:
                await message.bot.ban_chat_member(message.chat.id, uid)
                await message.bot.unban_chat_member(message.chat.id, uid)
            except Exception:
                pass
        else:
            await answer_and_autodelete(message, f"🔗 {sc('Link removed.')}\n⚠️ {mention} {sc('warned')} ({count}/{s['warn_limit']})")
    elif action == 'kick':
        await answer_and_autodelete(message, f'🚪 {mention} {sc("was kicked for sending a link.")}')
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
            await message.bot.unban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    elif action == 'ban':
        await answer_and_autodelete(message, f'🔨 {mention} {sc("was banned for sending a link.")}')
        try:
            await message.bot.ban_chat_member(message.chat.id, uid)
        except Exception:
            pass
    else:
        await answer_and_autodelete(message, f"🔗 {sc('Link removed')} — {mention}.")


@router.message(Command('antilink'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_antilink(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    username = await get_bot_username(message.bot)
    markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')]) if username else None
    await message.answer(box('Anti Link 🔗', [quote(sc('Anti-Link settings now live in my private chat — tap below.'))]), reply_markup=markup)


@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text | F.caption)
async def check_links(message: Message):
    if not message.from_user:
        raise SkipHandler
    if message.text and message.text.startswith('/'):
        raise SkipHandler
    if await check_is_admin(message.bot, message.chat.id, message.from_user.id):
        raise SkipHandler
    if message.sender_chat is not None:
        raise SkipHandler
    settings = await get_settings(message.chat.id)
    if not settings.get('antilink'):
        raise SkipHandler
    links = collect_links(message)
    if not links:
        raise SkipHandler
    whitelist = settings.get('antilink_whitelist', [])
    for link in links:
        if not is_domain_whitelisted(link, whitelist):
            await _apply_action(message, settings.get('antilink_action', 'delete'))
            return
    raise SkipHandler
