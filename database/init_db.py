"""
Database schema initialisation.
Creates all tables if they do not yet exist.
"""

import logging
from .connection import get_db

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    username    TEXT,
    joined_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS channels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id   INTEGER NOT NULL,
    channel_name TEXT    NOT NULL,
    username     TEXT,
    is_active    INTEGER NOT NULL DEFAULT 0,
    connected_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, channel_id)
);

CREATE TABLE IF NOT EXISTS drafts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT    NOT NULL DEFAULT 'Draft',
    content_type TEXT    NOT NULL,
    file_id      TEXT,
    caption      TEXT,
    buttons_json TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


async def init_database() -> None:
    """Execute the schema DDL to create tables on first run."""
    db = await get_db()
    await db.executescript(_SCHEMA)
    await db.commit()
    logger.info("Database schema initialised successfully.")
