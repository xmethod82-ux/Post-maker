"""
Business logic for channel connection and permission verification.
"""

import logging
from dataclasses import dataclass
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from bot.database.channels import add_channel, get_active_channel
from bot.models import Channel

logger = logging.getLogger(__name__)

REQUIRED_PERMISSIONS = (
    "can_post_messages",
    "can_edit_messages",
    "can_delete_messages",
    "can_manage_chat",
)


@dataclass
class ChannelVerificationResult:
    success: bool
    channel: Channel | None = None
    error: str | None = None


class ChannelService:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def connect_channel(
        self,
        user_id: int,
        identifier: str | None,
        channel_id_int: int | None,
    ) -> ChannelVerificationResult:
        """
        Verify the bot is an admin with required permissions and save the channel.

        *identifier*: @username string (public channels)
        *channel_id_int*: numeric -100xxxxxxxx (any channel)
        """
        # --- Step 1: Resolve chat ---
        try:
            if identifier:
                chat = await self._bot.get_chat(identifier)
            else:
                chat = await self._bot.get_chat(channel_id_int)
        except TelegramAPIError as exc:
            logger.warning("get_chat failed: %s", exc)
            return ChannelVerificationResult(
                success=False,
                error=(
                    "❌ <b>Channel not found.</b>\n\n"
                    "Please check the username or ID and try again."
                ),
            )

        if chat.type not in ("channel", "supergroup"):
            return ChannelVerificationResult(
                success=False,
                error=(
                    "❌ <b>Not a channel.</b>\n\n"
                    "Only Telegram channels (and supergroups) are supported."
                ),
            )

        # --- Step 2: Verify bot is admin ---
        try:
            bot_info = await self._bot.get_me()
            member = await self._bot.get_chat_member(chat.id, bot_info.id)
        except TelegramAPIError as exc:
            logger.warning("get_chat_member failed: %s", exc)
            return ChannelVerificationResult(
                success=False,
                error=(
                    "❌ <b>Could not check bot membership.</b>\n\n"
                    "Make sure the bot is added as an administrator to the channel."
                ),
            )

        if member.status not in ("administrator", "creator"):
            return ChannelVerificationResult(
                success=False,
                error=(
                    "❌ <b>Bot is not an administrator.</b>\n\n"
                    "Please add the bot as an admin to your channel first,\n"
                    "then try connecting again."
                ),
            )

        # --- Step 3: Verify required permissions ---
        missing: list[str] = []
        for perm in REQUIRED_PERMISSIONS:
            if not getattr(member, perm, False):
                missing.append(f"• <code>{perm}</code>")

        if missing:
            perm_list = "\n".join(missing)
            return ChannelVerificationResult(
                success=False,
                error=(
                    f"❌ <b>Missing bot permissions:</b>\n\n{perm_list}\n\n"
                    "Please grant all required permissions and try again."
                ),
            )

        # --- Step 4: Save channel ---
        username = chat.username  # None for private channels
        channel = await add_channel(
            user_id=user_id,
            channel_id=chat.id,
            channel_name=chat.title or str(chat.id),
            username=username,
        )
        logger.info(
            "Channel verified and saved: user_id=%d channel=%d name=%s",
            user_id,
            chat.id,
            chat.title,
        )
        return ChannelVerificationResult(success=True, channel=channel)

    async def check_admin_status(
        self, channel_id: int
    ) -> tuple[bool, list[str]]:
        """
        Re-check that the bot is still an admin with all required permissions.
        Returns (ok, missing_permissions).
        """
        try:
            bot_info = await self._bot.get_me()
            member = await self._bot.get_chat_member(channel_id, bot_info.id)
        except TelegramAPIError:
            return False, list(REQUIRED_PERMISSIONS)

        if member.status not in ("administrator", "creator"):
            return False, list(REQUIRED_PERMISSIONS)

        missing = [p for p in REQUIRED_PERMISSIONS if not getattr(member, p, False)]
        return len(missing) == 0, missing
