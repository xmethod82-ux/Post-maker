"""
Data-access layer for the `channels` table.
"""

import logging
from datetime import datetime
from aiosqlite import Row
from .connection import get_db
from bot.models import Channel

logger = logging.getLogger(__name__)


def _row_to_channel(row: Row) -> Channel:
    return Channel(
        id=row["id"],
        user_id=row["user_id"],
        channel_id=row["channel_id"],
        channel_name=row["channel_name"],
        username=row["username"],
        is_active=bool(row["is_active"]),
        connected_at=datetime.fromisoformat(row["connected_at"]),
    )


async def get_user_channels(user_id: int) -> list[Channel]:
    """Return all channels connected by a user, newest first."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM channels WHERE user_id = ? ORDER BY connected_at DESC",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_channel(r) for r in rows]


async def get_channel_by_id(channel_id: int, user_id: int) -> Channel | None:
    """Return a specific channel belonging to a user."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM channels WHERE channel_id = ? AND user_id = ?",
        (channel_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_channel(row) if row else None


async def get_active_channel(user_id: int) -> Channel | None:
    """Return the currently active channel for a user."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM channels WHERE user_id = ? AND is_active = 1",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_channel(row) if row else None


async def add_channel(
    user_id: int,
    channel_id: int,
    channel_name: str,
    username: str | None,
) -> Channel:
    """Insert or replace a channel record and set it as active."""
    db = await get_db()
    # Deactivate all others first
    await db.execute(
        "UPDATE channels SET is_active = 0 WHERE user_id = ?", (user_id,)
    )
    await db.execute(
        """
        INSERT INTO channels (user_id, channel_id, channel_name, username, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(user_id, channel_id) DO UPDATE SET
            channel_name = excluded.channel_name,
            username     = excluded.username,
            is_active    = 1
        """,
        (user_id, channel_id, channel_name, username),
    )
    await db.commit()
    channel = await get_channel_by_id(channel_id, user_id)
    assert channel is not None
    logger.info(
        "Channel connected: user_id=%d channel_id=%d name=%s",
        user_id, channel_id, channel_name,
    )
    return channel


async def set_active_channel(user_id: int, channel_db_id: int) -> bool:
    """Set the channel with the given DB primary key as active."""
    db = await get_db()
    await db.execute(
        "UPDATE channels SET is_active = 0 WHERE user_id = ?", (user_id,)
    )
    async with db.execute(
        "UPDATE channels SET is_active = 1 WHERE id = ? AND user_id = ? RETURNING id",
        (channel_db_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    await db.commit()
    return row is not None


async def remove_channel(user_id: int, channel_db_id: int) -> bool:
    """Delete a channel record; returns True if a row was deleted."""
    db = await get_db()
    async with db.execute(
        "DELETE FROM channels WHERE id = ? AND user_id = ? RETURNING id",
        (channel_db_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    await db.commit()
    if row:
        logger.info(
            "Channel disconnected: user_id=%d channel_db_id=%d", user_id, channel_db_id
        )
    return row is not None
