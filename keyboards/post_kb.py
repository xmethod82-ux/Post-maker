"""Keyboards for the post creation wizard."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def post_content_keyboard() -> InlineKeyboardMarkup:
    """Shown while waiting for post content (lets user skip or cancel)."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌  Cancel", callback_data="dashboard"),
    ]])


def button_type_keyboard() -> InlineKeyboardMarkup:
    """Choose what kind of button to add."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗  URL Button", callback_data="btn_type:url"),
            InlineKeyboardButton(text="🌐  WebApp Button", callback_data="btn_type:webapp"),
        ],
        [
            InlineKeyboardButton(text="✅  Done — No More Buttons", callback_data="btn_done"),
        ],
        [
            InlineKeyboardButton(text="❌  Cancel", callback_data="dashboard"),
        ],
    ])


def button_style_keyboard() -> InlineKeyboardMarkup:
    """Choose button visual style."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔵  Primary", callback_data="btn_style:primary"),
            InlineKeyboardButton(text="🟢  Success", callback_data="btn_style:success"),
            InlineKeyboardButton(text="🔴  Danger",  callback_data="btn_style:danger"),
        ],
        [
            InlineKeyboardButton(text="❌  Cancel", callback_data="dashboard"),
        ],
    ])


def button_row_keyboard() -> InlineKeyboardMarkup:
    """Ask whether to place this button on the same row or a new row."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➡️  Same Row", callback_data="btn_row:same"),
            InlineKeyboardButton(text="⬇️  New Row",  callback_data="btn_row:new"),
        ],
        [
            InlineKeyboardButton(text="❌  Cancel", callback_data="dashboard"),
        ],
    ])


def button_actions_keyboard(buttons_count: int) -> InlineKeyboardMarkup:
    """Shown after a button is saved — let user add more or finish."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="➕  Add Another Button", callback_data="add_button"),
            InlineKeyboardButton(text="✅  Done", callback_data="btn_done"),
        ],
    ]
    if buttons_count > 0:
        rows.append([
            InlineKeyboardButton(
                text="🗑  Remove Last Button", callback_data="remove_last_button"
            ),
        ])
    rows.append([
        InlineKeyboardButton(text="❌  Cancel", callback_data="dashboard"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_preview_keyboard() -> InlineKeyboardMarkup:
    """Actions available from the preview screen."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤  Publish Now", callback_data="publish_post"),
        ],
        [
            InlineKeyboardButton(text="💾  Save as Draft", callback_data="save_draft"),
            InlineKeyboardButton(text="🔘  Edit Buttons", callback_data="edit_buttons"),
        ],
        [
            InlineKeyboardButton(text="❌  Discard", callback_data="discard_post"),
        ],
    ])
