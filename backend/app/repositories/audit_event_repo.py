"""Repository for audit events."""

from __future__ import annotations

from app.models.audit_event import AuditEvent
from app.repositories.base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    collection_name = "audit_events"
    model = AuditEvent

    async def list_for_meeting(self, meeting_id: str, limit: int = 500) -> list[AuditEvent]:
        return await self.list(
            {"meeting_id": meeting_id},
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def delete_for_meeting(self, meeting_id: str) -> int:
        result = await self.collection.delete_many({"meeting_id": meeting_id})
        return result.deleted_count
