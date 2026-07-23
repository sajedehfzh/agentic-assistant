"""Repository for structured meeting items."""

from __future__ import annotations

from app.models.meeting_item import MeetingItem
from app.repositories.base import BaseRepository


class MeetingItemRepository(BaseRepository[MeetingItem]):
    collection_name = "meeting_items"
    model = MeetingItem

    async def list_for_meeting(self, meeting_id: str, limit: int = 500) -> list[MeetingItem]:
        return await self.list(
            {"meeting_id": meeting_id},
            limit=limit,
            sort=[("order", 1), ("created_at", 1)],
        )

    async def delete_for_meeting(self, meeting_id: str) -> int:
        result = await self.collection.delete_many({"meeting_id": meeting_id})
        return result.deleted_count
