"""Route-level tests for meeting cleanup behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.api.routes.meetings import delete_meeting
from app.auth.provider import AuthenticatedUser
from app.models.meeting import Meeting


class _MeetingRepo:
    def __init__(self, meeting: Meeting) -> None:
        self.meeting = meeting
        self.deleted = False

    async def get(self, meeting_id: str) -> Meeting | None:
        return self.meeting if meeting_id == self.meeting.id else None

    async def delete(self, meeting_id: str) -> bool:
        self.deleted = meeting_id == self.meeting.id
        return self.deleted


class _ChildRepo:
    def __init__(self) -> None:
        self.deleted_for: list[str] = []

    async def delete_for_meeting(self, meeting_id: str) -> int:
        self.deleted_for.append(meeting_id)
        return 1


class _AuditRepo(_ChildRepo):
    def __init__(self) -> None:
        super().__init__()
        self.created: list[dict[str, Any]] = []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(data)
        return data


@pytest.mark.asyncio
async def test_delete_meeting_cleans_children_and_audio(tmp_path: Path) -> None:
    audio_path = tmp_path / "meeting.webm"
    audio_path.write_bytes(b"audio")
    meeting = Meeting(id="meeting-1", title="Planning", audio_file_path=str(audio_path))
    meeting_repo = _MeetingRepo(meeting)
    items_repo = _ChildRepo()
    actions_repo = _ChildRepo()
    audit_repo = _AuditRepo()

    await delete_meeting(
        "meeting-1",
        AuthenticatedUser(username="admin", provider="simple"),
        meeting_repo,  # type: ignore[arg-type]
        items_repo,  # type: ignore[arg-type]
        actions_repo,  # type: ignore[arg-type]
        audit_repo,  # type: ignore[arg-type]
    )

    assert meeting_repo.deleted is True
    assert items_repo.deleted_for == ["meeting-1"]
    assert actions_repo.deleted_for == ["meeting-1"]
    assert audit_repo.deleted_for == ["meeting-1"]
    assert not audio_path.exists()
