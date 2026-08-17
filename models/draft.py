"""Pydantic models for draft posts and button structures."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl, field_validator


class ButtonData(BaseModel):
    """Represents a single inline button in a post."""

    type: Literal["url", "webapp"]
    url: str
    label: str
    style: Literal["primary", "success", "danger"]

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ButtonRow(BaseModel):
    """A row of buttons in the keyboard layout."""

    buttons: list[ButtonData]


class Draft(BaseModel):
    id: int
    user_id: int
    name: str
    content_type: str
    file_id: str | None
    caption: str | None
    buttons_json: str | None  # JSON-encoded list[list[ButtonData]]
    created_at: datetime
