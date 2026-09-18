import aiosqlite
from bot.core.config import DB_PATH

# Columns that may be missing on a database created by an older version
# of this bot (SQLite's CREATE TABLE IF NOT EXISTS does not add new
# columns to an existing table, so upgrades need a small migration).
_MIGRATION_COLUMNS = [
    ("group_settings", "reaction_enabled", "INTEGER DEFAULT 0"),
    ("group_settings", "reaction_emoji", "TEXT DEFAULT '👍'"),
]

async def _run_migrations(db: aiosqlite.Connection):
    for table, column, coltype in _MIGRATION_COLUMNS:
        async with db.execute(f"PRAGMA table_info({table})") as cur:
            existing = {row[1] async for row in cur}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
    await db.commit()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                antilink INTEGER DEFAULT 0,
                antilink_action TEXT DEFAULT 'delete',
                antiword INTEGER DEFAULT 0,
                antispam INTEGER DEFAULT 0,
                antispam_limit INTEGER DEFAULT 5,
                antispam_window INTEGER DEFAULT 10,
                antifake INTEGER DEFAULT 0,
                antifake_mode TEXT DEFAULT 'blacklist',
                welcome INTEGER DEFAULT 1,
                welcome_msg TEXT DEFAULT 'Welcome {name} to {group}!',
                goodbye INTEGER DEFAULT 1,
                goodbye_msg TEXT DEFAULT 'Goodbye {name}!',
                warn_limit INTEGER DEFAULT 3,
                warn_action TEXT DEFAULT 'kick',
                mute_on_join INTEGER DEFAULT 0,
                antiword_action TEXT DEFAULT 'delete',
                reaction_enabled INTEGER DEFAULT 0,
                reaction_emoji TEXT DEFAULT '👍'
            );
            CREATE TABLE IF NOT EXISTS banned_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                word TEXT,
                UNIQUE(chat_id, word)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS spam_tracker (
                user_id INTEGER,
                chat_id INTEGER,
                count INTEGER DEFAULT 0,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            );
            CREATE TABLE IF NOT EXISTS whitelisted_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                link TEXT,
                UNIQUE(chat_id, link)
            );
            CREATE TABLE IF NOT EXISTS antifake_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                prefix TEXT,
                UNIQUE(chat_id, prefix)
            );
            CREATE TABLE IF NOT EXISTS custom_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                keyword TEXT,
                reply TEXT,
                UNIQUE(chat_id, keyword)
            );
            CREATE TABLE IF NOT EXISTS muted_users (
                chat_id INTEGER,
                user_id INTEGER,
                muted_until TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        await db.commit()
        await _run_migrations(db)

async def get_settings(chat_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM group_settings WHERE chat_id=?", (chat_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
            await db.commit()
            async with db.execute("SELECT * FROM group_settings WHERE chat_id=?", (chat_id,)) as cur2:
                return dict(await cur2.fetchone())

async def update_setting(chat_id: int, key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO group_settings (chat_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(chat_id) DO UPDATE SET {key}=excluded.{key}",
            (chat_id, value)
        )
        await db.commit()

async def get_warnings(chat_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM warnings WHERE chat_id=? AND user_id=? ORDER BY created_at DESC",
            (chat_id, user_id)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def add_warning(chat_id: int, user_id: int, reason: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (chat_id, user_id, reason) VALUES (?, ?, ?)",
            (chat_id, user_id, reason)
        )
        await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ) as cur:
            return (await cur.fetchone())[0]

async def reset_warnings(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        await db.commit()

async def get_banned_words(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT word FROM banned_words WHERE chat_id=?", (chat_id,)) as cur:
            return [r[0] for r in await cur.fetchall()]

async def add_banned_word(chat_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO banned_words (chat_id, word) VALUES (?, ?)", (chat_id, word.lower()))
        await db.commit()

async def remove_banned_word(chat_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM banned_words WHERE chat_id=? AND word=?", (chat_id, word.lower()))
        await db.commit()

async def get_whitelisted_links(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT link FROM whitelisted_links WHERE chat_id=?", (chat_id,)) as cur:
            return [r[0] for r in await cur.fetchall()]

async def add_whitelist_link(chat_id: int, link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO whitelisted_links (chat_id, link) VALUES (?, ?)", (chat_id, link))
        await db.commit()

async def remove_whitelist_link(chat_id: int, link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelisted_links WHERE chat_id=? AND link=?", (chat_id, link))
        await db.commit()

async def get_spam_count(chat_id: int, user_id: int, window: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count, window_start FROM spam_tracker WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return 0
            import datetime
            ws = datetime.datetime.fromisoformat(row[1])
            if (datetime.datetime.now() - ws).seconds > window:
                await db.execute(
                    "UPDATE spam_tracker SET count=1, window_start=CURRENT_TIMESTAMP WHERE chat_id=? AND user_id=?",
                    (chat_id, user_id)
                )
                await db.commit()
                return 1
            return row[0]

async def increment_spam(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO spam_tracker (chat_id, user_id, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, chat_id) DO UPDATE SET count=count+1",
            (chat_id, user_id)
        )
        await db.commit()
        async with db.execute(
            "SELECT count FROM spam_tracker WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        ) as cur:
            return (await cur.fetchone())[0]

async def reset_spam(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM spam_tracker WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        await db.commit()

async def get_filters(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT keyword, reply FROM custom_filters WHERE chat_id=?", (chat_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def add_filter(chat_id: int, keyword: str, reply: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO custom_filters (chat_id, keyword, reply) VALUES (?, ?, ?)",
            (chat_id, keyword.lower(), reply)
        )
        await db.commit()

async def remove_filter(chat_id: int, keyword: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM custom_filters WHERE chat_id=? AND keyword=?", (chat_id, keyword.lower()))
        await db.commit()

async def get_antifake_prefixes(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT prefix FROM antifake_numbers WHERE chat_id=?", (chat_id,)) as cur:
            return [r[0] for r in await cur.fetchall()]

async def add_antifake_prefix(chat_id: int, prefix: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO antifake_numbers (chat_id, prefix) VALUES (?, ?)", (chat_id, prefix))
        await db.commit()

async def remove_antifake_prefix(chat_id: int, prefix: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM antifake_numbers WHERE chat_id=? AND prefix=?", (chat_id, prefix))
        await db.commit()
