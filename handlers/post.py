"""
Handlers for the full post creation wizard:
  content → buttons → preview → publish.

Session data stored in FSM storage (key: "post_session"):
{
    "content_type": str,
    "file_id": str | None,
    "caption": str | None,
    "buttons": list[list[dict]],   # serialisable ButtonData rows
    "current_button": dict | None, # button being assembled
}
"""

import logging
import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

from bot.database.channels import get_active_channel
from bot.database.posts import record_post
from bot.keyboards import (
    post_content_keyboard,
    button_type_keyboard,
    button_style_keyboard,
    button_row_keyboard,
    button_actions_keyboard,
    post_preview_keyboard,
    cancel_keyboard,
    dashboard_keyboard,
)
from bot.models import User, ButtonData
from bot.services import ChannelService, PostService, DraftService
from bot.states import PostStates
from bot.utils.validators import is_valid_url
from bot.utils.formatters import (
    format_post_preview_caption,
    html_escape,
    content_type_emoji,
)
from bot.utils.helpers import (
    serialize_buttons,
    deserialize_buttons,
    buttons_to_inline_keyboard,
    count_buttons,
)

logger = logging.getLogger(__name__)
router = Router()

_SESSION_KEY = "post_session"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────


async def _get_session(state: FSMContext) -> dict:
    data = await state.get_data()
    return data.get(_SESSION_KEY, {
        "content_type": None,
        "file_id": None,
        "caption": None,
        "buttons": [],
        "current_button": None,
    })


async def _save_session(state: FSMContext, session: dict) -> None:
    await state.update_data({_SESSION_KEY: session})


def _detect_content_type(message: Message) -> tuple[str | None, str | None]:
    """Return (content_type, file_id) for a media message."""
    if message.text:
        return "text", None
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.video:
        return "video", message.video.file_id
    if message.animation:
        return "animation", message.animation.file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.voice:
        return "voice", message.voice.file_id
    if message.document:
        return "document", message.document.file_id
    if message.sticker:
        return "sticker", message.sticker.file_id
    return None, None


# ─────────────────────────────────────────────
#  Step 1 — Start wizard / receive content
# ─────────────────────────────────────────────


@router.callback_query(F.data == "create_post")
async def cb_create_post(
    callback: CallbackQuery, state: FSMContext, db_user: User
) -> None:
    active = await get_active_channel(db_user.id)
    if not active:
        await callback.answer("No active channel. Connect one first.", show_alert=True)
        return

    await state.set_state(PostStates.waiting_content)
    await _save_session(state, {
        "content_type": None,
        "file_id": None,
        "caption": None,
        "buttons": [],
        "current_button": None,
    })

    await callback.message.edit_text(
        f"✏️ <b>Create Post</b>\n\n"
        f"📢 Channel: <b>{html_escape(active.channel_name)}</b>\n\n"
        "Send me your post content:\n"
        "• <b>Text</b> — type your message\n"
        "• <b>Photo / Video / Animation</b> — send media with optional caption\n"
        "• <b>Audio / Voice / Document / Sticker</b> — send the file\n\n"
        "📝 <i>Captions support basic HTML formatting.</i>",
        reply_markup=post_content_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PostStates.waiting_content)
async def handle_post_content(
    message: Message, state: FSMContext
) -> None:
    content_type, file_id = _detect_content_type(message)

    if content_type is None:
        await message.answer(
            "❌ Unsupported content type. Please send text, photo, video, "
            "animation, audio, voice, document, or sticker.",
        )
        return

    caption = (
        message.caption
        if message.caption
        else (message.text if content_type == "text" else None)
    )

    session = await _get_session(state)
    session.update({
        "content_type": content_type,
        "file_id": file_id,
        "caption": caption,
        "buttons": [],
        "current_button": None,
    })
    await _save_session(state, session)

    emoji = content_type_emoji(content_type)
    await message.answer(
        f"✅ {emoji} <b>{content_type.capitalize()}</b> received!\n\n"
        "Would you like to add <b>inline buttons</b> to your post?",
        reply_markup=button_type_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(PostStates.waiting_button_type)


# ─────────────────────────────────────────────
#  Step 2 — Button builder
# ─────────────────────────────────────────────


@router.callback_query(PostStates.waiting_button_type, F.data.startswith("btn_type:"))
async def cb_button_type(callback: CallbackQuery, state: FSMContext) -> None:
    btn_type = callback.data.split(":")[1]  # url | webapp
    session = await _get_session(state)
    session["current_button"] = {"type": btn_type}
    await _save_session(state, session)

    await state.set_state(PostStates.waiting_button_url)

    if btn_type == "webapp":
        notice = (
            "\n\n⚠️ <b>Note:</b> Telegram does not support WebApp buttons "
            "in channel posts. This button will be sent as a regular URL button "
            "(opens in browser) when published to your channel."
        )
        url_label = "WebApp URL"
    else:
        notice = ""
        url_label = "URL"

    await callback.message.edit_text(
        f"🔗 <b>Enter the {url_label}</b>\n\n"
        "Must start with <code>https://</code> or <code>http://</code>"
        f"{notice}",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PostStates.waiting_button_url)
async def handle_button_url(message: Message, state: FSMContext) -> None:
    url = (message.text or "").strip()

    if not is_valid_url(url):
        await message.answer(
            "❌ Invalid URL. Please enter a URL starting with "
            "<code>https://</code> or <code>http://</code>.",
            parse_mode="HTML",
        )
        return

    session = await _get_session(state)
    session["current_button"]["url"] = url
    await _save_session(state, session)

    await state.set_state(PostStates.waiting_button_style)
    await message.answer(
        "🎨 <b>Choose a button style:</b>",
        reply_markup=button_style_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(PostStates.waiting_button_style, F.data.startswith("btn_style:"))
async def cb_button_style(callback: CallbackQuery, state: FSMContext) -> None:
    style = callback.data.split(":")[1]  # primary | success | danger
    session = await _get_session(state)
    session["current_button"]["style"] = style
    await _save_session(state, session)

    await state.set_state(PostStates.waiting_button_label)
    await callback.message.edit_text(
        "✏️ <b>Enter the button label</b>\n\n"
        "This is the text shown on the button (max 64 characters).",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PostStates.waiting_button_label)
async def handle_button_label(message: Message, state: FSMContext) -> None:
    label = (message.text or "").strip()[:64]

    if not label:
        await message.answer("❌ Label cannot be empty. Please enter a button label.")
        return

    session = await _get_session(state)
    session["current_button"]["label"] = label
    await _save_session(state, session)

    existing_buttons = session.get("buttons", [])
    total = count_buttons([[ButtonData(**b) for b in row] for row in existing_buttons])

    # If no buttons yet, no row placement question — start a new row automatically
    if total == 0:
        await _save_button_to_session(state, session, placement="new")
        await _show_button_actions(message, state)
    else:
        await state.set_state(PostStates.waiting_button_row)
        await message.answer(
            f"📐 <b>Button placement</b>\n\n"
            f"Label: <b>{html_escape(label)}</b>\n\n"
            "Add this button to the same row as the previous one, "
            "or start a new row?",
            reply_markup=button_row_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(PostStates.waiting_button_row, F.data.startswith("btn_row:"))
async def cb_button_row(callback: CallbackQuery, state: FSMContext) -> None:
    placement = callback.data.split(":")[1]  # same | new
    session = await _get_session(state)
    await _save_button_to_session(state, session, placement)
    await callback.answer()
    await _show_button_actions(callback.message, state)


async def _save_button_to_session(
    state: FSMContext, session: dict, placement: str
) -> None:
    current = session.get("current_button", {})
    try:
        btn = ButtonData(**current)
    except Exception as exc:
        logger.error("Invalid button data: %s — %s", current, exc)
        return

    buttons: list[list[dict]] = session.get("buttons", [])

    if placement == "same" and buttons:
        buttons[-1].append(btn.model_dump())
    else:
        buttons.append([btn.model_dump()])

    session["buttons"] = buttons
    session["current_button"] = None
    await _save_session(state, session)


async def _show_button_actions(target: Message, state: FSMContext) -> None:
    session = await _get_session(state)
    buttons = session.get("buttons", [])
    total = count_buttons([[ButtonData(**b) for b in row] for row in buttons])

    await state.set_state(PostStates.waiting_button_type)
    await target.answer(
        f"✅ Button saved!  Total buttons: <b>{total}</b>\n\n"
        "Add another button or finish.",
        reply_markup=button_actions_keyboard(total),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "add_button")
async def cb_add_button(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PostStates.waiting_button_type)
    await callback.message.edit_text(
        "🔘 <b>Add a Button</b>\n\nChoose the button type:",
        reply_markup=button_type_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "remove_last_button")
async def cb_remove_last_button(
    callback: CallbackQuery, state: FSMContext
) -> None:
    session = await _get_session(state)
    buttons: list[list[dict]] = session.get("buttons", [])

    if not buttons:
        await callback.answer("No buttons to remove.", show_alert=True)
        return

    last_row = buttons[-1]
    if len(last_row) > 1:
        buttons[-1] = last_row[:-1]
    else:
        buttons.pop()

    session["buttons"] = buttons
    await _save_session(state, session)

    total = count_buttons([[ButtonData(**b) for b in row] for row in buttons])
    await callback.message.edit_text(
        f"🗑 Last button removed.  Total buttons: <b>{total}</b>\n\n"
        "Add another button or finish.",
        reply_markup=button_actions_keyboard(total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "btn_done")
async def cb_btn_done(
    callback: CallbackQuery, state: FSMContext, db_user: User
) -> None:
    """Buttons step complete — show preview."""
    await _show_preview(callback, state, db_user)


# ─────────────────────────────────────────────
#  Step 3 — Preview
# ─────────────────────────────────────────────


async def _show_preview(
    source: Message | CallbackQuery,
    state: FSMContext,
    db_user: User,
) -> None:
    session = await _get_session(state)
    active = await get_active_channel(db_user.id)

    if not active:
        text = "❌ No active channel. Please connect a channel first."
        if isinstance(source, CallbackQuery):
            await source.message.edit_text(text, reply_markup=dashboard_keyboard(False))
            await source.answer()
        else:
            await source.answer(text)
        return

    content_type: str = session["content_type"]
    file_id: str | None = session.get("file_id")
    caption: str | None = session.get("caption")
    buttons: list[list[dict]] = session.get("buttons", [])

    rows = [[ButtonData(**b) for b in row] for row in buttons]
    total_buttons = count_buttons(rows)
    buttons_json = serialize_buttons(rows) if rows else None

    await state.set_state(PostStates.preview)

    # Send the actual content preview + metadata card
    msg = source.message if isinstance(source, CallbackQuery) else source

    # Show metadata card first
    preview_text = format_post_preview_caption(
        caption, content_type, total_buttons, active.channel_name
    )

    # Render inline keyboard in the preview if buttons exist
    reply_markup_preview = buttons_to_inline_keyboard(rows) if rows else None

    # Show the actual post content as a separate message
    post_svc = PostService(msg.bot)
    await post_svc.forward_preview(
        target_chat_id=msg.chat.id,
        content_type=content_type,
        file_id=file_id,
        caption=caption,
        buttons_json=buttons_json,
    )

    await msg.answer(
        preview_text,
        reply_markup=post_preview_keyboard(),
        parse_mode="HTML",
    )

    if isinstance(source, CallbackQuery):
        await source.answer()


# ─────────────────────────────────────────────
#  Step 4 — Publish
# ─────────────────────────────────────────────


@router.callback_query(PostStates.preview, F.data == "publish_post")
async def cb_publish_post(
    callback: CallbackQuery, state: FSMContext, db_user: User, bot: Bot
) -> None:
    session = await _get_session(state)
    active = await get_active_channel(db_user.id)

    if not active:
        await callback.answer("No active channel!", show_alert=True)
        return

    # Re-check admin status before publishing
    ch_svc = ChannelService(bot)
    ok, missing = await ch_svc.check_admin_status(active.channel_id)
    if not ok:
        perms = "\n".join(f"• <code>{p}</code>" for p in missing)
        await callback.message.edit_text(
            f"❌ <b>Permission check failed.</b>\n\n"
            f"The bot is missing permissions on <b>{html_escape(active.channel_name)}</b>:\n"
            f"{perms}\n\n"
            "Please restore the permissions and try again.",
            reply_markup=dashboard_keyboard(has_channel=True),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    content_type: str = session["content_type"]
    file_id: str | None = session.get("file_id")
    caption: str | None = session.get("caption")
    buttons: list[list[dict]] = session.get("buttons", [])
    rows = [[ButtonData(**b) for b in row] for row in buttons]
    buttons_json = serialize_buttons(rows) if rows else None

    post_svc = PostService(bot)
    try:
        sent = await post_svc.publish(
            channel_id=active.channel_id,
            content_type=content_type,
            file_id=file_id,
            caption=caption,
            buttons_json=buttons_json,
        )
        await record_post(
            user_id=db_user.id,
            channel_id=active.channel_id,
            message_id=sent.message_id,
        )
    except TelegramAPIError as exc:
        logger.error("Publish failed: %s", exc)
        await callback.message.edit_text(
            f"❌ <b>Publish failed.</b>\n\n<code>{html_escape(str(exc))}</code>",
            reply_markup=dashboard_keyboard(has_channel=True),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        f"🎉 <b>Posted Successfully!</b>\n\n"
        f"Your post has been published to "
        f"<b>{html_escape(active.channel_name)}</b>.",
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )
    await callback.answer("✅ Published!")


# ─────────────────────────────────────────────
#  Save draft from preview
# ─────────────────────────────────────────────


@router.callback_query(PostStates.preview, F.data == "save_draft")
async def cb_save_draft_from_preview(
    callback: CallbackQuery, state: FSMContext, db_user: User
) -> None:
    await state.set_state(PostStates.waiting_draft_name)
    await callback.message.answer(
        "💾 <b>Save Draft</b>\n\nEnter a name for this draft:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PostStates.waiting_draft_name)
async def handle_draft_name(
    message: Message, state: FSMContext, db_user: User
) -> None:
    name = (message.text or "").strip()[:80] or "Draft"
    session = await _get_session(state)

    content_type: str = session["content_type"]
    file_id: str | None = session.get("file_id")
    caption: str | None = session.get("caption")
    buttons: list[list[dict]] = session.get("buttons", [])
    rows = [[ButtonData(**b) for b in row] for row in buttons]
    buttons_json = serialize_buttons(rows) if rows else None

    draft_svc = DraftService()
    draft = await draft_svc.save_draft(
        user_id=db_user.id,
        content_type=content_type,
        file_id=file_id,
        caption=caption,
        buttons_json=buttons_json,
        name=name,
    )

    await state.clear()
    await message.answer(
        f"💾 Draft <b>{html_escape(draft.name)}</b> saved!\n\n"
        "You can resume it anytime from <b>Drafts</b>.",
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
#  Edit buttons from preview
# ─────────────────────────────────────────────


@router.callback_query(PostStates.preview, F.data == "edit_buttons")
async def cb_edit_buttons(callback: CallbackQuery, state: FSMContext) -> None:
    session = await _get_session(state)
    buttons: list[list[dict]] = session.get("buttons", [])
    rows = [[ButtonData(**b) for b in row] for row in buttons]
    total = count_buttons(rows)

    await state.set_state(PostStates.waiting_button_type)
    await callback.message.edit_text(
        f"🔘 <b>Edit Buttons</b>\n\nCurrent buttons: <b>{total}</b>\n\n"
        "Add, remove, or finish editing:",
        reply_markup=button_actions_keyboard(total),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────
#  Discard post
# ─────────────────────────────────────────────


@router.callback_query(PostStates.preview, F.data == "discard_post")
async def cb_discard_post(
    callback: CallbackQuery, state: FSMContext, db_user: User
) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🗑 Post discarded.",
        reply_markup=dashboard_keyboard(has_channel=True),
        parse_mode="HTML",
    )
    await callback.answer()
