"""Approval and editing routes for proposed external actions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    get_audit_event_repo,
    get_meeting_repo,
    get_proposed_action_repo,
)
from app.auth.middleware import get_current_user
from app.auth.provider import AuthenticatedUser
from app.models.audit_event import AuditEventCreate, AuditEventType
from app.models.proposed_action import ProposedAction, ProposedActionStatus, ToolType
from app.repositories.audit_event_repo import AuditEventRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.proposed_action_repo import ProposedActionRepository
from app.services.action_policy import validate_action_transition
from app.services.temporal_client import TemporalService, get_temporal_service

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


class ActionEditRequest(BaseModel):
    tool_type: ToolType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict[str, Any] | None = None
    source_item_ids: list[str] | None = None


class BulkApproveRequest(BaseModel):
    meeting_id: str | None = None
    action_ids: list[str] = Field(default_factory=list)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _policy_error(exc: ValueError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


async def _record_audit(
    audit_repo: AuditEventRepository,
    *,
    meeting_id: str,
    action_id: str,
    event_type: AuditEventType,
    actor: str,
    details: dict[str, Any] | None = None,
) -> None:
    await audit_repo.create(
        AuditEventCreate(
            meeting_id=meeting_id,
            action_id=action_id,
            event_type=event_type,
            actor=actor,
            details=details or {},
        ).model_dump()
    )


async def _signal_workflow(
    meeting_id: str,
    meeting_repo: MeetingRepository,
    temporal: TemporalService,
) -> None:
    meeting = await meeting_repo.get(meeting_id)
    if not meeting or not meeting.temporal_workflow_id:
        return
    try:
        await temporal.signal_action_update(meeting.temporal_workflow_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to signal workflow %s for meeting %s: %s",
            meeting.temporal_workflow_id,
            meeting_id,
            exc,
        )


@router.get("", response_model=list[ProposedAction])
async def list_actions(
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    meeting_id: str | None = Query(default=None),
) -> list[ProposedAction]:
    if meeting_id:
        return await repo.list_for_meeting(meeting_id)
    return await repo.list(sort=[("created_at", -1)], limit=200)


@router.patch("/{action_id}", response_model=ProposedAction)
async def edit_action(
    action_id: str,
    payload: ActionEditRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    meeting_repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    temporal: Annotated[TemporalService, Depends(get_temporal_service)],
) -> ProposedAction:
    action = await repo.get(action_id)
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposed action not found")
    try:
        validate_action_transition(action.status, "edit")
    except ValueError as exc:
        raise _policy_error(exc) from exc

    changes = payload.model_dump(exclude_unset=True)
    updated = await repo.update(action_id, changes)
    assert updated is not None
    await _record_audit(
        audit_repo,
        meeting_id=updated.meeting_id,
        action_id=action_id,
        event_type=AuditEventType.ACTION_EDITED,
        actor=current_user.username,
        details={"changed_fields": sorted(changes.keys())},
    )
    await _signal_workflow(updated.meeting_id, meeting_repo, temporal)
    return updated


@router.post("/{action_id}/approve", response_model=ProposedAction)
async def approve_action(
    action_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    meeting_repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    temporal: Annotated[TemporalService, Depends(get_temporal_service)],
) -> ProposedAction:
    action = await repo.get(action_id)
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposed action not found")
    try:
        validate_action_transition(action.status, "approve")
    except ValueError as exc:
        raise _policy_error(exc) from exc

    updated = await repo.update(
        action_id,
        {
            "status": ProposedActionStatus.APPROVED.value,
            "approved_by": current_user.username,
            "approved_at": _now(),
        },
    )
    assert updated is not None
    await _record_audit(
        audit_repo,
        meeting_id=updated.meeting_id,
        action_id=action_id,
        event_type=AuditEventType.ACTION_APPROVED,
        actor=current_user.username,
    )
    await _signal_workflow(updated.meeting_id, meeting_repo, temporal)
    return updated


@router.post("/{action_id}/reject", response_model=ProposedAction)
async def reject_action(
    action_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    meeting_repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    temporal: Annotated[TemporalService, Depends(get_temporal_service)],
) -> ProposedAction:
    action = await repo.get(action_id)
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposed action not found")
    try:
        validate_action_transition(action.status, "reject")
    except ValueError as exc:
        raise _policy_error(exc) from exc

    updated = await repo.update(
        action_id,
        {
            "status": ProposedActionStatus.REJECTED.value,
            "rejected_by": current_user.username,
            "rejected_at": _now(),
        },
    )
    assert updated is not None
    await _record_audit(
        audit_repo,
        meeting_id=updated.meeting_id,
        action_id=action_id,
        event_type=AuditEventType.ACTION_REJECTED,
        actor=current_user.username,
    )
    await _signal_workflow(updated.meeting_id, meeting_repo, temporal)
    return updated


@router.post("/{action_id}/retry", response_model=ProposedAction)
async def retry_action(
    action_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    meeting_repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    temporal: Annotated[TemporalService, Depends(get_temporal_service)],
) -> ProposedAction:
    action = await repo.get(action_id)
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposed action not found")
    try:
        validate_action_transition(action.status, "retry")
    except ValueError as exc:
        raise _policy_error(exc) from exc

    updated = await repo.update(
        action_id,
        {
            "status": ProposedActionStatus.APPROVED.value,
            "approved_by": current_user.username,
            "approved_at": _now(),
        },
    )
    assert updated is not None
    await _record_audit(
        audit_repo,
        meeting_id=updated.meeting_id,
        action_id=action_id,
        event_type=AuditEventType.ACTION_RETRIED,
        actor=current_user.username,
    )
    await _signal_workflow(updated.meeting_id, meeting_repo, temporal)
    return updated


@router.post("/bulk-approve", response_model=list[ProposedAction])
async def bulk_approve_actions(
    payload: BulkApproveRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    meeting_repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    temporal: Annotated[TemporalService, Depends(get_temporal_service)],
) -> list[ProposedAction]:
    actions: list[ProposedAction] = []
    if payload.action_ids:
        for action_id in payload.action_ids:
            action = await repo.get(action_id)
            if action:
                actions.append(action)
    elif payload.meeting_id:
        actions = await repo.list_by_status(
            payload.meeting_id,
            [ProposedActionStatus.PROPOSED, ProposedActionStatus.FAILED],
        )
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide either action_ids or meeting_id.",
        )

    updated_actions: list[ProposedAction] = []
    signaled_meeting_ids: set[str] = set()
    for action in actions:
        try:
            validate_action_transition(action.status, "approve")
        except ValueError:
            continue
        updated = await repo.update(
            action.id or "",
            {
                "status": ProposedActionStatus.APPROVED.value,
                "approved_by": current_user.username,
                "approved_at": _now(),
            },
        )
        if not updated:
            continue
        updated_actions.append(updated)
        signaled_meeting_ids.add(updated.meeting_id)
        await _record_audit(
            audit_repo,
            meeting_id=updated.meeting_id,
            action_id=updated.id or "",
            event_type=AuditEventType.ACTION_APPROVED,
            actor=current_user.username,
            details={"bulk": True},
        )

    for meeting_id in signaled_meeting_ids:
        await _signal_workflow(meeting_id, meeting_repo, temporal)

    return updated_actions
