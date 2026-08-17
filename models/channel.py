"""Pydantic model representing a connected Telegram channel."""

from datetime import datetime
from pydantic import BaseModel


class Channel(BaseModel):
    id: int
    user_id: int
    channel_id: int
    channel_name: str
    username: str | None
    is_active: bool
    connected_at: datetime
