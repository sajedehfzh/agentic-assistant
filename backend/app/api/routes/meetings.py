"""Meeting CRUD routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_audit_event_repo,
    get_meeting_item_repo,
    get_meeting_repo,
    get_proposed_action_repo,
)
from app.auth.middleware import get_current_user
from app.auth.provider import AuthenticatedUser
from app.models.audit_event import AuditEventCreate, AuditEventType
from app.models.meeting import Meeting, MeetingCreate, MeetingUpdate
from app.repositories.audit_event_repo import AuditEventRepository
from app.repositories.meeting_item_repo import MeetingItemRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.proposed_action_repo import ProposedActionRepository

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[Meeting])
async def list_meetings(
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
) -> list[Meeting]:
    return await repo.list_recent()


@router.post("", response_model=Meeting, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
) -> Meeting:
    return await repo.create(payload.model_dump())


@router.get("/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: str,
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
) -> Meeting:
    item = await repo.get(meeting_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    return item


@router.patch("/{meeting_id}", response_model=Meeting)
async def update_meeting(
    meeting_id: str,
    payload: MeetingUpdate,
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
) -> Meeting:
    item = await repo.update(meeting_id, payload.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    return item


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_meeting(
    meeting_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    items_repo: Annotated[MeetingItemRepository, Depends(get_meeting_item_repo)],
    actions_repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
) -> None:
    meeting = await repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")

    await audit_repo.create(
        AuditEventCreate(
            meeting_id=meeting_id,
            event_type=AuditEventType.MEETING_DELETED,
            actor=current_user.username,
            details={"title": meeting.title},
        ).model_dump()
    )
    await items_repo.delete_for_meeting(meeting_id)
    await actions_repo.delete_for_meeting(meeting_id)
    await audit_repo.delete_for_meeting(meeting_id)
    deleted = await repo.delete(meeting_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")

    if meeting.audio_file_path:
        try:
            Path(meeting.audio_file_path).unlink(missing_ok=True)
        except OSError:
            pass
