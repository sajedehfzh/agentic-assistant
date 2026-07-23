"""Structured information extracted from a meeting transcript."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models._common import MongoModel


class MeetingItemType(str, Enum):
    DISCUSSION_POINT = "discussion_point"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    FOLLOW_UP = "follow_up"
    OPEN_QUESTION = "open_question"
    RISK = "risk"
    BLOCKER = "blocker"
    DEPENDENCY = "dependency"
    IMPORTANT_DATE = "important_date"
    REFERENCE = "reference"


class MeetingItemPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MeetingItemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class MeetingItemCreate(BaseModel):
    meeting_id: str = Field(..., min_length=1)
    order: int = Field(default=0, ge=0)
    item_type: MeetingItemType
    title: str = Field(..., min_length=1)
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: MeetingItemPriority | None = None
    status: MeetingItemStatus = MeetingItemStatus.OPEN
    source_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeetingItemUpdate(BaseModel):
    item_type: MeetingItemType | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: MeetingItemPriority | None = None
    status: MeetingItemStatus | None = None
    source_text: str | None = None
    metadata: dict[str, Any] | None = None


class MeetingItem(MongoModel):
    meeting_id: str
    order: int = 0
    item_type: MeetingItemType
    title: str
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: MeetingItemPriority | None = None
    status: MeetingItemStatus = MeetingItemStatus.OPEN
    source_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
