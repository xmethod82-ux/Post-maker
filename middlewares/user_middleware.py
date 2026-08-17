"""
Middleware that auto-registers every user on their first interaction
and injects `db_user` into handler data for convenience.
"""

import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from bot.database.users import get_or_create_user

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    """
    Runs before every update.

    • Silently creates a DB user record on first encounter.
    • Injects ``data["db_user"]`` so handlers can skip the lookup.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")

        if tg_user and not tg_user.is_bot:
            full_name = tg_user.full_name or tg_user.first_name or "User"
            db_user, created = await get_or_create_user(
                telegram_id=tg_user.id,
                name=full_name,
                username=tg_user.username,
            )
            data["db_user"] = db_user
            if created:
                logger.info(
                    "New user registered via middleware: telegram_id=%d name=%s",
                    tg_user.id,
                    full_name,
                )
        else:
            data["db_user"] = None

        return await handler(event, data)
