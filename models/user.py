"""Pydantic model representing a registered bot user."""

from datetime import datetime
from pydantic import BaseModel


class User(BaseModel):
    id: int
    telegram_id: int
    name: str
    username: str | None
    joined_at: datetime
