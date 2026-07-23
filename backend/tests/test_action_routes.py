"""Route-level tests for approval behavior."""

from __future__ import annotations

from typing import Any

import pytest

from app.api.routes.actions import approve_action
from app.auth.provider import AuthenticatedUser
from app.models.meeting import Meeting
from app.models.proposed_action import ProposedAction, ProposedActionStatus


class _ActionRepo:
    def __init__(self, action: ProposedAction) -> None:
        self.action = action
        self.updated_with: dict[str, Any] | None = None

    async def get(self, action_id: str) -> ProposedAction | None:
        return self.action if action_id == self.action.id else None

    async def update(self, action_id: str, data: dict[str, Any]) -> ProposedAction | None:
        if action_id != self.action.id:
            return None
        self.updated_with = data
        payload = {**self.action.model_dump(), **data}
        self.action = ProposedAction.model_validate(payload)
        return self.action


class _AuditRepo:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(data)
        return data


class _MeetingRepo:
    async def get(self, meeting_id: str) -> Meeting | None:
        return Meeting(
            id=meeting_id,
            title="Planning",
            temporal_workflow_id="meeting-processing-meeting-1",
        )


class _Temporal:
    def __init__(self) -> None:
        self.signaled: list[str] = []

    async def signal_action_update(self, workflow_id: str) -> None:
        self.signaled.append(workflow_id)


@pytest.mark.asyncio
async def test_approve_action_updates_state_audits_and_signals() -> None:
    action = ProposedAction(
        id="action-1",
        meeting_id="meeting-1",
        tool_type="task",
        title="Create docs task",
        payload={"owner": "Sara"},
        idempotency_key="key-1",
    )
    repo = _ActionRepo(action)
    audit_repo = _AuditRepo()
    meeting_repo = _MeetingRepo()
    temporal = _Temporal()

    updated = await approve_action(
        "action-1",
        AuthenticatedUser(username="admin", provider="simple"),
        repo,  # type: ignore[arg-type]
        audit_repo,  # type: ignore[arg-type]
        meeting_repo,  # type: ignore[arg-type]
        temporal,  # type: ignore[arg-type]
    )

    assert updated.status == ProposedActionStatus.APPROVED
    assert repo.updated_with is not None
    assert repo.updated_with["approved_by"] == "admin"
    assert audit_repo.created[0]["event_type"] == "action_approved"
    assert temporal.signaled == ["meeting-processing-meeting-1"]
