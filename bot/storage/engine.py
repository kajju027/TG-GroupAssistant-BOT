from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from bot.core.config import CHATS_DIR

log = logging.getLogger('group_assistant_bot.storage')

_DEFAULT_SETTINGS: dict[str, Any] = {'chat_title': '', 'chat_type': '', 'antilink': False, 'antilink_action': 'delete', 'antilink_whitelist': [], 'antiword': False, 'antiword_action': 'delete', 'antiword_words': [], 'antispam': False, 'antispam_limit': 5, 'antispam_window': 10, 'antifake': False, 'antifake_mode': 'blacklist', 'antifake_prefixes': [], 'antitag': False, 'welcome': True, 'welcome_msg': '🌟 <b>Welcome, {mention}!</b>\n\n🎉 You just joined <b>{group}</b>.\n\n💫 You are member <b>#{count}</b> — feel at home!', 'goodbye': True, 'goodbye_msg': '👋 <b>Goodbye, {mention}!</b>\n\n💔 You left <b>{group}</b>.\n\n😢 We now have <b>{count}</b> members. Take care!', 'warn_limit': 3, 'warn_action': 'kick', 'mute_on_join': False, 'reaction_enabled': False, 'reaction_emojis': ['👍'], 'reaction_mode': 'automatic', 'filters': {}, 'warnings': {}, 'spam_tracker': {}, 'muted_users': {}, 'admins_cache': [], 'bot_is_admin': False, 'members': {}}

T = TypeVar('T')

_locks: dict[int, asyncio.Lock] = {}
_lock_guard = asyncio.Lock()

# In-memory mirror of every chat file. It is the working copy used by all
# read/write calls, so features keep working even when the filesystem is
# read-only or gets wiped between restarts (common on free hosting platforms).
_memory: dict[int, dict[str, Any]] = {}
_index_memory: dict[str, Any] | None = None

# None = not checked yet, True = disk writes work, False = disk is read-only.
_disk_ok: bool | None = None
_disk_warned = False
_last_retry = 0.0
_RETRY_DISK_EVERY = 300.0


async def _get_lock(chat_id: int) -> asyncio.Lock:
    async with _lock_guard:
        return _locks.setdefault(chat_id, asyncio.Lock())


def _chat_path(chat_id: int) -> Path:
    return CHATS_DIR / f'{chat_id}.json'


def _index_path() -> Path:
    return CHATS_DIR / '_index.json'


def _ensure_dirs() -> None:
    try:
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _read_json(path: Path, default: T) -> T:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        with path.open('r', encoding='utf-8') as file:
            loaded = json.load(file)
        return loaded if isinstance(loaded, type(default)) else copy.deepcopy(default)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(default)


def _write_json_atomic(path: Path, data: Any) -> bool:
    """Try to persist to disk. Returns False when the disk refuses writes.

    A read-only or ephemeral filesystem must never break the bot: the caller
    keeps the data in memory and the bot keeps working for the whole session.
    """
    global _disk_ok, _disk_warned, _last_retry
    now = time.monotonic()
    if _disk_ok is False and now - _last_retry < _RETRY_DISK_EVERY:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + '.tmp')
        with temp_path.open('w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
        if _disk_ok is not True:
            _disk_ok = True
            if _disk_warned:
                log.info('Disk storage recovered — settings are being saved to disk again.')
        return True
    except OSError as error:
        _disk_ok = False
        _last_retry = now
        if not _disk_warned:
            _disk_warned = True
            log.warning(
                'Cannot write settings to %s (%s). Falling back to in-memory storage: '
                'the bot keeps working, but settings reset when it restarts. '
                'Mount a persistent volume on this path to keep them.',
                path.parent, type(error).__name__,
            )
        return False


def _normalise_chat(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(_DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)
    return merged


async def init_storage() -> None:
    _ensure_dirs()
    if not _index_path().exists():
        _write_json_atomic(_index_path(), {'chats': {}})


async def load_chat(chat_id: int) -> dict[str, Any]:
    lock = await _get_lock(chat_id)
    async with lock:
        cached = _memory.get(chat_id)
        if cached is None:
            cached = _normalise_chat(_read_json(_chat_path(chat_id), {}))
            _memory[chat_id] = cached
            _write_json_atomic(_chat_path(chat_id), cached)
        return copy.deepcopy(cached)


async def mutate_chat(chat_id: int, mutator: Callable[[dict[str, Any]], T]) -> T:
    lock = await _get_lock(chat_id)
    async with lock:
        cached = _memory.get(chat_id)
        if cached is None:
            cached = _normalise_chat(_read_json(_chat_path(chat_id), {}))
            _memory[chat_id] = cached
        result = mutator(cached)
        _write_json_atomic(_chat_path(chat_id), cached)
        return result


async def save_chat(chat_id: int, data: dict[str, Any]) -> None:
    await mutate_chat(chat_id, lambda current: current.update(data) or None)


async def update_chat(chat_id: int, **kwargs: Any) -> dict[str, Any]:

    def apply(data: dict[str, Any]) -> dict[str, Any]:
        data.update(kwargs)
        return copy.deepcopy(data)
    return await mutate_chat(chat_id, apply)


def _load_index() -> dict[str, Any]:
    global _index_memory
    if _index_memory is None:
        loaded = _read_json(_index_path(), {'chats': {}})
        _index_memory = loaded if isinstance(loaded, dict) else {'chats': {}}
        _index_memory.setdefault('chats', {})
    return _index_memory


async def update_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list[int]) -> None:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        index.setdefault('chats', {})[str(chat_id)] = {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'admin_user_ids': sorted(set(admin_user_ids))}
        _write_json_atomic(_index_path(), index)


async def remove_from_index(chat_id: int) -> None:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        index.get('chats', {}).pop(str(chat_id), None)
        _write_json_atomic(_index_path(), index)
    _memory.pop(chat_id, None)


async def get_managed_chats_for_user(user_id: int) -> list[dict[str, Any]]:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
    result: list[dict[str, Any]] = []
    for chat_id_text, info in index.get('chats', {}).items():
        if info.get('bot_is_admin') and user_id in info.get('admin_user_ids', []):
            result.append({'chat_id': int(chat_id_text), 'title': info.get('title') or 'Untitled', 'type': info.get('type') or 'group'})
    return sorted(result, key=lambda item: item['title'].casefold())


async def note_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool) -> None:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        chats = index.setdefault('chats', {})
        entry = chats.setdefault(str(chat_id), {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'admin_user_ids': []})
        entry['title'] = chat_title or entry.get('title', '')
        entry['type'] = chat_type or entry.get('type', '')
        entry['bot_is_admin'] = bot_is_admin
        admins = set(entry.get('admin_user_ids', []))
        if is_admin:
            admins.add(user_id)
        else:
            admins.discard(user_id)
        entry['admin_user_ids'] = sorted(admins)
        _write_json_atomic(_index_path(), index)
