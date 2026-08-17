"""
Data-access layer for the `drafts` table.
"""

import logging
from datetime import datetime
from aiosqlite import Row
from .connection import get_db
from bot.models import Draft

logger = logging.getLogger(__name__)


def _row_to_draft(row: Row) -> Draft:
    return Draft(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        content_type=row["content_type"],
        file_id=row["file_id"],
        caption=row["caption"],
        buttons_json=row["buttons_json"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


async def get_user_drafts(user_id: int) -> list[Draft]:
    """Return all drafts for a user, newest first."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM drafts WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_draft(r) for r in rows]


async def get_draft_by_id(draft_id: int, user_id: int) -> Draft | None:
    """Return a specific draft belonging to a user."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM drafts WHERE id = ? AND user_id = ?",
        (draft_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_draft(row) if row else None


async def create_draft(
    user_id: int,
    content_type: str,
    file_id: str | None,
    caption: str | None,
    buttons_json: str | None,
    name: str = "Draft",
) -> Draft:
    """Create a new draft and return it."""
    db = await get_db()
    async with db.execute(
        """
        INSERT INTO drafts (user_id, name, content_type, file_id, caption, buttons_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, content_type, file_id, caption, buttons_json),
    ) as cursor:
        draft_id = cursor.lastrowid
    await db.commit()
    draft = await get_draft_by_id(draft_id, user_id)
    assert draft is not None
    logger.info("Draft created: id=%d user_id=%d", draft_id, user_id)
    return draft


async def update_draft(
    draft_id: int,
    user_id: int,
    content_type: str | None = None,
    file_id: str | None = None,
    caption: str | None = None,
    buttons_json: str | None = None,
    name: str | None = None,
) -> Draft | None:
    """Update an existing draft's fields; returns the updated draft or None if not found."""
    db = await get_db()
    fields: list[str] = []
    values: list = []

    if content_type is not None:
        fields.append("content_type = ?")
        values.append(content_type)
    if file_id is not None:
        fields.append("file_id = ?")
        values.append(file_id)
    if caption is not None:
        fields.append("caption = ?")
        values.append(caption)
    if buttons_json is not None:
        fields.append("buttons_json = ?")
        values.append(buttons_json)
    if name is not None:
        fields.append("name = ?")
        values.append(name)

    if not fields:
        return await get_draft_by_id(draft_id, user_id)

    values.extend([draft_id, user_id])
    await db.execute(
        f"UPDATE drafts SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
        values,
    )
    await db.commit()
    return await get_draft_by_id(draft_id, user_id)


async def delete_draft(draft_id: int, user_id: int) -> bool:
    """Delete a draft; returns True if a row was removed."""
    db = await get_db()
    async with db.execute(
        "DELETE FROM drafts WHERE id = ? AND user_id = ? RETURNING id",
        (draft_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()
    await db.commit()
    if row:
        logger.info("Draft deleted: id=%d user_id=%d", draft_id, user_id)
    return row is not None
