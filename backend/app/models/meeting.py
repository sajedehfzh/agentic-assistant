"""Meeting domain model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models._common import MongoModel


class MeetingStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    EXTRACTING_INFORMATION = "extracting_information"
    PLANNING_ACTIONS = "planning_actions"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING_ACTIONS = "executing_actions"
    COMPLETED = "completed"
    COMPLETED_WITH_ACTION_FAILURES = "completed_with_action_failures"
    FAILED = "failed"


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    meeting_date: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    participants: list[str] = Field(default_factory=list)
    notes: str | None = None


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    meeting_date: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    participants: list[str] | None = None
    notes: str | None = None
    status: MeetingStatus | None = None
    audio_file_path: str | None = None
    audio_sha256: str | None = None
    transcript: str | None = None
    executive_summary: str | None = None
    temporal_workflow_id: str | None = None
    failure_reason: str | None = None


class Meeting(MongoModel):
    title: str
    meeting_date: datetime | None = None
    duration_seconds: int | None = None
    participants: list[str] = Field(default_factory=list)
    notes: str | None = None
    status: MeetingStatus = MeetingStatus.CREATED

    audio_file_path: str | None = None
    audio_sha256: str | None = None
    transcript: str | None = None
    executive_summary: str | None = None

    temporal_workflow_id: str | None = None
    failure_reason: str | None = None
