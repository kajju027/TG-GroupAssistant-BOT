import asyncio
from aiogram.exceptions import TelegramBadRequest
AUTO_DELETE_SECONDS = 12 * 60

def schedule_auto_delete(message, delay: int=None):
    if delay is None:
        delay = AUTO_DELETE_SECONDS
    asyncio.create_task(_delete_after(message, delay))

async def _delete_after(message, delay: int):
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except TelegramBadRequest:
        pass
    except Exception:
        pass

async def answer_and_autodelete(message, text: str, delay: int=None, **kwargs):
    if delay is None:
        delay = AUTO_DELETE_SECONDS
    sent = await message.answer(text, **kwargs)
    schedule_auto_delete(sent, delay)
    return sent
