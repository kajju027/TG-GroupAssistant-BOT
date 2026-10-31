from __future__ import annotations

import asyncio
import sqlite3

from collections.abc import Iterable

from bot.core.config import DATABASE_PATH

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
_DB = str(DATABASE_PATH)

STAT_KEYS = ('messages', 'reactions', 'commands', 'downloads')

# Hot counters live in memory: inc_stat() never touches the disk on the
# message hot path. A background task flushes them to sqlite once a minute.
_stats_memory: dict[str, int] = {}


def _c() -> sqlite3.Connection:
    connection = sqlite3.connect(_DB, check_same_thread=False, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=10000')
    return connection


def init() -> None:
    global _stats_memory
    with _c() as connection:
        connection.executescript(
            '\n            CREATE TABLE IF NOT EXISTS allowed_users (\n                user_id    INTEGER PRIMARY KEY,\n                username   TEXT    DEFAULT \'\',\n                first_name TEXT    DEFAULT \'\',\n                added_at   TEXT    DEFAULT (datetime(\'now\'))\n            );\n            CREATE TABLE IF NOT EXISTS blocked_users (\n                user_id INTEGER PRIMARY KEY\n            );\n            CREATE TABLE IF NOT EXISTS stats (\n                key TEXT PRIMARY KEY,\n                val INTEGER NOT NULL DEFAULT 0\n            );\n        '
        )
        for key in STAT_KEYS:
            connection.execute('INSERT OR IGNORE INTO stats (key, val) VALUES (?, 0)', (key,))
        rows = connection.execute('SELECT key, val FROM stats').fetchall()
        _stats_memory = {row['key']: int(row['val']) for row in rows}


def inc_stat(key: str) -> None:
    """Increment a counter in memory — instant, zero disk I/O."""
    _stats_memory[key] = _stats_memory.get(key, 0) + 1


def get_stat(key: str) -> int:
    return _stats_memory.get(key, 0)


def get_all_stats() -> dict[str, int]:
    return dict(_stats_memory)


def flush_stats() -> None:
    if not _stats_memory:
        return
    with _c() as connection:
        for key, value in _stats_memory.items():
            connection.execute(
                'INSERT INTO stats (key, val) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET val=excluded.val',
                (key, int(value)),
            )


async def stats_flush_loop(interval: float = 60.0) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            flush_stats()
        except Exception:
            pass


def is_allowed(user_id: int) -> bool:
    with _c() as connection:
        return connection.execute('SELECT 1 FROM allowed_users WHERE user_id=?', (user_id,)).fetchone() is not None


def add_allowed(user_id: int, username: str, name: str) -> None:
    with _c() as connection:
        connection.execute(
            'INSERT INTO allowed_users (user_id, username, first_name) VALUES (?, ?, ?)\n               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name',
            (user_id, username or '', name or ''),
        )


def del_allowed(user_id: int) -> None:
    with _c() as connection:
        connection.execute('DELETE FROM allowed_users WHERE user_id=?', (user_id,))


def get_allowed() -> Iterable[sqlite3.Row]:
    with _c() as connection:
        return connection.execute('SELECT * FROM allowed_users ORDER BY added_at DESC').fetchall()


def is_blocked(user_id: int) -> bool:
    with _c() as connection:
        return connection.execute('SELECT 1 FROM blocked_users WHERE user_id=?', (user_id,)).fetchone() is not None


def block_user(user_id: int) -> None:
    with _c() as connection:
        connection.execute('INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)', (user_id,))


def unblock_user(user_id: int) -> None:
    with _c() as connection:
        connection.execute('DELETE FROM blocked_users WHERE user_id=?', (user_id,))
