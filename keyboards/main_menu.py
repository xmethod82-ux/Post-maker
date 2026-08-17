"""Main dashboard and utility keyboards."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def dashboard_keyboard(has_channel: bool = True) -> InlineKeyboardMarkup:
    """Primary dashboard keyboard shown after a channel is connected."""
    buttons: list[list[InlineKeyboardButton]] = []

    if has_channel:
        buttons.append([
            InlineKeyboardButton(text="✏️  Create Post", callback_data="create_post"),
        ])
        buttons.append([
            InlineKeyboardButton(text="📂  Drafts", callback_data="my_drafts"),
            InlineKeyboardButton(text="📡  My Channels", callback_data="my_channels"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🔄  Switch Channel", callback_data="switch_channel"),
            InlineKeyboardButton(text="🔌  Disconnect", callback_data="disconnect_channel"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="➕  Connect Channel", callback_data="connect_channel"),
        ])

    buttons.append([
        InlineKeyboardButton(text="❓  Help", callback_data="help"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕  Connect My Channel", callback_data="connect_channel"),
        InlineKeyboardButton(text="❓  Help", callback_data="help"),
    ]])


def cancel_keyboard(back_cb: str = "dashboard") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌  Cancel", callback_data=back_cb),
    ]])


def confirm_keyboard(
    confirm_cb: str,
    cancel_cb: str = "dashboard",
    confirm_label: str = "✅  Confirm",
    cancel_label: str = "❌  Cancel",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=confirm_label, callback_data=confirm_cb),
        InlineKeyboardButton(text=cancel_label, callback_data=cancel_cb),
    ]])
