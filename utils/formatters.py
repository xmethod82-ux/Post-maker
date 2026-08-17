"""
Text formatting utilities for bot messages.
"""

import html
from bot.models import Channel


def html_escape(text: str) -> str:
    """Escape special HTML characters for Telegram HTML parse mode."""
    return html.escape(text, quote=False)


CONTENT_TYPE_EMOJIS: dict[str, str] = {
    "text":      "📝",
    "photo":     "🖼",
    "video":     "🎬",
    "animation": "🎞",
    "audio":     "🎵",
    "voice":     "🎙",
    "document":  "📄",
    "sticker":   "🎭",
}


def content_type_emoji(content_type: str) -> str:
    return CONTENT_TYPE_EMOJIS.get(content_type, "📎")


def format_channel_status(channel: Channel) -> str:
    """Return a formatted one-liner for a channel (used in lists)."""
    name = html_escape(channel.channel_name)
    tag = f"  @{html_escape(channel.username)}" if channel.username else ""
    active = "  ✅ Active" if channel.is_active else ""
    return f"📢 <b>{name}</b>{tag}{active}"


def format_post_preview_caption(
    caption: str | None,
    content_type: str,
    buttons_count: int,
    channel_name: str,
) -> str:
    """Build the preview message shown before publishing."""
    lines: list[str] = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "👁  <b>POST PREVIEW</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{content_type_emoji(content_type)} Content type: <b>{content_type.capitalize()}</b>",
        f"📢 Channel: <b>{html_escape(channel_name)}</b>",
    ]

    if buttons_count:
        lines.append(f"🔘 Buttons: <b>{buttons_count}</b>")

    if caption:
        lines += ["", "📋 <b>Caption:</b>", html_escape(caption)]

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "Choose an action below 👇",
    ]
    return "\n".join(lines)
