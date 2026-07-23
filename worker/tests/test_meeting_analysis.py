"""Unit tests for meeting extraction/action-planning helpers."""

from __future__ import annotations

from activities.meeting_analysis import _coerce_actions, _coerce_items, _idempotency_key


def test_coerce_items_normalizes_valid_meeting_information() -> None:
    result = _coerce_items(
        {
            "items": [
                {
                    "order": "1",
                    "item_type": "action item",
                    "title": "Finish API documentation",
                    "owner": "Sara",
                    "due_date": "Friday",
                    "priority": "High",
                    "status": "open",
                },
                {"item_type": "nonsense", "title": "ignored"},
            ]
        }
    )

    assert len(result) == 1
    assert result[0].item_type == "action_item"
    assert result[0].owner == "Sara"
    assert result[0].priority == "high"


def test_action_idempotency_key_is_stable() -> None:
    payload = {"due": "Friday", "owner": "Sara"}

    assert _idempotency_key("m1", "task", "Docs", payload) == _idempotency_key(
        "m1",
        "task",
        "Docs",
        {"owner": "Sara", "due": "Friday"},
    )


def test_coerce_actions_deduplicates_and_filters_invalid_tools() -> None:
    raw = {
        "proposed_actions": [
            {
                "tool_type": "task",
                "title": "Create documentation task",
                "payload": {"owner": "Sara"},
                "source_item_orders": ["1"],
            },
            {
                "tool_type": "task",
                "title": "Create documentation task",
                "payload": {"owner": "Sara"},
                "source_item_orders": [1],
            },
            {"tool_type": "unknown", "title": "Ignore"},
        ]
    }

    result = _coerce_actions(raw, "meeting-1")

    assert len(result) == 1
    assert result[0].tool_type == "task"
    assert result[0].source_item_orders == [1]


def test_coerce_actions_preserves_event_and_reminder_payloads() -> None:
    raw = {
        "proposed_actions": [
            {
                "tool_type": "calendar event",
                "title": "Schedule follow-up planning review",
                "payload": {
                    "title": "Planning review",
                    "starts_at": "next Tuesday at 10:00",
                    "attendees": ["Sara", "Leo"],
                },
                "source_item_orders": [2],
            },
            {
                "tool_type": "reminder",
                "title": "Remind Sara about API docs",
                "payload": {
                    "title": "API docs reminder",
                    "remind_at": "Friday at 09:00",
                    "owner": "Sara",
                },
                "source_item_orders": [3],
            },
        ]
    }

    result = _coerce_actions(raw, "meeting-1")

    assert [action.tool_type for action in result] == ["calendar_event", "reminder"]
    assert result[0].payload["starts_at"] == "next Tuesday at 10:00"
    assert result[1].payload["owner"] == "Sara"
