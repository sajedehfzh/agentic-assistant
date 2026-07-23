"""Repository for the `meetings` collection."""

from __future__ import annotations

from app.models.meeting import Meeting
from app.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    collection_name = "meetings"
    model = Meeting

    async def list_recent(self, limit: int = 200) -> list[Meeting]:
        return await self.list(sort=[("meeting_date", -1), ("created_at", -1)], limit=limit)
