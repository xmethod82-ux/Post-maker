"""
Handlers for the draft management system:
  list drafts, view, publish, rename, delete.

Rename flow uses a dedicated FSM state (DraftRenameState) kept local to this module.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

from bot.database.channels import get_active_channel
from bot.database.posts import record_post
from bot.keyboards import (
    drafts_list_keyboard,
    draft_actions_keyboard,
    dashboard_keyboard,
    cancel_keyboard,
)
from bot.models import User, ButtonData
from bot.services import PostService, ChannelService, DraftService
from bot.utils.formatters import html_escape, content_type_emoji
from bot.utils.helpers import deserialize_buttons

logger = logging.getLogger(__name__)
router = Router()


class DraftRenameState(StatesGroup):
    waiting_name = State()


_RENAME_DRAFT_ID_KEY = "rename_draft_id"


# ────────────────────────────────────────────────────────────
#  List drafts
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "my_drafts")
async def cb_my_drafts(callback: CallbackQuery, db_user: User) -> None:
    svc = DraftService()
    drafts = await svc.list_drafts(db_user.id)

    if not drafts:
        await callback.message.edit_text(
            "📂 <b>Drafts</b>\n\nYou have no saved drafts yet.\n\n"
            "Drafts are created when you tap <b>Save as Draft</b> "
            "in the post preview.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📂 <b>My Drafts</b>  ({len(drafts)} saved)\n\nSelect a draft to view:",
        reply_markup=drafts_list_keyboard(drafts),
        parse_mode="HTML",
    )
    await callback.answer()


# ────────────────────────────────────────────────────────────
#  Open a specific draft
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("draft_open:"))
async def cb_draft_open(callback: CallbackQuery, db_user: User) -> None:
    draft_id = int(callback.data.split(":")[1])
    svc = DraftService()
    draft = await svc.get_draft(draft_id, db_user.id)

    if not draft:
        await callback.answer("Draft not found.", show_alert=True)
        return

    emoji = content_type_emoji(draft.content_type)
    btn_count = 0
    if draft.buttons_json:
        rows = deserialize_buttons(draft.buttons_json)
        btn_count = sum(len(r) for r in rows)

    caption_preview = ""
    if draft.caption:
        snippet = draft.caption[:120]
        if len(draft.caption) > 120:
            snippet += "…"
        caption_preview = f"\n\n📋 <i>{html_escape(snippet)}</i>"

    text = (
        f"{emoji} <b>{html_escape(draft.name)}</b>\n\n"
        f"Type: <b>{draft.content_type.capitalize()}</b>\n"
        f"Buttons: <b>{btn_count}</b>\n"
        f"Saved: {draft.created_at.strftime('%Y-%m-%d %H:%M')}"
        f"{caption_preview}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=draft_actions_keyboard(draft.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ────────────────────────────────────────────────────────────
#  Publish a draft
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("draft_publish:"))
async def cb_draft_publish(
    callback: CallbackQuery, db_user: User, bot: Bot
) -> None:
    draft_id = int(callback.data.split(":")[1])
    svc = DraftService()
    draft = await svc.get_draft(draft_id, db_user.id)

    if not draft:
        await callback.answer("Draft not found.", show_alert=True)
        return

    active = await get_active_channel(db_user.id)
    if not active:
        await callback.answer("No active channel!", show_alert=True)
        return

    # Permission check
    ch_svc = ChannelService(bot)
    ok, missing = await ch_svc.check_admin_status(active.channel_id)
    if not ok:
        perms = "\n".join(f"• <code>{p}</code>" for p in missing)
        await callback.message.edit_text(
            f"❌ <b>Permission check failed.</b>\n\n"
            f"Missing on <b>{html_escape(active.channel_name)}</b>:\n{perms}\n\n"
            "Restore the permissions and try again.",
            reply_markup=dashboard_keyboard(has_channel=True),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    post_svc = PostService(bot)
    try:
        sent = await post_svc.publish(
            channel_id=active.channel_id,
            content_type=draft.content_type,
            file_id=draft.file_id,
            caption=draft.caption,
            buttons_json=draft.buttons_json,
        )
        await record_post(
            user_id=db_user.id,
            channel_id=active.channel_id,
            message_id=sent.message_id,
        )
    except TelegramAPIError as exc:
        logger.error("Draft publish failed: %s", exc)
        await callback.message.edit_text(
            f"❌ <b>Publish failed.</b>\n\n<code>{html_escape(str(exc))}</code>",
            reply_markup=draft_actions_keyboard(draft.id),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Delete the draft after successful publish
    await svc.delete_draft(draft.id, db_user.id)

    await callback.message.edit_text(
        f"🎉 <b>Draft Published!</b>\n\n"
        f"<b>{html_escape(draft.name)}</b> was published to "
        f"<b>{html_escape(active.channel_name)}</b>.",
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )
    await callback.answer("✅ Published!")


# ────────────────────────────────────────────────────────────
#  Rename a draft
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("draft_rename:"))
async def cb_draft_rename(
    callback: CallbackQuery, state: FSMContext
) -> None:
    draft_id = int(callback.data.split(":")[1])
    await state.set_state(DraftRenameState.waiting_name)
    await state.update_data({_RENAME_DRAFT_ID_KEY: draft_id})

    await callback.message.answer(
        "✏️ <b>Rename Draft</b>\n\nEnter a new name for this draft:",
        reply_markup=cancel_keyboard("my_drafts"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DraftRenameState.waiting_name)
async def handle_draft_rename_input(
    message: Message, state: FSMContext, db_user: User
) -> None:
    name = (message.text or "").strip()[:80]
    if not name:
        await message.answer("❌ Name cannot be empty. Please enter a name:")
        return

    data = await state.get_data()
    draft_id: int | None = data.get(_RENAME_DRAFT_ID_KEY)
    if draft_id is None:
        await state.clear()
        await message.answer("❌ Session expired. Please try again from Drafts.")
        return

    svc = DraftService()
    draft = await svc.rename_draft(draft_id, db_user.id, name)
    await state.clear()

    if not draft:
        await message.answer(
            "❌ Draft not found.",
            reply_markup=dashboard_keyboard(has_channel=True),
        )
        return

    await message.answer(
        f"✅ Draft renamed to <b>{html_escape(draft.name)}</b>.",
        reply_markup=draft_actions_keyboard(draft.id),
        parse_mode="HTML",
    )


# ────────────────────────────────────────────────────────────
#  Delete a draft
# ────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("draft_delete:"))
async def cb_draft_delete(
    callback: CallbackQuery, db_user: User
) -> None:
    draft_id = int(callback.data.split(":")[1])
    svc = DraftService()
    removed = await svc.delete_draft(draft_id, db_user.id)

    if not removed:
        await callback.answer("Draft not found.", show_alert=True)
        return

    drafts = await svc.list_drafts(db_user.id)
    if drafts:
        await callback.message.edit_text(
            f"📂 <b>My Drafts</b>  ({len(drafts)} saved)\n\n"
            "✅ Draft deleted. Select another:",
            reply_markup=drafts_list_keyboard(drafts),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "📂 <b>Drafts</b>\n\n✅ Draft deleted. No drafts remaining.",
            reply_markup=dashboard_keyboard(has_channel=True),
            parse_mode="HTML",
        )
    await callback.answer("🗑 Deleted")
