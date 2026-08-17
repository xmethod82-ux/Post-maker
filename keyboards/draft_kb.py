"""Keyboards for draft management."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models import Draft
from bot.utils.formatters import content_type_emoji


def drafts_list_keyboard(drafts: list[Draft]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for draft in drafts:
        emoji = content_type_emoji(draft.content_type)
        label = f"{emoji}  {draft.name}"
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"draft_open:{draft.id}"),
        ])

    rows.append([
        InlineKeyboardButton(text="🏠  Dashboard", callback_data="dashboard"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def draft_actions_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤  Publish", callback_data=f"draft_publish:{draft_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="✏️  Rename", callback_data=f"draft_rename:{draft_id}"
            ),
            InlineKeyboardButton(
                text="🗑  Delete", callback_data=f"draft_delete:{draft_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙  Back to Drafts", callback_data="my_drafts"),
            InlineKeyboardButton(text="🏠  Dashboard", callback_data="dashboard"),
        ],
    ])
