import datetime
from bot.storage.engine import init_storage, load_chat, save_chat, update_chat, update_index, remove_from_index, get_managed_chats_for_user, note_admin_seen

async def init_db():
    await init_storage()

async def get_settings(chat_id: int) -> dict:
    return await load_chat(chat_id)

async def update_setting(chat_id: int, key: str, value):
    await update_chat(chat_id, **{key: value})

async def get_warnings(chat_id: int, user_id: int) -> list:
    data = await load_chat(chat_id)
    entries = data.get('warnings', {}).get(str(user_id), [])
    return sorted(entries, key=lambda w: w.get('created_at', ''), reverse=True)

async def add_warning(chat_id: int, user_id: int, reason: str) -> int:
    data = await load_chat(chat_id)
    warnings = data.setdefault('warnings', {})
    user_warnings = warnings.setdefault(str(user_id), [])
    user_warnings.append({'reason': reason, 'created_at': datetime.datetime.now().isoformat(timespec='minutes')})
    await save_chat(chat_id, data)
    return len(user_warnings)

async def reset_warnings(chat_id: int, user_id: int):
    data = await load_chat(chat_id)
    data.get('warnings', {}).pop(str(user_id), None)
    await save_chat(chat_id, data)

async def remove_last_warning(chat_id: int, user_id: int) -> int:
    data = await load_chat(chat_id)
    warnings = data.get('warnings', {})
    entries = warnings.get(str(user_id), [])
    if not entries:
        return 0
    entries.sort(key=lambda w: w.get('created_at', ''))
    entries.pop()
    if entries:
        warnings[str(user_id)] = entries
    else:
        warnings.pop(str(user_id), None)
    await save_chat(chat_id, data)
    return len(entries)

async def next_reaction_index(chat_id: int) -> int:
    data = await load_chat(chat_id)
    idx = data.get('_reaction_index', 0)
    data['_reaction_index'] = idx + 1
    await save_chat(chat_id, data)
    return idx

async def get_banned_words(chat_id: int) -> list:
    data = await load_chat(chat_id)
    return data.get('antiword_words', [])

async def add_banned_word(chat_id: int, word: str):
    data = await load_chat(chat_id)
    words = data.setdefault('antiword_words', [])
    word = word.lower()
    if word not in words:
        words.append(word)
    await save_chat(chat_id, data)

async def remove_banned_word(chat_id: int, word: str):
    data = await load_chat(chat_id)
    word = word.lower()
    data['antiword_words'] = [w for w in data.get('antiword_words', []) if w != word]
    await save_chat(chat_id, data)

async def get_whitelisted_links(chat_id: int) -> list:
    data = await load_chat(chat_id)
    return data.get('antilink_whitelist', [])

async def add_whitelist_link(chat_id: int, link: str):
    data = await load_chat(chat_id)
    links = data.setdefault('antilink_whitelist', [])
    link = link.lower().strip()
    if link not in links:
        links.append(link)
    await save_chat(chat_id, data)

async def remove_whitelist_link(chat_id: int, link: str):
    data = await load_chat(chat_id)
    link = link.lower().strip()
    data['antilink_whitelist'] = [l for l in data.get('antilink_whitelist', []) if l != link]
    await save_chat(chat_id, data)

async def get_spam_count(chat_id: int, user_id: int, window: int) -> int:
    data = await load_chat(chat_id)
    tracker = data.get('spam_tracker', {}).get(str(user_id))
    if not tracker:
        return 0
    ws = datetime.datetime.fromisoformat(tracker['window_start'])
    if (datetime.datetime.now() - ws).total_seconds() > window:
        return 0
    return tracker.get('count', 0)

async def increment_spam(chat_id: int, user_id: int) -> int:
    data = await load_chat(chat_id)
    tracker = data.setdefault('spam_tracker', {})
    entry = tracker.get(str(user_id))
    window = data.get('antispam_window', 10)
    now = datetime.datetime.now()
    if entry:
        ws = datetime.datetime.fromisoformat(entry['window_start'])
        if (now - ws).total_seconds() > window:
            entry = {'count': 1, 'window_start': now.isoformat()}
        else:
            entry['count'] = entry.get('count', 0) + 1
    else:
        entry = {'count': 1, 'window_start': now.isoformat()}
    tracker[str(user_id)] = entry
    await save_chat(chat_id, data)
    return entry['count']

async def reset_spam(chat_id: int, user_id: int):
    data = await load_chat(chat_id)
    data.get('spam_tracker', {}).pop(str(user_id), None)
    await save_chat(chat_id, data)

async def get_filters(chat_id: int) -> list:
    data = await load_chat(chat_id)
    return [{'keyword': k, 'reply': v} for k, v in data.get('filters', {}).items()]

async def add_filter(chat_id: int, keyword: str, reply: str):
    data = await load_chat(chat_id)
    data.setdefault('filters', {})[keyword.lower()] = reply
    await save_chat(chat_id, data)

async def remove_filter(chat_id: int, keyword: str):
    data = await load_chat(chat_id)
    data.get('filters', {}).pop(keyword.lower(), None)
    await save_chat(chat_id, data)

async def get_antifake_prefixes(chat_id: int) -> list:
    data = await load_chat(chat_id)
    return data.get('antifake_prefixes', [])

async def add_antifake_prefix(chat_id: int, prefix: str):
    data = await load_chat(chat_id)
    prefixes = data.setdefault('antifake_prefixes', [])
    if prefix not in prefixes:
        prefixes.append(prefix)
    await save_chat(chat_id, data)

async def remove_antifake_prefix(chat_id: int, prefix: str):
    data = await load_chat(chat_id)
    data['antifake_prefixes'] = [p for p in data.get('antifake_prefixes', []) if p != prefix]
    await save_chat(chat_id, data)

async def get_muted_user(chat_id: int, user_id: int):
    data = await load_chat(chat_id)
    return data.get('muted_users', {}).get(str(user_id))

async def set_muted_user(chat_id: int, user_id: int, until_iso):
    data = await load_chat(chat_id)
    muted = data.setdefault('muted_users', {})
    if until_iso is None:
        muted.pop(str(user_id), None)
    else:
        muted[str(user_id)] = until_iso
    await save_chat(chat_id, data)

async def sync_chat_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list):
    await update_index(chat_id, chat_title, chat_type, bot_is_admin, admin_user_ids)
    await update_chat(chat_id, chat_title=chat_title, chat_type=chat_type, bot_is_admin=bot_is_admin, admins_cache=admin_user_ids)

async def drop_chat_from_index(chat_id: int):
    await remove_from_index(chat_id)

async def list_managed_chats(user_id: int) -> list:
    return await get_managed_chats_for_user(user_id)

async def note_chat_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool):
    await note_admin_seen(chat_id, chat_title, chat_type, user_id, is_admin, bot_is_admin)
