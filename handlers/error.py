"""
Global error handler — catches all unhandled exceptions and logs them.
"""

import logging
from aiogram import Router
from aiogram.types import Update, ErrorEvent
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)
router = Router()


@router.errors()
async def global_error_handler(event: ErrorEvent) -> None:
    """
    Catch-all handler for any exception that bubbles out of a handler
    or middleware.  Logs the full traceback and tries to inform the user.
    """
    exc = event.exception
    update: Update = event.update

    if isinstance(exc, TelegramAPIError):
        # Telegram API errors are usually transient — log at WARNING level.
        logger.warning(
            "TelegramAPIError in update %s: %s",
            update.update_id,
            exc,
        )
    else:
        logger.exception(
            "Unhandled exception in update %s",
            update.update_id,
            exc_info=exc,
        )

    # Try to send a friendly error message back to the user.
    try:
        if update.message:
            await update.message.answer(
                "⚠️ An unexpected error occurred. Please try again or use /start.",
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "⚠️ Something went wrong. Please try again.",
                show_alert=True,
            )
    except Exception:
        # If we can't notify the user, at least don't crash the error handler.
        pass
