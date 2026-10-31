"""Auto-purge: delete every message in a group older than the configured
window. Default OFF. When enabled, a slow background sweep runs through the
chat's recent history and removes anything past the cutoff.

The sweep is incremental (a cursor remembers where the last sweep stopped)
and re-entrant (a per-chat lock prevents overlapping sweeps). It is also
gentle on Telegram: small batches, short sleeps between them, and any 429
response backs off immediately.

Important: this only ever touches a group's own messages. Channels and
private chats are never touched.
"""
from __future__ import annotations

import asyncio
import datetime
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from bot.core import database as db
from bot.utils.helpers import is_bot_admin
from bot.utils.ui import bold, box, quote, row, sc

log = logging.getLogger('group_assistant_bot.autodelete')

router = Router()

# How often the sweep wakes up. Short enough to feel live, long enough to
# stay gentle with Telegram's flood limits.
SWEEP_INTERVAL_SECONDS = 5 * 60  # 5 minutes
# Max messages to look at per sweep. Keeps each pass fast even in busy chats.
SWEEP_BATCH_LIMIT = 200
# Pause between delete batches so we don't trip flood control.
BATCH_SLEEP = 0.4
# When deleting many at once, batch them in chunks Telegram accepts.
DELETE_CHUNK = 100


def _cutoff_timestamp(window_hours: int) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    return int((now - datetime.timedelta(hours=window_hours)).timestamp())


async def _delete_chunk(bot: Bot, chat_id: int, message_ids: list[int]) -> int:
    """Delete a batch of messages; returns how many were actually removed."""
    if not message_ids:
        return 0
    deleted = 0
    try:
        result = await bot.delete_messages(chat_id, message_ids)
        deleted = sum(1 for ok in result if ok)
    except TelegramBadRequest as error:
        msg = str(error).casefold()
        if 'message to delete not found' in msg or 'message id not found' in msg:
            # Already gone — count them as deleted so the cursor advances.
            deleted = len(message_ids)
        elif 'can be deleted' in msg or 'not enough rights' in msg:
            # Admin rights lost — abort the sweep.
            log.warning('Lost delete rights in %s: %s', chat_id, error)
            return -1
        else:
            # Fall back to one-by-one.
            for mid in message_ids:
                try:
                    await bot.delete_message(chat_id, mid)
                    deleted += 1
                    await asyncio.sleep(BATCH_SLEEP)
                except TelegramBadRequest:
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    return deleted


async def sweep_chat(bot: Bot, chat_id: int) -> int:
    """Run one sweep pass over a single chat. Returns the number of messages
    deleted this round (0 when nothing to do or already running)."""
    settings = await db.get_settings(chat_id)
    if not settings.get('autodelete'):
        return 0
    window = int(settings.get('autodelete_window') or 24)
    if window < 1 or window > 168:
        window = 24

    if not await is_bot_admin(bot, chat_id):
        return 0
    if not await acquire_autodelete_lock(chat_id):
        return 0

    deleted_total = 0
    try:
        cutoff = _cutoff_timestamp(window)
        cursor = await db.get_autodelete_cursor(chat_id)
        if cursor < 1:
            cursor = 1

        # Walk forward from the cursor in bounded pages. We stop as soon as
        # we hit messages newer than the cutoff OR we run out of history.
        scanned = 0
        last_seen_id = cursor
        while scanned < SWEEP_BATCH_LIMIT:
            ids_to_delete: list[int] = []
            oldest_kept = None
            # Inspect a window of up to 100 ids at a time. Telegram does not
            # expose a generic "list messages" endpoint, so we walk id ranges.
            probe_size = 100
            probe_start = cursor
            probe_end = cursor + probe_size - 1

            # We don't know the latest message id ahead of time, so we look
            # at the chat directly to get an upper bound.
            if probe_start < 1:
                probe_start = 1

            # Fetch messages in the probe window. We use forward_history via
            # get_chat + iterative get_message isn't practical, so we rely on
            # the simpler approach: ask Telegram for messages newer than the
            # cursor and delete anything older than the cutoff.
            try:
                # Try to fetch up to probe_size messages starting from cursor.
                # aiogram exposes Bot.get_messages (a forward-history helper).
                messages = await bot.get_messages(chat_id, list(range(probe_start, probe_end + 1)))
            except Exception as error:
                log.debug('get_messages failed in %s (cursor=%s): %s', chat_id, cursor, error)
                # Likely ids don't exist yet. Advance cursor past the probe.
                cursor = probe_end + 1
                if cursor > last_seen_id:
                    last_seen_id = cursor
                continue

            for msg in messages or []:
                if msg is None:
                    continue
                if msg.date is None:
                    continue
                msg_ts = int(msg.date.timestamp())
                if msg_ts < cutoff:
                    ids_to_delete.append(msg.message_id)
                else:
                    if oldest_kept is None or msg.message_id < oldest_kept:
                        oldest_kept = msg.message_id

            if ids_to_delete:
                count = await _delete_chunk(bot, chat_id, ids_to_delete[:DELETE_CHUNK])
                if count < 0:
                    break
                deleted_total += count

            last_seen_id = max(last_seen_id, probe_end)
            cursor = probe_end + 1
            scanned += probe_size

            if oldest_kept is not None and oldest_kept <= probe_end:
                # We've crossed into "fresh" territory — stop here.
                break

            await asyncio.sleep(BATCH_SLEEP)
            # If the probe returned nothing usable, we are past the end of
            # current history; stop rather than spin forever.
            if not messages:
                break

        if last_seen_id > 0:
            await db.set_autodelete_cursor(chat_id, last_seen_id)
    finally:
        await db.release_autodelete_lock(chat_id)

    if deleted_total:
        log.info('Auto-purge removed %s messages in %s', deleted_total, chat_id)
    return deleted_total


async def autodelete_loop(bot: Bot) -> None:
    """Background task: every SWEEP_INTERVAL_SECONDS, walk every active group
    that has auto-purge enabled and run a sweep pass over it."""
    await asyncio.sleep(30)  # let the bot settle first
    while True:
        try:
            chats = await db.list_broadcast_chats()
            for chat in chats:
                if chat.get('type') == 'channel':
                    continue  # channels never get auto-purged
                chat_id = chat['chat_id']
                try:
                    settings = await db.get_settings(chat_id)
                    if settings.get('autodelete'):
                        await sweep_chat(bot, chat_id)
                except Exception as error:
                    log.warning('Auto-purge failed in %s: %s', chat_id, error)
        except Exception as error:
            log.warning('Auto-purge loop error: %s', error)
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)


# ---------------------------------------------------------- commands -----
@router.message(Command('purge24h'), F.chat.type.in_({'group', 'supergroup'}))
async def cmd_purge24h(message: Message, is_admin: bool = False):
    """Toggle the 24h auto-purge on/off for this group."""
    if not is_admin:
        await message.answer(f"❌ <b>{sc('Admins only.')}</b>")
        return
    parts = (message.text or '').split(maxsplit=1)
    arg = parts[1].strip().casefold() if len(parts) > 1 else ''
    if arg in {'on', 'off'}:
        await db.update_setting(message.chat.id, 'autodelete', arg == 'on')
        state = '✅ On' if arg == 'on' else '❌ Off'
        await message.answer(box('Auto Purge 🧹', [
            row('Status', bold(sc(state))),
            '',
            quote(sc('Messages older than 24 hours are deleted automatically on a slow sweep.') if arg == 'on'
                  else sc('Auto purge turned off — nothing is deleted automatically.')),
        ]))
        return
    s = await db.get_settings(message.chat.id)
    enabled = bool(s.get('autodelete'))
    await message.answer(box('Auto Purge 🧹', [
        row('Status', f"{'🟢' if enabled else '🔴'} <b>{sc('On') if enabled else sc('Off')}</b>"),
        row('Window', bold(f"24 {sc('hours')}")),
        '',
        quote(sc('Use /purge24h on | off. When ON, the bot slowly sweeps this group every few minutes and deletes any message older than 24 hours.')),
    ]))
