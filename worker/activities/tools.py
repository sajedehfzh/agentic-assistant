"""Stub external-tool activities for approval-gated meeting actions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from temporalio import activity


class ToolExecutionInput(BaseModel):
    action_id: str
    meeting_id: str
    tool_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str


class ToolExecutionResult(BaseModel):
    action_id: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None


@activity.defn
async def execute_tool_action(payload: ToolExecutionInput) -> ToolExecutionResult:
    """Record what would be executed by a real integration.

    This is intentionally a no-op adapter. Real providers can later replace
    this activity behind the same idempotent contract.
    """
    return ToolExecutionResult(
        action_id=payload.action_id,
        success=True,
        result={
            "mode": "stub",
            "tool_type": payload.tool_type,
            "title": payload.title,
            "external_id": f"stub-{payload.idempotency_key[:16]}",
            "message": "No external provider was called. Action recorded as approved stub.",
        },
    )
