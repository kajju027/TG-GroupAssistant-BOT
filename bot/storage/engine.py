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

# ---------------------------------------------------------------- defaults --
# EVERY feature ships disabled. Nothing turns itself on.
_DEFAULT_SETTINGS: dict[str, Any] = {
    'chat_title': '',
    'chat_type': '',
    # 🎭 reactions
    'reaction_enabled': False,
    'reaction_mode': 'random',          # random | cycle | fixed
    'reaction_emojis': ['🔥', '❤', '👏', '🎉', '💯'],
    # 👋 welcome / goodbye (need a text before they can fire)
    'welcome': False,
    'welcome_msg': '',
    'goodbye': False,
    'goodbye_msg': '',
    # 🔗 anti-link
    'antilink': False,
    'antilink_action': 'delete',        # delete | warn | kick | ban
    'antilink_whitelist': [],
    # 🔤 anti-word
    'antiword': False,
    'antiword_action': 'delete',
    'antiword_words': [],
    # 🚫 anti-spam
    'antispam': False,
    'antispam_limit': 5,
    'antispam_window': 10,
    # ⚠️ warnings
    'warn_limit': 3,
    'warn_action': 'kick',              # kick | ban | mute
    # 🛡️ channel anti-tag guard
    'antitag': False,
    # bookkeeping (filled by the trackers)
    'admins_cache': [],
    'bot_is_admin': False,
}

# Keys that never travel through the hot read path.
_HOT_KEYS = {'warnings', 'members'}

# Old builds shipped welcome/goodbye ON with these template texts. On
# migration they are reset to OFF + empty so nothing shouts on its own.
_LEGACY_TEXTS = {
    '🌟 <b>Welcome, {mention}!</b>\n\n🎉 You just joined <b>{group}</b>.\n\n💫 You are member <b>#{count}</b> — feel at home!',
    '👋 <b>Goodbye, {mention}!</b>\n\n💔 You left <b>{group}</b>.\n\n😢 We now have <b>{count}</b> members. Take care!',
}

T = TypeVar('T')

_locks: dict[int, asyncio.Lock] = {}
_lock_guard = asyncio.Lock()

# In-memory mirror of every chat file — the working copy for all calls, so
# the bot keeps running even when the filesystem is read-only.
_memory: dict[int, dict[str, Any]] = {}
_index_memory: dict[str, Any] | None = None

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
    """Persist to disk atomically. False when the disk refuses writes —
    the caller keeps the data in memory and the bot stays alive."""
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
                log.info('Disk storage recovered — settings are being saved again.')
        return True
    except OSError as error:
        _disk_ok = False
        _last_retry = now
        if not _disk_warned:
            _disk_warned = True
            log.warning(
                'Cannot write settings to %s (%s). Running on in-memory storage: '
                'settings reset when the bot restarts. Point DATA_DIR at a '
                'persistent folder to keep them.',
                path.parent, type(error).__name__,
            )
        return False


def _normalise_chat(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(_DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)
    # Migration + safety: welcome/goodbye may only stay ON when a real
    # custom text exists (old builds shipped always-on template texts).
    if not merged.get('welcome_msg') or merged.get('welcome_msg') in _LEGACY_TEXTS:
        merged['welcome_msg'] = ''
        merged['welcome'] = False
    if not merged.get('goodbye_msg') or merged.get('goodbye_msg') in _LEGACY_TEXTS:
        merged['goodbye_msg'] = ''
        merged['goodbye'] = False
    merged.pop('_reaction_index', None)
    merged.pop('spam_tracker', None)
    merged.pop('muted_users', None)
    return merged


async def init_storage() -> None:
    _ensure_dirs()
    if not _index_path().exists():
        _write_json_atomic(_index_path(), {'chats': {}})


async def _ensure_loaded(chat_id: int) -> dict[str, Any]:
    cached = _memory.get(chat_id)
    if cached is None:
        cached = _normalise_chat(_read_json(_chat_path(chat_id), {}))
        _memory[chat_id] = cached
        _write_json_atomic(_chat_path(chat_id), cached)
    return cached


async def load_chat(chat_id: int) -> dict[str, Any]:
    """Full chat record (settings + members + warnings)."""
    lock = await _get_lock(chat_id)
    async with lock:
        return copy.deepcopy(await _ensure_loaded(chat_id))


async def load_settings(chat_id: int) -> dict[str, Any]:
    """Lightweight settings-only view used on the message hot path —
    no deep copies of the big member/warning blobs."""
    lock = await _get_lock(chat_id)
    async with lock:
        cached = await _ensure_loaded(chat_id)
    return {key: copy.deepcopy(value) for key, value in cached.items() if key not in _HOT_KEYS}


async def mutate_chat(chat_id: int, mutator: Callable[[dict[str, Any]], T]) -> T:
    lock = await _get_lock(chat_id)
    async with lock:
        cached = await _ensure_loaded(chat_id)
        result = mutator(cached)
        _write_json_atomic(_chat_path(chat_id), cached)
        return result


async def update_chat(chat_id: int, **kwargs: Any) -> dict[str, Any]:

    def apply(data: dict[str, Any]) -> dict[str, Any]:
        data.update(kwargs)
        return {key: copy.deepcopy(value) for key, value in data.items() if key not in _HOT_KEYS}

    return await mutate_chat(chat_id, apply)


def _load_index() -> dict[str, Any]:
    global _index_memory
    if _index_memory is None:
        loaded = _read_json(_index_path(), {'chats': {}})
        _index_memory = loaded if isinstance(loaded, dict) else {'chats': {}}
        _index_memory.setdefault('chats', {})
    return _index_memory


async def update_index(
    chat_id: int,
    chat_title: str,
    chat_type: str,
    bot_is_admin: bool,
    admin_user_ids: list[int],
) -> None:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        entry = index.setdefault('chats', {}).setdefault(
            str(chat_id),
            {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'bot_in_chat': True, 'admin_user_ids': []},
        )
        entry['title'] = chat_title or entry.get('title', '')
        entry['type'] = chat_type or entry.get('type', '')
        entry['bot_is_admin'] = bool(bot_is_admin)
        entry['bot_in_chat'] = True
        entry['admin_user_ids'] = sorted(set(admin_user_ids))
        _write_json_atomic(_index_path(), index)


async def mark_bot_left(chat_id: int) -> None:
    """The bot was removed: keep the entry + settings so everything comes
    back the moment it is re-added — nothing is wiped."""
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        entry = index.get('chats', {}).get(str(chat_id))
        if entry is not None:
            entry['bot_in_chat'] = False
            entry['bot_is_admin'] = False
            _write_json_atomic(_index_path(), index)


async def note_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool) -> None:
    lock = await _get_lock(-1)
    async with lock:
        index = _load_index()
        entry = index.setdefault('chats', {}).setdefault(
            str(chat_id),
            {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'bot_in_chat': True, 'admin_user_ids': []},
        )
        entry['title'] = chat_title or entry.get('title', '')
        entry['type'] = chat_type or entry.get('type', '')
        entry['bot_is_admin'] = bool(bot_is_admin)
        entry['bot_in_chat'] = True
        admins = set(entry.get('admin_user_ids', []))
        if is_admin:
            admins.add(user_id)
        else:
            admins.discard(user_id)
        entry['admin_user_ids'] = sorted(admins)
        _write_json_atomic(_index_path(), index)


async def list_chats_for_user(user_id: int, *, owner: bool) -> list[dict[str, Any]]:
    """Chats the user may manage. The bot owner/sudo users see every chat
    the bot sits in (so they can configure groups AND channels from the
    private chat); everyone else only sees chats where they are admin."""
    lock = await _get_lock(-1)
    async with lock:
        index = copy.deepcopy(_load_index())
    result: list[dict[str, Any]] = []
    for chat_id_text, info in index.get('chats', {}).items():
        in_chat = bool(info.get('bot_in_chat', True))
        if owner:
            result.append({'chat_id': int(chat_id_text), 'title': info.get('title') or 'Untitled',
                           'type': info.get('type') or 'group', 'bot_in_chat': in_chat})
        elif in_chat and info.get('bot_is_admin') and user_id in info.get('admin_user_ids', []):
            result.append({'chat_id': int(chat_id_text), 'title': info.get('title') or 'Untitled',
                           'type': info.get('type') or 'group', 'bot_in_chat': True})
    return sorted(result, key=lambda item: (not item['bot_in_chat'], item['type'] != 'channel', item['title'].casefold()))


async def list_active_chats() -> list[dict[str, Any]]:
    """Every chat the bot currently sits in (used by broadcast)."""
    lock = await _get_lock(-1)
    async with lock:
        index = copy.deepcopy(_load_index())
    result: list[dict[str, Any]] = []
    for chat_id_text, info in index.get('chats', {}).items():
        if info.get('bot_in_chat', True):
            result.append({'chat_id': int(chat_id_text), 'title': info.get('title') or 'Untitled',
                           'type': info.get('type') or 'group'})
    return result
