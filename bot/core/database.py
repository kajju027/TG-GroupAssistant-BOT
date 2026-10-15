from __future__ import annotations
import sqlite3
from collections.abc import Iterable
from bot.core.config import DATABASE_PATH
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
_DB = str(DATABASE_PATH)

def _c() -> sqlite3.Connection:
    connection = sqlite3.connect(_DB, check_same_thread=False, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=10000')
    connection.execute('PRAGMA foreign_keys=ON')
    return connection

def init() -> None:
    with _c() as connection:
        connection.executescript("\n            CREATE TABLE IF NOT EXISTS allowed_users (\n                user_id    INTEGER PRIMARY KEY,\n                username   TEXT    DEFAULT '',\n                first_name TEXT    DEFAULT '',\n                added_at   TEXT    DEFAULT (datetime('now'))\n            );\n            CREATE TABLE IF NOT EXISTS blocked_users (\n                user_id INTEGER PRIMARY KEY\n            );\n            CREATE TABLE IF NOT EXISTS groups (\n                chat_id         INTEGER PRIMARY KEY,\n                title           TEXT    DEFAULT '',\n                welcome_text    TEXT    DEFAULT NULL,\n                welcome_enabled INTEGER DEFAULT 1,\n                react_enabled   INTEGER DEFAULT 0,\n                react_emoji     TEXT    DEFAULT '🔥'\n            );\n            CREATE TABLE IF NOT EXISTS warnings (\n                id        INTEGER PRIMARY KEY AUTOINCREMENT,\n                user_id   INTEGER NOT NULL,\n                chat_id   INTEGER NOT NULL,\n                reason    TEXT    DEFAULT 'No reason',\n                warned_at TEXT    DEFAULT (datetime('now'))\n            );\n            CREATE TABLE IF NOT EXISTS stats (\n                key TEXT PRIMARY KEY,\n                val INTEGER NOT NULL DEFAULT 0\n            );\n            ")
        for key in ('messages', 'reactions', 'commands', 'downloads', 'music'):
            connection.execute('INSERT OR IGNORE INTO stats (key, val) VALUES (?, 0)', (key,))

def is_allowed(user_id: int) -> bool:
    with _c() as connection:
        return connection.execute('SELECT 1 FROM allowed_users WHERE user_id=?', (user_id,)).fetchone() is not None

def add_allowed(user_id: int, username: str, name: str) -> None:
    with _c() as connection:
        connection.execute('INSERT INTO allowed_users (user_id, username, first_name) VALUES (?, ?, ?)\n               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name', (user_id, username or '', name or ''))

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

def ensure_group(chat_id: int, title: str) -> None:
    with _c() as connection:
        connection.execute('INSERT INTO groups (chat_id, title) VALUES (?, ?)\n               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title', (chat_id, title or ''))

def get_group(chat_id: int) -> sqlite3.Row | None:
    with _c() as connection:
        return connection.execute('SELECT * FROM groups WHERE chat_id=?', (chat_id,)).fetchone()

def set_welcome_text(chat_id: int, text: str) -> None:
    with _c() as connection:
        connection.execute('UPDATE groups SET welcome_text=? WHERE chat_id=?', (text, chat_id))

def toggle_welcome(chat_id: int, enabled: bool) -> None:
    with _c() as connection:
        connection.execute('UPDATE groups SET welcome_enabled=? WHERE chat_id=?', (int(enabled), chat_id))

def toggle_react(chat_id: int, enabled: bool) -> None:
    with _c() as connection:
        connection.execute('UPDATE groups SET react_enabled=? WHERE chat_id=?', (int(enabled), chat_id))

def set_react_emoji(chat_id: int, emoji: str) -> None:
    with _c() as connection:
        connection.execute('UPDATE groups SET react_emoji=? WHERE chat_id=?', (emoji, chat_id))

def all_groups() -> Iterable[sqlite3.Row]:
    with _c() as connection:
        return connection.execute('SELECT * FROM groups ORDER BY title COLLATE NOCASE').fetchall()

def add_warn(user_id: int, chat_id: int, reason: str) -> int:
    with _c() as connection:
        connection.execute('INSERT INTO warnings (user_id, chat_id, reason) VALUES (?, ?, ?)', (user_id, chat_id, reason[:500]))
        row = connection.execute('SELECT COUNT(*) FROM warnings WHERE user_id=? AND chat_id=?', (user_id, chat_id)).fetchone()
        return int(row[0]) if row else 0

def warn_count(user_id: int, chat_id: int) -> int:
    with _c() as connection:
        row = connection.execute('SELECT COUNT(*) FROM warnings WHERE user_id=? AND chat_id=?', (user_id, chat_id)).fetchone()
        return int(row[0]) if row else 0

def get_warns(user_id: int, chat_id: int) -> Iterable[sqlite3.Row]:
    with _c() as connection:
        return connection.execute('SELECT * FROM warnings WHERE user_id=? AND chat_id=? ORDER BY warned_at DESC, id DESC', (user_id, chat_id)).fetchall()

def clear_warns(user_id: int, chat_id: int) -> None:
    with _c() as connection:
        connection.execute('DELETE FROM warnings WHERE user_id=? AND chat_id=?', (user_id, chat_id))

def inc_stat(key: str) -> None:
    with _c() as connection:
        connection.execute('INSERT OR IGNORE INTO stats (key, val) VALUES (?, 0)', (key,))
        connection.execute('UPDATE stats SET val=val+1 WHERE key=?', (key,))

def get_stat(key: str) -> int:
    with _c() as connection:
        row = connection.execute('SELECT val FROM stats WHERE key=?', (key,)).fetchone()
        return int(row[0]) if row else 0
