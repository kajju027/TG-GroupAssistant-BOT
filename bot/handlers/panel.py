from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.core.config import OWNER_ID, SUDO_IDS
from bot.database import list_managed_chats
from bot.handlers.chat_tracker import refresh_chat_index
from bot.utils.helpers import get_bot_username, is_admin, safe_edit
from bot.utils.ui import box, btn, kb, quote, row, sc, ubtn

router = Router()

PAGE_SIZE = 8


def _is_privileged(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_IDS


async def can_manage(obj, chat_id: int, user_id: int) -> bool:
    """Owner/sudo can open any chat panel; everyone else must be an admin
    of that exact chat (checked live)."""
    if _is_privileged(user_id):
        return True
    return await is_admin(obj.bot, chat_id, user_id)


def _empty_text() -> str:
    return box('My Chats ⚙️', [
        quote(sc('No chats yet. Add me as an admin to a group or channel, then tap Refresh.')),
    ])


def _list_text(chats: list) -> str:
    groups = [c for c in chats if c.get('type') != 'channel']
    channels = [c for c in chats if c.get('type') == 'channel']
    missing = [c for c in chats if not c.get('bot_in_chat', True)]
    lines = [
        row('Groups', f"👥 <b>{len(groups)}</b>"),
        row('Channels', f"📢 <b>{len(channels)}</b>"),
    ]
    if missing:
        lines.append(row('Needs Re-Add', f"⚠️ <b>{len(missing)}</b>"))
    lines += [
        '',
        quote(sc('Pick a chat to configure. Everything is managed right here — you never have to open the group or channel.')),
    ]
    return box('My Chats ⚙️', lines)


def _list_kb(chats: list, page: int) -> object:
    total_pages = max(1, (len(chats) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = chats[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    rows = []
    for chat in chunk:
        icon = '📢' if chat.get('type') == 'channel' else '👥'
        status = '' if chat.get('bot_in_chat', True) else ' ⚠️'
        title = (chat['title'] or 'Untitled')[:30]
        rows.append([btn(f'{icon} {title}{status}', f"panel:open:{chat['chat_id']}")])
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(btn('⬅️', f'panel:pg:{page - 1}'))
        nav.append(btn(f'📃 {page + 1}/{total_pages}', 'panel:list'))
        if page < total_pages - 1:
            nav.append(btn('➡️', f'panel:pg:{page + 1}'))
        rows.append(nav)
    rows.append([btn('🔄 Refresh', 'panel:list:refresh'), btn('🏠 Home', 'menu:start')])
    return kb(*rows)


async def _show_list(message: Message, user_id: int, page: int = 0, *, edit: bool = False) -> None:
    chats = await list_managed_chats(user_id, owner=_is_privileged(user_id))
    if not chats:
        text, markup = _empty_text(), kb([btn('🔄 Refresh', 'panel:list:refresh'), btn('🏠 Home', 'menu:start')])
    else:
        text, markup = _list_text(chats), _list_kb(chats, page)
    if edit:
        if await safe_edit(message, text, markup):
            return
    await message.answer(text, reply_markup=markup)


# --------------------------------------------------------------- commands --
@router.message(Command('settings', 'chats'), F.chat.type == 'private')
async def cmd_settings_private(message: Message, state: FSMContext):
    await state.clear()
    await _show_list(message, message.from_user.id)


@router.message(Command('settings'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_settings_group(message: Message, is_admin: bool = False):
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Only group admins can open settings.')}</b>")
        return
    await refresh_chat_index(message.bot, message.chat.id, message.chat.title or 'Untitled', message.chat.type, force=True)
    username = await get_bot_username(message.bot)
    markup = kb([ubtn('⚙️ Open In Private', f'https://t.me/{username}?start=cfg{message.chat.id}')]) if username else None
    await message.answer(box('Settings ⚙️', [
        quote(sc('All settings for this chat are managed in my private chat — tap below. Nothing is configured inside the group.')),
    ]), reply_markup=markup)


# -------------------------------------------------------------- callbacks --
@router.callback_query(F.data == 'panel:list')
async def panel_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if callback.message is None:
        return
    await _show_list(callback.message, callback.from_user.id, edit=True)


@router.callback_query(F.data == 'panel:list:refresh')
async def panel_list_refresh(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer('🔄')
    if callback.message is None:
        return
    await _show_list(callback.message, callback.from_user.id, edit=True)


@router.callback_query(F.data.startswith('panel:pg:'))
async def panel_page(callback: CallbackQuery):
    try:
        page = int(callback.data.rsplit(':', 1)[1])
    except (AttributeError, ValueError):
        await callback.answer('Invalid page.', show_alert=True)
        return
    await callback.answer()
    if callback.message is None:
        return
    await _show_list(callback.message, callback.from_user.id, page, edit=True)


@router.callback_query(F.data.startswith('panel:open:'))
async def panel_open(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        chat_id = int(callback.data.rsplit(':', 1)[1])
    except (AttributeError, ValueError):
        await callback.answer('Invalid settings request.', show_alert=True)
        return
    if not await can_manage(callback, chat_id, callback.from_user.id):
        await callback.answer('You are not an admin in that chat.', show_alert=True)
        return
    await callback.answer()
    from bot.handlers.settings import render_chat_panel

    if callback.message is not None:
        text, markup = await render_chat_panel(chat_id)
        if not await safe_edit(callback.message, text, markup):
            await callback.message.answer(text, reply_markup=markup)


async def open_chat_panel_message(message: Message, chat_id: int) -> None:
    """Deep-link entry (t.me/bot?start=cfg<id>): jump straight to the panel."""
    if message.from_user is None or not await can_manage(message, chat_id, message.from_user.id):
        await message.answer(f"❌ <b>{sc('You are not an admin in that chat.')}</b>")
        return
    from bot.handlers.settings import render_chat_panel

    text, markup = await render_chat_panel(chat_id)
    await message.answer(text, reply_markup=markup)
