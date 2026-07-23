"""Tests for approval-gated external tool stubs."""

from __future__ import annotations

import pytest

from activities.tools import ToolExecutionInput, execute_tool_action


@pytest.mark.asyncio
async def test_execute_tool_action_is_noop_stub() -> None:
    result = await execute_tool_action(
        ToolExecutionInput(
            action_id="action-1",
            meeting_id="meeting-1",
            tool_type="calendar_event",
            title="Follow-up",
            payload={"starts_at": "next Tuesday 10:00"},
            idempotency_key="abcdef1234567890",
        )
    )

    assert result.success is True
    assert result.result["mode"] == "stub"
    assert result.result["external_id"] == "stub-abcdef1234567890"
