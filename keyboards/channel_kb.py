"""Keyboards for channel listing and management."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models import Channel


def channels_list_keyboard(
    channels: list[Channel],
    mode: str = "view",   # "view" | "switch" | "disconnect"
) -> InlineKeyboardMarkup:
    """
    Render one button per channel.
    *mode* controls the callback_data prefix.
    """
    rows: list[list[InlineKeyboardButton]] = []

    for ch in channels:
        label = ch.channel_name
        if ch.is_active:
            label = f"✅  {label}"
        if mode == "switch":
            cb = f"switch_to:{ch.id}"
        elif mode == "disconnect":
            cb = f"confirm_disconnect:{ch.id}"
        else:
            cb = f"channel_info:{ch.id}"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])

    rows.append([
        InlineKeyboardButton(text="➕  Connect New Channel", callback_data="connect_channel"),
        InlineKeyboardButton(text="🏠  Dashboard", callback_data="dashboard"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_actions_keyboard(channel: Channel) -> InlineKeyboardMarkup:
    """Actions available for a specific channel."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="✅  Set Active" if not channel.is_active else "📌  Already Active",
                callback_data=f"switch_to:{channel.id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔌  Disconnect",
                callback_data=f"confirm_disconnect:{channel.id}",
            ),
            InlineKeyboardButton(text="🔙  Back", callback_data="my_channels"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
