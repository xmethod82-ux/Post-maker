"""
Handlers for all channel-related flows:
  /connect, connect_channel callback, my_channels, switch_to, disconnect.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database.channels import (
    get_user_channels,
    get_channel_by_id,
    set_active_channel,
    remove_channel,
    get_active_channel,
)
from bot.keyboards import (
    cancel_keyboard,
    confirm_keyboard,
    channels_list_keyboard,
    channel_actions_keyboard,
    dashboard_keyboard,
)
from bot.models import User
from bot.services import ChannelService
from bot.states import ChannelStates
from bot.utils.validators import is_valid_channel_input, parse_channel_input
from bot.utils.formatters import format_channel_status, html_escape

logger = logging.getLogger(__name__)
router = Router()


# ────────────────────────────────────────────────────────────
#  Connect a new channel
# ────────────────────────────────────────────────────────────


async def _prompt_channel_input(target: Message | CallbackQuery, state: FSMContext) -> None:
    text = (
        "📡 <b>Connect a Channel</b>\n\n"
        "Send me the channel's <b>@username</b> or its <b>numeric ID</b> "
        "(e.g. <code>-1001234567890</code>).\n\n"
        "⚠️ Make sure the bot is already added as an <b>Administrator</b> "
        "with all required permissions."
    )
    await state.set_state(ChannelStates.waiting_channel_input)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(
            text,
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await target.answer()
    else:
        await target.answer(
            text,
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )


@router.message(Command("connect"))
async def cmd_connect(
    message: Message, state: FSMContext, bot: Bot, db_user: User
) -> None:
    """
    /connect @username  or  /connect -100xxxxxxx
    If an argument is given, run the full connection flow immediately.
    Otherwise prompt the user for input.
    """
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        identifier = args[1].strip()
        if not is_valid_channel_input(identifier):
            await message.answer(
                "❌ Invalid channel identifier.\n\n"
                "Use <code>@username</code> or a numeric ID like "
                "<code>-1001234567890</code>.",
                parse_mode="HTML",
            )
            return
        await _do_connect(message, db_user, bot, identifier)
    else:
        await _prompt_channel_input(message, state)


@router.callback_query(F.data == "connect_channel")
async def cb_connect_channel(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await _prompt_channel_input(callback, state)


@router.message(ChannelStates.waiting_channel_input)
async def handle_channel_input(
    message: Message, state: FSMContext, bot: Bot, db_user: User
) -> None:
    text = message.text.strip() if message.text else ""

    if not is_valid_channel_input(text):
        await message.answer(
            "❌ That doesn't look like a valid channel identifier.\n\n"
            "Send <code>@username</code> or a numeric ID like "
            "<code>-1001234567890</code>.",
            parse_mode="HTML",
        )
        return

    await state.clear()
    await _do_connect(message, db_user, bot, text)


async def _do_connect(
    message: Message,
    db_user: User,
    bot: Bot,
    raw_input: str,
) -> None:
    """Run the full 5-step channel verification and save flow."""
    username, channel_id_int = parse_channel_input(raw_input)

    status_msg = await message.answer(
        "🔍 Verifying channel…", parse_mode="HTML"
    )

    service = ChannelService(bot)
    result = await service.connect_channel(
        user_id=db_user.id,
        identifier=username,
        channel_id_int=channel_id_int,
    )

    if not result.success:
        await status_msg.edit_text(result.error, parse_mode="HTML")
        return

    ch = result.channel
    success_text = (
        f"✅ <b>Channel connected successfully!</b>\n\n"
        f"{format_channel_status(ch)}\n\n"
        "This channel is now your <b>Active</b> channel."
    )
    await status_msg.edit_text(
        success_text,
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )


# ────────────────────────────────────────────────────────────
#  My Channels list
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "my_channels")
async def cb_my_channels(
    callback: CallbackQuery, db_user: User
) -> None:
    channels = await get_user_channels(db_user.id)

    if not channels:
        await callback.message.edit_text(
            "📡 <b>My Channels</b>\n\nYou have no connected channels yet.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = f"📡 <b>My Channels</b>  ({len(channels)} connected)\n\nSelect a channel:"
    await callback.message.edit_text(
        text,
        reply_markup=channels_list_keyboard(channels),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel_info:"))
async def cb_channel_info(
    callback: CallbackQuery, db_user: User
) -> None:
    channel_db_id = int(callback.data.split(":")[1])
    channels = await get_user_channels(db_user.id)
    channel = next((c for c in channels if c.id == channel_db_id), None)

    if not channel:
        await callback.answer("Channel not found.", show_alert=True)
        return

    text = (
        f"📢 <b>Channel Details</b>\n\n"
        f"{format_channel_status(channel)}\n\n"
        f"🆔 ID: <code>{channel.channel_id}</code>\n"
        f"📅 Connected: {channel.connected_at.strftime('%Y-%m-%d %H:%M')}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=channel_actions_keyboard(channel),
        parse_mode="HTML",
    )
    await callback.answer()


# ────────────────────────────────────────────────────────────
#  Switch active channel
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "switch_channel")
async def cb_switch_channel(
    callback: CallbackQuery, db_user: User
) -> None:
    channels = await get_user_channels(db_user.id)

    if not channels:
        await callback.answer("No channels connected.", show_alert=True)
        return

    await callback.message.edit_text(
        "🔄 <b>Switch Active Channel</b>\n\nChoose a channel to activate:",
        reply_markup=channels_list_keyboard(channels, mode="switch"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("switch_to:"))
async def cb_switch_to(
    callback: CallbackQuery, db_user: User
) -> None:
    channel_db_id = int(callback.data.split(":")[1])
    ok = await set_active_channel(db_user.id, channel_db_id)

    if not ok:
        await callback.answer("Channel not found.", show_alert=True)
        return

    channels = await get_user_channels(db_user.id)
    active = next((c for c in channels if c.id == channel_db_id), None)
    name = active.channel_name if active else "channel"

    await callback.answer(f"✅ Switched to {name}", show_alert=False)

    # Re-render dashboard
    active_channel = await get_active_channel(db_user.id)
    text = (
        f"🏠 <b>Dashboard</b>\n\n"
        f"Active channel:\n{format_channel_status(active_channel)}\n\n"
        f"What would you like to do?"
    )
    await callback.message.edit_text(
        text,
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )


# ────────────────────────────────────────────────────────────
#  Disconnect a channel
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "disconnect_channel")
async def cb_disconnect_channel(
    callback: CallbackQuery, db_user: User
) -> None:
    active = await get_active_channel(db_user.id)
    if not active:
        await callback.answer("No active channel.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ <b>Disconnect Channel</b>\n\n"
        f"Are you sure you want to disconnect:\n"
        f"{format_channel_status(active)}\n\n"
        f"This will not affect the channel itself.",
        reply_markup=confirm_keyboard(
            confirm_cb=f"confirm_disconnect:{active.id}",
            confirm_label="🔌  Yes, Disconnect",
            cancel_label="❌  Cancel",
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_disconnect:"))
async def cb_confirm_disconnect(
    callback: CallbackQuery, db_user: User
) -> None:
    channel_db_id = int(callback.data.split(":")[1])
    channels = await get_user_channels(db_user.id)
    target = next((c for c in channels if c.id == channel_db_id), None)
    name = target.channel_name if target else "channel"

    removed = await remove_channel(db_user.id, channel_db_id)

    if not removed:
        await callback.answer("Channel not found.", show_alert=True)
        return

    # Check if any channel remains and pick a new active
    remaining = await get_user_channels(db_user.id)
    has_channel = len(remaining) > 0
    if has_channel:
        await set_active_channel(db_user.id, remaining[0].id)

    await callback.message.edit_text(
        f"🔌 <b>{html_escape(name)}</b> has been disconnected.\n\n"
        + (
            "Your first remaining channel is now active."
            if has_channel
            else "You have no channels connected. Connect one to continue."
        ),
        reply_markup=dashboard_keyboard(has_channel=has_channel),
        parse_mode="HTML",
    )
    await callback.answer()
