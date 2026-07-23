"""External actions proposed from meeting content."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models._common import MongoModel


class ToolType(str, Enum):
    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    TASK = "task"
    NOTION_PAGE = "notion_page"
    JIRA_TICKET = "jira_ticket"
    EMAIL = "email"
    SLACK_MESSAGE = "slack_message"
    TEAMS_MESSAGE = "teams_message"
    DOCUMENT_NOTE = "document_note"


class ProposedActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"


class ProposedActionCreate(BaseModel):
    meeting_id: str = Field(..., min_length=1)
    tool_type: ToolType
    title: str = Field(..., min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    source_item_ids: list[str] = Field(default_factory=list)
    status: ProposedActionStatus = ProposedActionStatus.PROPOSED
    idempotency_key: str = Field(..., min_length=1)


class ProposedActionUpdate(BaseModel):
    tool_type: ToolType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict[str, Any] | None = None
    source_item_ids: list[str] | None = None
    status: ProposedActionStatus | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    execution_result: dict[str, Any] | None = None
    failure_reason: str | None = None
    executed_at: datetime | None = None


class ProposedAction(MongoModel):
    meeting_id: str
    tool_type: ToolType
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_item_ids: list[str] = Field(default_factory=list)
    status: ProposedActionStatus = ProposedActionStatus.PROPOSED
    idempotency_key: str

    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    execution_result: dict[str, Any] | None = None
    failure_reason: str | None = None
    executed_at: datetime | None = None
