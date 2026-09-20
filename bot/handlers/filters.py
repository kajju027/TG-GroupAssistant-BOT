from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import get_filters, add_filter, remove_filter
router = Router()

@router.message(Command('filter'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_filter(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer('<b>Usage:</b> /filter [keyword] [reply text]\n\n<b>Example:</b> /filter hello Hello there! 👋')
        return
    keyword = parts[1].lower()
    reply = parts[2]
    await add_filter(message.chat.id, keyword, reply)
    await message.answer(f'✅ <b>Filter added.</b>\n<b>Keyword:</b> <code>{keyword}</code>\n<b>Reply:</b> {reply}')

@router.message(Command('filters'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_filters(message: Message):
    filters = await get_filters(message.chat.id)
    if not filters:
        await message.answer('No filters set in this group.')
        return
    text = '🔍 <b>Active Filters</b>\n\n'
    for f in filters:
        preview = f['reply'][:30] + ('...' if len(f['reply']) > 30 else '')
        text += f"• <code>{f['keyword']}</code> → {preview}\n"
    await message.answer(text)

@router.message(Command('stop'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_stop(message: Message, is_admin: bool=False):
    if not is_admin:
        await message.answer('❌ <b>Admins only.</b>')
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer('<b>Usage:</b> /stop [keyword]')
        return
    keyword = parts[1].lower()
    await remove_filter(message.chat.id, keyword)
    await message.answer(f'✅ Filter <code>{keyword}</code> removed.')

@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text, ~F.text.startswith('/'))
async def check_filters(message: Message):
    if not message.text:
        return
    filters = await get_filters(message.chat.id)
    text_lower = message.text.lower()
    for f in filters:
        if f['keyword'] in text_lower:
            await message.answer(f['reply'])
            return
