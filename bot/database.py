from __future__ import annotations

import datetime

from typing import Any

from bot.storage.engine import (
    list_active_chats,
    list_chats_for_user,
    load_chat,
    load_settings,
    mark_bot_left,
    mutate_chat,
    note_admin_seen,
    update_chat,
    update_index,
)


async def init_db() -> None:
    from bot.storage.engine import init_storage

    await init_storage()


async def get_settings(chat_id: int) -> dict[str, Any]:
    return await load_settings(chat_id)


async def get_full_chat(chat_id: int) -> dict[str, Any]:
    return await load_chat(chat_id)


async def update_setting(chat_id: int, key: str, value: Any) -> None:
    await update_chat(chat_id, **{key: value})


async def reset_chat_settings(chat_id: int) -> None:
    """Back to factory defaults (title/type and member data are kept)."""

    def reset(data: dict[str, Any]) -> None:
        from bot.storage.engine import _DEFAULT_SETTINGS

        for key, value in _DEFAULT_SETTINGS.items():
            data[key] = value

    await mutate_chat(chat_id, reset)


# ------------------------------------------------------------- warnings ----
async def get_warnings(chat_id: int, user_id: int) -> list[dict[str, str]]:
    data = await load_chat(chat_id)
    entries = data.get('warnings', {}).get(str(user_id), [])
    return sorted(entries, key=lambda warning: warning.get('created_at', ''), reverse=True)


async def add_warning(chat_id: int, user_id: int, reason: str) -> int:

    def add(data: dict[str, Any]) -> int:
        warnings = data.setdefault('warnings', {})
        entries = warnings.setdefault(str(user_id), [])
        entries.append({
            'reason': reason[:500],
            'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        })
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


# -------------------------------------------------------------- filters ----
async def get_filters(chat_id: int) -> list[dict[str, str]]:
    data = await load_chat(chat_id)
    return [
        {'keyword': keyword, 'reply': str(value)}
        for keyword, value in data.get('filters', {}).items()
    ]


async def add_filter(chat_id: int, keyword: str, reply: str) -> None:
    keyword = keyword.strip().casefold()
    if not keyword:
        return

    def add(data: dict[str, Any]) -> None:
        data.setdefault('filters', {})[keyword] = reply[:4000]

    await mutate_chat(chat_id, add)


async def remove_filter(chat_id: int, keyword: str) -> None:
    keyword = keyword.strip().casefold()
    await mutate_chat(chat_id, lambda data: data.get('filters', {}).pop(keyword, None))


# ------------------------------------------------------------ anti-word ----
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


# ----------------------------------------------------------- anti-link -----
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


# ----------------------------------------------------------- chat index ----
async def sync_chat_index(chat_id: int, chat_title: str, chat_type: str, bot_is_admin: bool, admin_user_ids: list[int]) -> None:
    await update_index(chat_id, chat_title, chat_type, bot_is_admin, admin_user_ids)
    await update_chat(chat_id, chat_title=chat_title, chat_type=chat_type, bot_is_admin=bot_is_admin, admins_cache=admin_user_ids)


async def drop_chat_from_index(chat_id: int) -> None:
    """Bot removed: mark inactive but KEEP the settings."""
    await mark_bot_left(chat_id)


async def list_managed_chats(user_id: int, *, owner: bool) -> list[dict[str, Any]]:
    return await list_chats_for_user(user_id, owner=owner)


async def list_broadcast_chats() -> list[dict[str, Any]]:
    return await list_active_chats()


async def note_chat_admin_seen(chat_id: int, chat_title: str, chat_type: str, user_id: int, is_admin: bool, bot_is_admin: bool) -> None:
    await note_admin_seen(chat_id, chat_title, chat_type, user_id, is_admin, bot_is_admin)


# -------------------------------------------------------- seen members -----
async def note_seen_member(chat_id: int, user_id: int, name: str, is_bot: bool = False) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

    def note(data: dict[str, Any]) -> None:
        members = data.setdefault('members', {})
        members[str(user_id)] = {'name': str(name)[:128], 'bot': bool(is_bot), 'seen': now}
        if len(members) > 500:
            keep = sorted(members.items(), key=lambda item: item[1].get('seen', ''), reverse=True)[:400]
            data['members'] = dict(keep)

    await mutate_chat(chat_id, note)


async def remove_seen_member(chat_id: int, user_id: int) -> None:
    await mutate_chat(chat_id, lambda data: data.get('members', {}).pop(str(user_id), None))


async def get_seen_members(chat_id: int) -> list[dict[str, Any]]:
    data = await load_chat(chat_id)
    members = data.get('members', {})
    result = []
    for user_id, info in members.items():
        if info.get('bot'):
            continue
        try:
            result.append({'user_id': int(user_id), 'name': str(info.get('name', '')) or str(user_id), 'seen': info.get('seen', '')})
        except (TypeError, ValueError):
            continue
    result.sort(key=lambda item: item.get('seen', ''), reverse=True)
    return result


# ----------------------------------------------------------- auto-purge ----
async def get_autodelete_cursor(chat_id: int) -> int:
    data = await load_chat(chat_id)
    return int(data.get('autodelete_last_id', 0) or 0)


async def set_autodelete_cursor(chat_id: int, message_id: int) -> None:
    """Advance the cursor so the next sweep picks up where this one stopped."""
    await mutate_chat(chat_id, lambda data: data.__setitem__('autodelete_last_id', int(message_id)))


async def acquire_autodelete_lock(chat_id: int) -> bool:
    """Try to grab the sweep lock. Returns True when acquired, False when a
    sweep is already running (avoids overlapping deletes)."""
    acquired = False

    def grab(data: dict[str, Any]) -> None:
        nonlocal acquired
        if data.get('autodelete_running'):
            return
        data['autodelete_running'] = True
        acquired = True

    await mutate_chat(chat_id, grab)
    return acquired


async def release_autodelete_lock(chat_id: int) -> None:
    await mutate_chat(chat_id, lambda data: data.__setitem__('autodelete_running', False))
