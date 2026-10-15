from __future__ import annotations
import datetime
from typing import Any
from bot.storage.engine import get_managed_chats_for_user, init_storage, load_chat, mutate_chat, note_admin_seen, remove_from_index, update_chat, update_index

async def init_db() -> None:
    await init_storage()

async def get_settings(chat_id: int) -> dict[str, Any]:
    return await load_chat(chat_id)

async def update_setting(chat_id: int, key: str, value: Any) -> None:
    await update_chat(chat_id, **{key: value})

async def get_warnings(chat_id: int, user_id: int) -> list[dict[str, str]]:
    data = await load_chat(chat_id)
    entries = data.get('warnings', {}).get(str(user_id), [])
    return sorted(entries, key=lambda warning: warning.get('created_at', ''), reverse=True)

async def add_warning(chat_id: int, user_id: int, reason: str) -> int:

    def add(data: dict[str, Any]) -> int:
        warnings = data.setdefault('warnings', {})
        entries = warnings.setdefault(str(user_id), [])
        entries.append({'reason': reason[:500], 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')})
        return len(entries)
    return await mutate_chat(chat_id, add)

async def reset_warnings(chat_id: int, user_id: int) -> None:
    await mutate_chat(chat_id, lambda data: data.get('warnings', {}).pop(str(user_id), None))

async def remove_last_warning(chat_id: int, user_id: int) -> int:

    def remove(data: dict[str, Any]) -> int:
        warnings = data.get('warnings', {})
        entries = warnings.get(str(user_id), [])
        if not entries:
            return 0
        entries.sort(key=lambda warning: warning.get('created_at', ''))
        entries.pop()
        if entries:
            warnings[str(user_id)] = entries
        else:
            warnings.pop(str(user_id), None)
        return len(entries)
    return await mutate_chat(chat_id, remove)

async def next_reaction_index(chat_id: int) -> int:

    def increment(data: dict[str, Any]) -> int:
        index = int(data.get('_reaction_index', 0))
        data['_reaction_index'] = index + 1
        return index
    return await mutate_chat(chat_id, increment)

async def get_banned_words(chat_id: int) -> list[str]:
    return list((await load_chat(chat_id)).get('antiword_words', []))

async def add_banned_word(chat_id: int, word: str) -> None:
    word = word.strip().casefold()
    if not word:
        return

    def add(data: dict[str, Any]) -> None:
        words = data.setdefault('antiword_words', [])
        if word not in words:
            words.append(word)
    await mutate_chat(chat_id, add)

async def remove_banned_word(chat_id: int, word: str) -> None:
    word = word.strip().casefold()
    await mutate_chat(chat_id, lambda data: data.__setitem__('antiword_words', [item for item in data.get('antiword_words', []) if item != word]))

async def get_whitelisted_links(chat_id: int) -> list[str]:
    return list((await load_chat(chat_id)).get('antilink_whitelist', []))

async def add_whitelist_link(chat_id: int, link: str) -> None:
    link = link.strip().casefold()
    if not link:
        return

    def add(data: dict[str, Any]) -> None:
        links = data.setdefault('antilink_whitelist', [])
        if link not in links:
            links.append(link)
    await mutate_chat(chat_id, add)

async def remove_whitelist_link(chat_id: int, link: str) -> None:
    link = link.strip().casefold()
    await mutate_chat(chat_id, lambda data: data.__setitem__('antilink_whitelist', [item for item in data.get('antilink_whitelist', []) if item != link]))

async def get_spam_count(chat_id: int, user_id: int, window: int) -> int:
    data = await load_chat(chat_id)
    entry = data.get('spam_tracker', {}).get(str(user_id))
    if not entry:
        return 0
    try:
        started = datetime.datetime.fromisoformat(entry['window_start'])
    except (KeyError, TypeError, ValueError):
        return 0
    now = datetime.datetime.now(datetime.timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=datetime.timezone.utc)
    return int(entry.get('count', 0)) if (now - started).total_seconds() <= window else 0

async def increment_spam(chat_id: int, user_id: int) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)

    def increment(data: dict[str, Any]) -> int:
        tracker = data.setdefault('spam_tracker', {})
        entry = tracker.get(str(user_id))
        window = int(data.get('antispam_window', 10))
        if entry:
            try:
                started = datetime.datetime.fromisoformat(entry['window_start'])
                if started.tzinfo is None:
                    started = started.replace(tzinfo=datetime.timezone.utc)
            except (KeyError, TypeError, ValueError):
                started = now - datetime.timedelta(seconds=window + 1)
            if (now - started).total_seconds() <= window:
                entry['count'] = int(entry.get('count', 0)) + 1
            else:
                entry = {'count': 1, 'window_start': now.isoformat()}
        else:
            entry = {'count': 1, 'window_start': now.isoformat()}
        tracker[str(user_id)] = entry
        return int(entry['count'])
    return await mutate_chat(chat_id, increment)

async def reset_spam(chat_id: int, user_id: int) -> None:
    await mutate_chat(chat_id, lambda data: data.get('spam_tracker', {}).pop(str(user_id), None))

async def get_filters(chat_id: int) -> list[dict[str, str]]:
    data = await load_chat(chat_id)
    return [{'keyword': keyword, 'reply': reply} for keyword, reply in data.get('filters', {}).items()]

async def add_filter(chat_id: int, keyword: str, reply: str) -> None:
    keyword = keyword.strip().casefold()
    if not keyword:
        return
    await mutate_chat(chat_id, lambda data: data.setdefault('filters', {}).__setitem__(keyword, reply[:4000]))

async def remove_filter(chat_id: int, keyword: str) -> None:
    keyword = keyword.strip().casefold()
    await mutate_chat(chat_id, lambda data: data.get('filters', {}).pop(keyword, None))

async def get_antifake_prefixes(chat_id: int) -> list[str]:
    return list((await load_chat(chat_id)).get('antifake_prefixes', []))

async def add_antifake_prefix(chat_id: int, prefix: str) -> None:
    prefix = prefix.strip()
    if not prefix:
        return

    def add(data: dict[str, Any]) -> None:
        prefixes = data.setdefault('antifake_prefixes', [])
        if prefix not in prefixes:
            prefixes.append(prefix)
    await mutate_chat(chat_id, add)

async def remove_antifake_prefix(chat_id: int, prefix: str) -> None:
    prefix = prefix.strip()
    await mutate_chat(chat_id, lambda data: data.__setitem__('antifake_prefixes', [item for item in data.get('antifake_prefixes', []) if item != prefix]))

async def sync_chat_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list[int]) -> None:
    await update_index(chat_id, chat_title, chat_type, bot_is_admin, admin_user_ids)
    await update_chat(chat_id, chat_title=chat_title, chat_type=chat_type, bot_is_admin=bot_is_admin, admins_cache=admin_user_ids)

async def drop_chat_from_index(chat_id: int) -> None:
    await remove_from_index(chat_id)

async def list_managed_chats(user_id: int) -> list[dict[str, Any]]:
    return await get_managed_chats_for_user(user_id)

async def note_chat_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool) -> None:
    await note_admin_seen(chat_id, chat_title, chat_type, user_id, is_admin, bot_is_admin)
