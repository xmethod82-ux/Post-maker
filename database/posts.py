"""
Data-access layer for the `posts` table.
"""

import logging
from datetime import datetime
from aiosqlite import Row
from .connection import get_db
from bot.models import Post

logger = logging.getLogger(__name__)


def _row_to_post(row: Row) -> Post:
    return Post(
        id=row["id"],
        user_id=row["user_id"],
        channel_id=row["channel_id"],
        message_id=row["message_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


async def record_post(
    user_id: int,
    channel_id: int,
    message_id: int,
) -> Post:
    """Save a published post record and return it."""
    db = await get_db()
    async with db.execute(
        "INSERT INTO posts (user_id, channel_id, message_id) VALUES (?, ?, ?)",
        (user_id, channel_id, message_id),
    ) as cursor:
        post_id = cursor.lastrowid
    await db.commit()
    db2 = await get_db()
    async with db2.execute("SELECT * FROM posts WHERE id = ?", (post_id,)) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    logger.info(
        "Post recorded: id=%d user_id=%d channel_id=%d message_id=%d",
        post_id, user_id, channel_id, message_id,
    )
    return _row_to_post(row)


async def get_user_posts(user_id: int, limit: int = 20) -> list[Post]:
    """Return recent posts by a user."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_post(r) for r in rows]
