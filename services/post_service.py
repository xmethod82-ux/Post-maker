"""
Business logic for publishing posts to Telegram channels.
"""

import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from bot.models import ButtonData
from bot.utils.helpers import buttons_to_inline_keyboard, deserialize_buttons

logger = logging.getLogger(__name__)

# Mapping from content_type to the Bot method name
_SEND_METHODS: dict[str, str] = {
    "text":      "send_message",
    "photo":     "send_photo",
    "video":     "send_video",
    "animation": "send_animation",
    "audio":     "send_audio",
    "voice":     "send_voice",
    "document":  "send_document",
    "sticker":   "send_sticker",
}


class PostService:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def publish(
        self,
        channel_id: int,
        content_type: str,
        file_id: str | None,
        caption: str | None,
        buttons_json: str | None,
    ) -> Message:
        """
        Publish a post to *channel_id*.
        Returns the sent Message on success; raises TelegramAPIError on failure.
        """
        reply_markup = None
        if buttons_json:
            rows = deserialize_buttons(buttons_json)
            if rows:
                reply_markup = buttons_to_inline_keyboard(rows, for_channel=True)

        method_name = _SEND_METHODS.get(content_type, "send_message")
        method = getattr(self._bot, method_name)

        kwargs: dict = {"chat_id": channel_id}

        if content_type == "text":
            kwargs["text"] = caption or " "
            kwargs["parse_mode"] = "HTML"
        elif content_type == "sticker":
            kwargs["sticker"] = file_id
        else:
            # All media types use a file_id key matching their type
            media_key = content_type  # "photo", "video", etc.
            kwargs[media_key] = file_id
            if caption:
                kwargs["caption"] = caption
                kwargs["parse_mode"] = "HTML"

        if reply_markup and content_type != "sticker":
            kwargs["reply_markup"] = reply_markup

        logger.info(
            "Publishing to channel_id=%d content_type=%s", channel_id, content_type
        )
        return await method(**kwargs)

    async def forward_preview(
        self,
        target_chat_id: int,
        content_type: str,
        file_id: str | None,
        caption: str | None,
        buttons_json: str | None,
    ) -> Message | None:
        """
        Send a preview copy to the user's private chat (not the channel).
        Returns the Message or None if sending failed.
        """
        try:
            return await self.publish(
                channel_id=target_chat_id,
                content_type=content_type,
                file_id=file_id,
                caption=caption,
                buttons_json=buttons_json,
            )
        except TelegramAPIError as exc:
            logger.warning("Preview delivery failed: %s", exc)
            return None
