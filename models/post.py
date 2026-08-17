"""Pydantic model representing a published post record."""

from datetime import datetime
from pydantic import BaseModel


class Post(BaseModel):
    id: int
    user_id: int
    channel_id: int
    message_id: int
    created_at: datetime
