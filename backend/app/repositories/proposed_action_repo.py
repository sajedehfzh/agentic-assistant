"""Repository for proposed external actions."""

from __future__ import annotations

from app.models.proposed_action import ProposedAction, ProposedActionStatus
from app.repositories.base import BaseRepository


class ProposedActionRepository(BaseRepository[ProposedAction]):
    collection_name = "proposed_actions"
    model = ProposedAction

    async def list_for_meeting(self, meeting_id: str, limit: int = 500) -> list[ProposedAction]:
        return await self.list(
            {"meeting_id": meeting_id},
            limit=limit,
            sort=[("created_at", 1)],
        )

    async def list_by_status(
        self,
        meeting_id: str,
        statuses: list[ProposedActionStatus],
        limit: int = 500,
    ) -> list[ProposedAction]:
        return await self.list(
            {"meeting_id": meeting_id, "status": {"$in": [s.value for s in statuses]}},
            limit=limit,
            sort=[("created_at", 1)],
        )

    async def delete_for_meeting(self, meeting_id: str) -> int:
        result = await self.collection.delete_many({"meeting_id": meeting_id})
        return result.deleted_count
