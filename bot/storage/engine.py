from __future__ import annotations
import asyncio
import copy
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar
from bot.core.config import CHATS_DIR
_DEFAULT_SETTINGS: dict[str, Any] = {'chat_title': '', 'chat_type': '', 'antilink': False, 'antilink_action': 'delete', 'antilink_whitelist': [], 'antiword': False, 'antiword_action': 'delete', 'antiword_words': [], 'antispam': False, 'antispam_limit': 5, 'antispam_window': 10, 'antifake': False, 'antifake_mode': 'blacklist', 'antifake_prefixes': [], 'welcome': True, 'welcome_msg': 'Welcome {mention} to {group}!', 'goodbye': True, 'goodbye_msg': 'Goodbye {mention}, we will miss you!', 'warn_limit': 3, 'warn_action': 'kick', 'mute_on_join': False, 'reaction_enabled': False, 'reaction_emojis': ['👍'], 'reaction_mode': 'automatic', 'filters': {}, 'warnings': {}, 'spam_tracker': {}, 'muted_users': {}, 'admins_cache': [], 'bot_is_admin': False}
_locks: dict[int, asyncio.Lock] = {}
_lock_guard = asyncio.Lock()
T = TypeVar('T')

async def _get_lock(chat_id: int) -> asyncio.Lock:
    async with _lock_guard:
        return _locks.setdefault(chat_id, asyncio.Lock())

def _chat_path(chat_id: int) -> Path:
    return CHATS_DIR / f'{chat_id}.json'

def _index_path() -> Path:
    return CHATS_DIR / '_index.json'

def _ensure_dirs() -> None:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)

def _read_json(path: Path, default: T) -> T:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        with path.open('r', encoding='utf-8') as file:
            loaded = json.load(file)
        return loaded if isinstance(loaded, type(default)) else copy.deepcopy(default)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(default)

def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + '.tmp')
    with temp_path.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp_path, path)

def _normalise_chat(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(_DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)
    return merged

async def init_storage() -> None:
    _ensure_dirs()
    index_path = _index_path()
    if not index_path.exists():
        _write_json_atomic(index_path, {'chats': {}})

async def load_chat(chat_id: int) -> dict[str, Any]:
    lock = await _get_lock(chat_id)
    async with lock:
        path = _chat_path(chat_id)
        existed = path.exists()
        data = _normalise_chat(_read_json(path, {}))
        if not existed:
            _write_json_atomic(path, data)
        return copy.deepcopy(data)

async def mutate_chat(chat_id: int, mutator: Callable[[dict[str, Any]], T]) -> T:
    lock = await _get_lock(chat_id)
    async with lock:
        path = _chat_path(chat_id)
        data = _normalise_chat(_read_json(path, {}))
        result = mutator(data)
        _write_json_atomic(path, data)
        return result

async def save_chat(chat_id: int, data: dict[str, Any]) -> None:
    lock = await _get_lock(chat_id)
    async with lock:
        _write_json_atomic(_chat_path(chat_id), _normalise_chat(data))

async def update_chat(chat_id: int, **kwargs: Any) -> dict[str, Any]:

    def apply(data: dict[str, Any]) -> dict[str, Any]:
        data.update(kwargs)
        return copy.deepcopy(data)
    return await mutate_chat(chat_id, apply)

async def update_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list[int]) -> None:
    lock = await _get_lock(-1)
    async with lock:
        path = _index_path()
        index = _read_json(path, {'chats': {}})
        index.setdefault('chats', {})[str(chat_id)] = {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'admin_user_ids': sorted(set(admin_user_ids))}
        _write_json_atomic(path, index)

async def remove_from_index(chat_id: int) -> None:
    lock = await _get_lock(-1)
    async with lock:
        path = _index_path()
        index = _read_json(path, {'chats': {}})
        index.get('chats', {}).pop(str(chat_id), None)
        _write_json_atomic(path, index)

async def get_managed_chats_for_user(user_id: int) -> list[dict[str, Any]]:
    lock = await _get_lock(-1)
    async with lock:
        index = _read_json(_index_path(), {'chats': {}})
    result: list[dict[str, Any]] = []
    for chat_id_text, info in index.get('chats', {}).items():
        if info.get('bot_is_admin') and user_id in info.get('admin_user_ids', []):
            result.append({'chat_id': int(chat_id_text), 'title': info.get('title') or 'Untitled', 'type': info.get('type') or 'group'})
    return sorted(result, key=lambda item: item['title'].casefold())

async def note_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool) -> None:
    lock = await _get_lock(-1)
    async with lock:
        path = _index_path()
        index = _read_json(path, {'chats': {}})
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
        _write_json_atomic(path, index)
