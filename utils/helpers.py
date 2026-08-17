"""
Shared helper functions: button (de)serialisation and keyboard building.
"""

import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.models import ButtonData, ButtonRow



def serialize_buttons(rows: list[list[ButtonData]]) -> str:
    """Convert a 2-D list of ButtonData into a JSON string for storage."""
    data = [
        [btn.model_dump() for btn in row]
        for row in rows
    ]
    return json.dumps(data, ensure_ascii=False)


def deserialize_buttons(json_str: str) -> list[list[ButtonData]]:
    """Parse a stored JSON string back into a 2-D list of ButtonData."""
    raw = json.loads(json_str)
    return [
        [ButtonData(**btn) for btn in row]
        for row in raw
    ]


def buttons_to_inline_keyboard(
    rows: list[list[ButtonData]],
    for_channel: bool = False,
) -> InlineKeyboardMarkup:
    """
    Build an aiogram InlineKeyboardMarkup from button row data.

    ``for_channel=True`` forces all buttons to plain URL buttons because
    Telegram does not allow WebApp buttons in channel posts.
    """
    keyboard: list[list[InlineKeyboardButton]] = []
    for row in rows:
        kb_row: list[InlineKeyboardButton] = []
        for btn in row:
            label = f"{btn.label} | style: {btn.style}"

            if btn.type == "webapp" and not for_channel:
                kb_row.append(
                    InlineKeyboardButton(
                        text=label,
                        web_app=WebAppInfo(url=btn.url),
                    )
                )
            else:
                # In channel posts WebApp buttons are not supported;
                # fall back to a regular URL button using the same URL.
                kb_row.append(
                    InlineKeyboardButton(
                        text=label,
                        url=btn.url,
                    )
                )
        keyboard.append(kb_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def count_buttons(rows: list[list[ButtonData]]) -> int:
    """Return the total number of buttons across all rows."""
    return sum(len(row) for row in rows)
