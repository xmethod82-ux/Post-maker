"""
Async SQLite connection manager using aiosqlite.
Provides a single shared connection instance for the process lifetime.
"""

import logging
import aiosqlite
from bot.config import settings

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the active database connection, creating it if necessary."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.DATABASE_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        logger.info("Database connection established: %s", settings.DATABASE_PATH)
    return _db


class DatabaseConnection:
    """Async context manager for the shared database connection."""

    async def __aenter__(self) -> aiosqlite.Connection:
        return await get_db()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Connection is long-lived; we commit or rollback per operation.
        if exc_type is not None:
            db = await get_db()
            await db.rollback()
        return False


async def close_db() -> None:
    """Close the database connection gracefully on shutdown."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed.")
