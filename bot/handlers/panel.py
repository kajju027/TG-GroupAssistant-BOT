from __future__ import annotations
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from bot.database import list_managed_chats, sync_chat_index
from bot.utils.helpers import groups_picker_kb, is_admin, settings_main_kb
router = Router()
_GROUP_TYPES = {'group', 'supergroup'}

async def _bot_is_admin(bot, chat_id: int) -> bool:
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    except Exception:
        return False

async def _index_group(message: Message) -> None:
    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
    except Exception:
        admin_ids = []
    bot_is_admin = await _bot_is_admin(message.bot, message.chat.id)
    await sync_chat_index(message.chat.id, message.chat.title or 'Untitled', message.chat.type, bot_is_admin, admin_ids)

async def _show_group_list(message: Message, user_id: int) -> None:
    groups = await list_managed_chats(user_id)
    if not groups:
        await message.answer('⚙️ <b>Settings panel</b>\n\nNo manageable groups are indexed yet. Add me as an admin to a group, then send <code>/settings</code> inside that group once.')
        return
    await message.answer('⚙️ <b>Choose a group to manage</b>', reply_markup=groups_picker_kb(groups))

@router.message(Command('settings'), F.chat.type == 'private')
async def cmd_settings_private(message: Message):
    await _show_group_list(message, message.from_user.id)

@router.message(Command('settings'), F.chat.type.in_(_GROUP_TYPES))
async def cmd_settings_group(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Only group admins can open settings.</b>')
        return
    await _index_group(message)
    if not await _bot_is_admin(message.bot, message.chat.id):
        await message.answer('⚠️ <b>I need administrator rights</b> to enforce moderation settings. Please grant Delete Messages / Restrict Members rights first.')
        return
    await message.answer(f"⚙️ <b>Settings: {message.chat.title or 'this group'}</b>", reply_markup=settings_main_kb(message.chat.id))

@router.callback_query(F.data == 'panel:list')
async def panel_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    groups = await list_managed_chats(callback.from_user.id)
    if not groups:
        await callback.message.edit_text('No manageable groups are indexed yet.')
        return
    await callback.message.edit_text('⚙️ <b>Choose a group to manage</b>', reply_markup=groups_picker_kb(groups))

@router.callback_query(F.data.startswith('panel:open:'))
async def panel_open(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        chat_id = int(callback.data.rsplit(':', 1)[1])
    except (AttributeError, ValueError):
        await callback.answer('Invalid settings request.', show_alert=True)
        return
    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer('You are not an admin in that group.', show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text('⚙️ <b>Group settings</b>', reply_markup=settings_main_kb(chat_id))

@router.callback_query(F.data.startswith('menu:main:'))
async def panel_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        chat_id = int(callback.data.rsplit(':', 1)[1])
    except (AttributeError, ValueError):
        await callback.answer('Invalid settings request.', show_alert=True)
        return
    if not await is_admin(callback.bot, chat_id, callback.from_user.id):
        await callback.answer('You are not an admin in that group.', show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text('⚙️ <b>Group settings</b>', reply_markup=settings_main_kb(chat_id))

@router.callback_query(F.data == 'close')
async def panel_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer('Closed')
    await callback.message.delete()
