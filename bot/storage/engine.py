import asyncio
import json
import os
from bot.core.config import CHATS_DIR
_DEFAULT_SETTINGS = {'chat_title': '', 'chat_type': '', 'antilink': False, 'antilink_action': 'delete', 'antilink_whitelist': [], 'antiword': False, 'antiword_action': 'delete', 'antiword_words': [], 'antispam': False, 'antispam_limit': 5, 'antispam_window': 10, 'antifake': False, 'antifake_mode': 'blacklist', 'antifake_prefixes': [], 'welcome': True, 'welcome_msg': 'Welcome {mention} to {group}!', 'goodbye': True, 'goodbye_msg': 'Goodbye {mention}, we will miss you!', 'warn_limit': 3, 'warn_action': 'kick', 'mute_on_join': False, 'reaction_enabled': False, 'reaction_emojis': ['👍'], 'reaction_mode': 'automatic', 'filters': {}, 'warnings': {}, 'spam_tracker': {}, 'muted_users': {}, 'admins_cache': [], 'bot_is_admin': False}
_locks = {}
_lock_guard = asyncio.Lock()

async def _get_lock(chat_id: int) -> asyncio.Lock:
    async with _lock_guard:
        if chat_id not in _locks:
            _locks[chat_id] = asyncio.Lock()
        return _locks[chat_id]

def _chat_path(chat_id: int) -> str:
    return os.path.join(CHATS_DIR, f'{chat_id}.json')

def _index_path() -> str:
    return os.path.join(CHATS_DIR, '_index.json')

def _ensure_dirs():
    os.makedirs(CHATS_DIR, exist_ok=True)

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default

def _write_json_atomic(path: str, data):
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

async def init_storage():
    _ensure_dirs()
    if not os.path.exists(_index_path()):
        _write_json_atomic(_index_path(), {'chats': {}})

async def load_chat(chat_id: int) -> dict:
    lock = await _get_lock(chat_id)
    async with lock:
        data = _read_json(_chat_path(chat_id), None)
        if data is None:
            data = dict(_DEFAULT_SETTINGS)
            data['filters'] = {}
            data['warnings'] = {}
            data['spam_tracker'] = {}
            data['muted_users'] = {}
            data['antilink_whitelist'] = []
            data['antiword_words'] = []
            data['antifake_prefixes'] = []
            data['reaction_emojis'] = ['👍']
            data['admins_cache'] = []
            _write_json_atomic(_chat_path(chat_id), data)
        merged = dict(_DEFAULT_SETTINGS)
        merged.update(data)
        return merged

async def save_chat(chat_id: int, data: dict):
    lock = await _get_lock(chat_id)
    async with lock:
        _write_json_atomic(_chat_path(chat_id), data)

async def update_chat(chat_id: int, **kwargs):
    data = await load_chat(chat_id)
    data.update(kwargs)
    await save_chat(chat_id, data)
    return data

async def update_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list):
    lock = await _get_lock(-1)
    async with lock:
        idx = _read_json(_index_path(), {'chats': {}})
        idx.setdefault('chats', {})
        idx['chats'][str(chat_id)] = {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'admin_user_ids': admin_user_ids}
        _write_json_atomic(_index_path(), idx)

async def remove_from_index(chat_id: int):
    lock = await _get_lock(-1)
    async with lock:
        idx = _read_json(_index_path(), {'chats': {}})
        idx.get('chats', {}).pop(str(chat_id), None)
        _write_json_atomic(_index_path(), idx)

async def get_managed_chats_for_user(user_id: int) -> list:
    idx = _read_json(_index_path(), {'chats': {}})
    result = []
    for chat_id_str, info in idx.get('chats', {}).items():
        if not info.get('bot_is_admin'):
            continue
        if user_id in info.get('admin_user_ids', []):
            result.append({'chat_id': int(chat_id_str), 'title': info.get('title') or 'Untitled', 'type': info.get('type') or 'group'})
    return result

async def note_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool):
    lock = await _get_lock(-1)
    async with lock:
        idx = _read_json(_index_path(), {'chats': {}})
        idx.setdefault('chats', {})
        entry = idx['chats'].setdefault(str(chat_id), {'title': chat_title, 'type': chat_type, 'bot_is_admin': bot_is_admin, 'admin_user_ids': []})
        entry['title'] = chat_title or entry.get('title', '')
        entry['type'] = chat_type or entry.get('type', '')
        entry['bot_is_admin'] = bot_is_admin
        admin_ids = set(entry.get('admin_user_ids', []))
        if is_admin:
            admin_ids.add(user_id)
        else:
            admin_ids.discard(user_id)
        entry['admin_user_ids'] = list(admin_ids)
        _write_json_atomic(_index_path(), idx)
