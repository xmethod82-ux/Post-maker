"""
Business logic for the draft system.
"""

import logging
from bot.database import drafts as draft_db
from bot.models import Draft

logger = logging.getLogger(__name__)


class DraftService:
    async def save_draft(
        self,
        user_id: int,
        content_type: str,
        file_id: str | None,
        caption: str | None,
        buttons_json: str | None,
        name: str = "Draft",
    ) -> Draft:
        """Persist a new draft and return it."""
        return await draft_db.create_draft(
            user_id=user_id,
            content_type=content_type,
            file_id=file_id,
            caption=caption,
            buttons_json=buttons_json,
            name=name,
        )

    async def list_drafts(self, user_id: int) -> list[Draft]:
        return await draft_db.get_user_drafts(user_id)

    async def get_draft(self, draft_id: int, user_id: int) -> Draft | None:
        return await draft_db.get_draft_by_id(draft_id, user_id)

    async def rename_draft(
        self, draft_id: int, user_id: int, new_name: str
    ) -> Draft | None:
        return await draft_db.update_draft(draft_id, user_id, name=new_name)

    async def delete_draft(self, draft_id: int, user_id: int) -> bool:
        return await draft_db.delete_draft(draft_id, user_id)
