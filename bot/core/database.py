import sqlite3
from bot.core.config import DATABASE_PATH

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
_DB = str(DATABASE_PATH)


def _c():
    c = sqlite3.connect(_DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _c() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS allowed_users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT    DEFAULT '',
                first_name TEXT    DEFAULT '',
                added_at   TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS groups (
                chat_id         INTEGER PRIMARY KEY,
                title           TEXT    DEFAULT '',
                welcome_text    TEXT    DEFAULT NULL,
                welcome_enabled INTEGER DEFAULT 1,
                react_enabled   INTEGER DEFAULT 0,
                react_emoji     TEXT    DEFAULT '🔥'
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                chat_id   INTEGER NOT NULL,
                reason    TEXT    DEFAULT 'No reason',
                warned_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                val INTEGER DEFAULT 0
            );
        """)
        for k in ("messages", "reactions", "commands", "downloads"):
            c.execute("INSERT OR IGNORE INTO stats (key,val) VALUES (?,0)", (k,))
        c.commit()


def is_allowed(uid: int) -> bool:
    with _c() as c:
        return c.execute("SELECT 1 FROM allowed_users WHERE user_id=?", (uid,)).fetchone() is not None


def add_allowed(uid: int, username: str, name: str):
    with _c() as c:
        c.execute("INSERT OR REPLACE INTO allowed_users (user_id,username,first_name) VALUES(?,?,?)",
                  (uid, username or "", name or ""))
        c.commit()


def del_allowed(uid: int):
    with _c() as c:
        c.execute("DELETE FROM allowed_users WHERE user_id=?", (uid,))
        c.commit()


def get_allowed():
    with _c() as c:
        return c.execute("SELECT * FROM allowed_users ORDER BY added_at DESC").fetchall()


def is_blocked(uid: int) -> bool:
    with _c() as c:
        return c.execute("SELECT 1 FROM blocked_users WHERE user_id=?", (uid,)).fetchone() is not None


def block_user(uid: int):
    with _c() as c:
        c.execute("INSERT OR IGNORE INTO blocked_users VALUES(?)", (uid,))
        c.commit()


def unblock_user(uid: int):
    with _c() as c:
        c.execute("DELETE FROM blocked_users WHERE user_id=?", (uid,))
        c.commit()


def ensure_group(chat_id: int, title: str):
    with _c() as c:
        c.execute("INSERT OR IGNORE INTO groups (chat_id,title) VALUES(?,?)", (chat_id, title or ""))
        c.execute("UPDATE groups SET title=? WHERE chat_id=?", (title or "", chat_id))
        c.commit()


def get_group(chat_id: int):
    with _c() as c:
        return c.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,)).fetchone()


def set_welcome_text(chat_id: int, text: str):
    with _c() as c:
        c.execute("UPDATE groups SET welcome_text=? WHERE chat_id=?", (text, chat_id))
        c.commit()


def toggle_welcome(chat_id: int, on: bool):
    with _c() as c:
        c.execute("UPDATE groups SET welcome_enabled=? WHERE chat_id=?", (1 if on else 0, chat_id))
        c.commit()


def toggle_react(chat_id: int, on: bool):
    with _c() as c:
        c.execute("UPDATE groups SET react_enabled=? WHERE chat_id=?", (1 if on else 0, chat_id))
        c.commit()


def set_react_emoji(chat_id: int, emoji: str):
    with _c() as c:
        c.execute("UPDATE groups SET react_emoji=? WHERE chat_id=?", (emoji, chat_id))
        c.commit()


def all_groups():
    with _c() as c:
        return c.execute("SELECT * FROM groups").fetchall()


def add_warn(uid: int, cid: int, reason: str) -> int:
    with _c() as c:
        c.execute("INSERT INTO warnings (user_id,chat_id,reason) VALUES(?,?,?)", (uid, cid, reason))
        c.commit()
    return warn_count(uid, cid)


def warn_count(uid: int, cid: int) -> int:
    with _c() as c:
        r = c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
        return r[0] if r else 0


def get_warns(uid: int, cid: int):
    with _c() as c:
        return c.execute(
            "SELECT * FROM warnings WHERE user_id=? AND chat_id=? ORDER BY warned_at DESC", (uid, cid)
        ).fetchall()


def clear_warns(uid: int, cid: int):
    with _c() as c:
        c.execute("DELETE FROM warnings WHERE user_id=? AND chat_id=?", (uid, cid))
        c.commit()


def inc_stat(key: str):
    with _c() as c:
        c.execute("UPDATE stats SET val=val+1 WHERE key=?", (key,))
        c.commit()


def get_stat(key: str) -> int:
    with _c() as c:
        r = c.execute("SELECT val FROM stats WHERE key=?", (key,)).fetchone()
        return r[0] if r else 0
