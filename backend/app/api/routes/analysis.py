"""Analysis routes — kicks off and inspects the Temporal meeting workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import (
    get_meeting_item_repo,
    get_meeting_repo,
    get_proposed_action_repo,
)
from app.auth.middleware import get_current_user
from app.models.meeting import Meeting, MeetingStatus
from app.models.meeting_item import MeetingItem
from app.models.proposed_action import ProposedAction
from app.repositories.meeting_item_repo import MeetingItemRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.proposed_action_repo import ProposedActionRepository
from app.services.temporal_client import TemporalService, get_temporal_service

router = APIRouter(dependencies=[Depends(get_current_user)])


class AnalysisStartResponse(BaseModel):
    meeting_id: str
    workflow_id: str
    status: str


class AnalysisResultResponse(BaseModel):
    meeting: Meeting
    items: list[MeetingItem]
    proposed_actions: list[ProposedAction]


@router.post(
    "/{meeting_id}/start",
    response_model=AnalysisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_analysis(
    meeting_id: str,
    repo: MeetingRepository = Depends(get_meeting_repo),
    temporal: TemporalService = Depends(get_temporal_service),
) -> AnalysisStartResponse:
    meeting = await repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    if not meeting.audio_file_path:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Meeting has no audio file uploaded yet.",
        )

    workflow_id = await temporal.start_meeting_processing(
        meeting_id=meeting_id,
        audio_path=meeting.audio_file_path,
    )
    await repo.update(
        meeting_id,
        {
            "temporal_workflow_id": workflow_id,
            "status": MeetingStatus.TRANSCRIBING.value,
        },
    )
    return AnalysisStartResponse(
        meeting_id=meeting_id,
        workflow_id=workflow_id,
        status=MeetingStatus.TRANSCRIBING.value,
    )


@router.get("/{meeting_id}", response_model=AnalysisResultResponse)
async def get_analysis(
    meeting_id: str,
    repo: MeetingRepository = Depends(get_meeting_repo),
    items_repo: MeetingItemRepository = Depends(get_meeting_item_repo),
    actions_repo: ProposedActionRepository = Depends(get_proposed_action_repo),
) -> AnalysisResultResponse:
    meeting = await repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    items = await items_repo.list_for_meeting(meeting_id)
    actions = await actions_repo.list_for_meeting(meeting_id)
    return AnalysisResultResponse(meeting=meeting, items=items, proposed_actions=actions)


@router.get("/{meeting_id}/workflow")
async def describe_workflow(
    meeting_id: str,
    repo: MeetingRepository = Depends(get_meeting_repo),
    temporal: TemporalService = Depends(get_temporal_service),
) -> dict:
    meeting = await repo.get(meeting_id)
    if not meeting or not meeting.temporal_workflow_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No workflow associated with this meeting.",
        )
    return await temporal.describe_workflow(meeting.temporal_workflow_id)
