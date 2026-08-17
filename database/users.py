"""
Data-access layer for the `users` table.
"""

import logging
from datetime import datetime
from aiosqlite import Row
from .connection import get_db
from bot.models import User

logger = logging.getLogger(__name__)


def _row_to_user(row: Row) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        name=row["name"],
        username=row["username"],
        joined_at=datetime.fromisoformat(row["joined_at"]),
    )


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Return a User if they have already registered; None otherwise."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def create_user(telegram_id: int, name: str, username: str | None) -> User:
    """Insert a new user row and return the created User."""
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO users (telegram_id, name, username) VALUES (?, ?, ?)",
        (telegram_id, name, username),
    )
    await db.commit()
    user = await get_user_by_telegram_id(telegram_id)
    assert user is not None
    logger.info("User registered: telegram_id=%d name=%s", telegram_id, name)
    return user


async def get_or_create_user(
    telegram_id: int, name: str, username: str | None
) -> tuple[User, bool]:
    """
    Return (user, created) — created is True if the user was just registered.
    """
    existing = await get_user_by_telegram_id(telegram_id)
    if existing:
        return existing, False
    new_user = await create_user(telegram_id, name, username)
    return new_user, True
