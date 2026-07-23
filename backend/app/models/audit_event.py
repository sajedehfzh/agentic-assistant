"""Audit events for consent, approvals, and external-action attempts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models._common import MongoModel


class AuditEventType(str, Enum):
    CONSENT_CONFIRMED = "consent_confirmed"
    ACTION_APPROVED = "action_approved"
    ACTION_REJECTED = "action_rejected"
    ACTION_EDITED = "action_edited"
    ACTION_RETRIED = "action_retried"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"
    MEETING_DELETED = "meeting_deleted"


class AuditEventCreate(BaseModel):
    meeting_id: str | None = None
    action_id: str | None = None
    event_type: AuditEventType
    actor: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(MongoModel):
    meeting_id: str | None = None
    action_id: str | None = None
    event_type: AuditEventType
    actor: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
