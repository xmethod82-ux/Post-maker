"""
Handlers for /start, /help, and the main dashboard callback.
"""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database.channels import get_active_channel
from bot.keyboards import dashboard_keyboard, welcome_keyboard
from bot.models import User
from bot.utils.formatters import html_escape, format_channel_status

logger = logging.getLogger(__name__)
router = Router()

_WELCOME_TEXT = (
    "👋 <b>Welcome to Post Maker Bot!</b>\n\n"
    "I help you create and publish beautiful posts to your Telegram channels "
    "with rich media, custom buttons, and a live preview before you publish.\n\n"
    "✨ <b>What you can do:</b>\n"
    "• Connect unlimited channels\n"
    "• Build posts with text, photos, videos, audio, and more\n"
    "• Add clickable URL and WebApp buttons\n"
    "• Preview before publishing\n"
    "• Save drafts and resume anytime\n\n"
    "👇 Get started by connecting your channel:"
)

_HELP_TEXT = (
    "📖 <b>Post Maker Bot — Help</b>\n\n"
    "<b>Commands:</b>\n"
    "• /start — Open the dashboard\n"
    "• /connect @channel — Quick-connect a channel\n"
    "• /help — Show this message\n\n"
    "<b>How to connect a channel:</b>\n"
    "1. Add this bot as an <b>Administrator</b> to your channel.\n"
    "2. Grant these permissions:\n"
    "   – Post messages\n"
    "   – Edit messages\n"
    "   – Delete messages\n"
    "   – Manage chat\n"
    "3. Use /connect @yourchannel or tap <b>Connect Channel</b>.\n\n"
    "<b>Creating a post:</b>\n"
    "1. Select a connected channel (it becomes Active).\n"
    "2. Tap <b>Create Post</b> and send any supported content:\n"
    "   Text • Photo • Video • Animation • Audio • Voice • Document • Sticker\n"
    "3. Add optional buttons, then preview and publish.\n\n"
    "<b>Drafts:</b>\n"
    "Posts are auto-saved as drafts. Resume, rename, or delete them anytime."
)


async def _send_dashboard(
    target: Message | CallbackQuery,
    user: User,
    state: FSMContext,
) -> None:
    """Render the dashboard in the appropriate context."""
    await state.clear()

    # Resolve underlying Message for both cases
    if isinstance(target, CallbackQuery):
        msg = target.message
        answer = target.answer
    else:
        msg = target
        answer = None

    active_channel = await get_active_channel(user.id)

    if active_channel:
        text = (
            f"🏠 <b>Dashboard</b>\n\n"
            f"Active channel:\n{format_channel_status(active_channel)}\n\n"
            f"What would you like to do?"
        )
    else:
        text = (
            "🏠 <b>Dashboard</b>\n\n"
            "⚠️ No channel connected yet.\n\n"
            "Connect a channel to start creating posts."
        )

    kb = dashboard_keyboard(has_channel=active_channel is not None)

    if isinstance(target, CallbackQuery) and msg:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await answer()
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User) -> None:
    await state.clear()
    active_channel = await get_active_channel(db_user.id)

    if active_channel:
        await _send_dashboard(message, db_user, state)
    else:
        await message.answer(
            _WELCOME_TEXT,
            reply_markup=welcome_keyboard(),
            parse_mode="HTML",
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_HELP_TEXT, parse_mode="HTML")


@router.callback_query(F.data == "dashboard")
async def cb_dashboard(
    callback: CallbackQuery, state: FSMContext, db_user: User
) -> None:
    await _send_dashboard(callback, db_user, state)


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(_HELP_TEXT, parse_mode="HTML")
    await callback.answer()
