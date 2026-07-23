"""LLM activities for meeting information extraction and action planning."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from temporalio import activity

from activities._llm import chat, parse_json_response

logger = logging.getLogger(__name__)


VALID_ITEM_TYPES = {
    "discussion_point",
    "decision",
    "action_item",
    "follow_up",
    "open_question",
    "risk",
    "blocker",
    "dependency",
    "important_date",
    "reference",
}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_STATUSES = {"open", "in_progress", "done", "blocked"}
VALID_TOOLS = {
    "calendar_event",
    "reminder",
    "task",
    "notion_page",
    "jira_ticket",
    "email",
    "slack_message",
    "teams_message",
    "document_note",
}


class MeetingItemDraft(BaseModel):
    order: int = 0
    item_type: str
    title: str
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str = "open"
    source_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionPlanDraft(BaseModel):
    tool_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_item_orders: list[int] = Field(default_factory=list)
    idempotency_key: str


class ExtractMeetingInformationInput(BaseModel):
    transcript: str
    title: str | None = None
    meeting_date: str | None = None
    participants: list[str] = Field(default_factory=list)


class ExtractMeetingInformationResult(BaseModel):
    items: list[MeetingItemDraft]


class ActionPlanningInput(BaseModel):
    meeting_id: str
    transcript: str
    executive_summary: str | None = None
    items: list[MeetingItemDraft] = Field(default_factory=list)


class ActionPlanningResult(BaseModel):
    proposed_actions: list[ActionPlanDraft]


EXTRACT_SYSTEM = (
    "You are an expert meeting analyst. Extract concrete, useful meeting "
    "information from transcripts. Focus on decisions, action items, owners, "
    "deadlines, follow-ups, open questions, risks, blockers, dependencies, "
    "important dates, and references to documents, projects, tickets, or "
    "external systems."
)

EXTRACT_USER_TEMPLATE = """Meeting title: {title}
Meeting date: {meeting_date}
Participants: {participants}

Transcript:
{transcript}

Return ONLY valid JSON in this exact shape:

{{
  "items": [
    {{
      "order": 1,
      "item_type": "discussion_point|decision|action_item|follow_up|open_question|risk|blocker|dependency|important_date|reference",
      "title": "...",
      "description": "...",
      "owner": "person or team, if any",
      "due_date": "natural-language or ISO date, if any",
      "priority": "low|medium|high|urgent",
      "status": "open|in_progress|done|blocked",
      "source_text": "short supporting quote or paraphrase",
      "metadata": {{}}
    }}
  ]
}}
"""


ACTION_SYSTEM = (
    "You are an approval-first agentic assistant for managing meetings, "
    "follow-up events, reminders, tasks, notes, tickets, emails, and team "
    "messages. Decide which extracted meeting items are useful enough to "
    "become proposed external actions. Do not propose an action for every "
    "item. Propose only actions where an external tool would clearly help. "
    "Never execute anything; only prepare editable proposals for user approval."
)

ACTION_USER_TEMPLATE = """Executive summary:
{executive_summary}

Extracted items:
{items_json}

Transcript:
{transcript}

Return ONLY valid JSON:

{{
  "proposed_actions": [
    {{
      "tool_type": "calendar_event|reminder|task|notion_page|jira_ticket|email|slack_message|teams_message|document_note",
      "title": "...",
      "payload": {{
        "description": "editable tool-specific payload"
      }},
      "source_item_orders": [1, 2]
    }}
  ]
}}

Use these payload conventions:

- calendar_event: {{"title": "...", "starts_at": "natural language or ISO datetime", "ends_at": "...", "attendees": ["..."], "description": "...", "location": "..."}}
- reminder: {{"title": "...", "remind_at": "natural language or ISO datetime", "owner": "...", "description": "..."}}
- task: {{"title": "...", "owner": "...", "due_date": "...", "priority": "low|medium|high|urgent", "description": "..."}}
- email: {{"to": ["..."], "cc": [], "subject": "...", "body": "...", "mode": "draft"}}
- document_note/notion_page: {{"title": "...", "body": "...", "references": ["..."]}}
- jira_ticket: {{"summary": "...", "description": "...", "project": "...", "issue_type": "Task"}}
- slack_message/teams_message: {{"channel": "...", "message": "..."}}

Prefer calendar_event for proposed future meetings or dated events, reminder
for nudges before deadlines, task for assigned work, document_note/notion_page
for durable notes, and email/team messages only when a clear outbound
communication is useful.
"""


def _normalize_choice(value: Any, valid: set[str], default: str | None = None) -> str | None:
    if not isinstance(value, str):
        return default
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    candidates = [normalized, normalized.replace("_", "-")]
    for candidate in candidates:
        if candidate in valid:
            return candidate
    return default


def _coerce_metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_items(raw: Any) -> list[MeetingItemDraft]:
    if not isinstance(raw, dict):
        return []
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []
    drafts: list[MeetingItemDraft] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        item_type = _normalize_choice(item.get("item_type"), VALID_ITEM_TYPES)
        if not title or not item_type:
            continue
        try:
            drafts.append(
                MeetingItemDraft(
                    order=int(item.get("order") or idx),
                    item_type=item_type,
                    title=title,
                    description=(item.get("description") or None),
                    owner=(item.get("owner") or None),
                    due_date=(item.get("due_date") or None),
                    priority=_normalize_choice(item.get("priority"), VALID_PRIORITIES),
                    status=_normalize_choice(item.get("status"), VALID_STATUSES, "open")
                    or "open",
                    source_text=(item.get("source_text") or None),
                    metadata=_coerce_metadata(item.get("metadata")),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Skipping bad meeting item: %s (%s)", item, exc)
    return drafts


def _idempotency_key(meeting_id: str, tool_type: str, title: str, payload: dict[str, Any]) -> str:
    stable = json.dumps(
        {
            "meeting_id": meeting_id,
            "tool_type": tool_type,
            "title": title,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _coerce_actions(raw: Any, meeting_id: str) -> list[ActionPlanDraft]:
    if not isinstance(raw, dict):
        return []
    items = raw.get("proposed_actions", [])
    if not isinstance(items, list):
        return []
    drafts: list[ActionPlanDraft] = []
    seen_keys: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        tool_type = _normalize_choice(item.get("tool_type"), VALID_TOOLS)
        title = str(item.get("title") or "").strip()
        payload = _coerce_metadata(item.get("payload"))
        if not tool_type or not title:
            continue
        key = _idempotency_key(meeting_id, tool_type, title, payload)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        source_orders: list[int] = []
        for raw_order in item.get("source_item_orders") or []:
            try:
                source_orders.append(int(raw_order))
            except (TypeError, ValueError):
                continue
        drafts.append(
            ActionPlanDraft(
                tool_type=tool_type,
                title=title,
                payload=payload,
                source_item_orders=source_orders,
                idempotency_key=key,
            )
        )
    return drafts


@activity.defn
async def extract_meeting_information(
    payload: ExtractMeetingInformationInput,
) -> ExtractMeetingInformationResult:
    if not payload.transcript.strip():
        return ExtractMeetingInformationResult(items=[])
    content = await chat(
        system=EXTRACT_SYSTEM,
        user=EXTRACT_USER_TEMPLATE.format(
            title=payload.title or "unknown",
            meeting_date=payload.meeting_date or "unknown",
            participants=", ".join(payload.participants) or "unknown",
            transcript=payload.transcript,
        ),
        response_format_json=True,
        temperature=0.1,
        max_tokens=8192,
    )
    parsed = parse_json_response(content)
    return ExtractMeetingInformationResult(items=_coerce_items(parsed))


@activity.defn
async def plan_meeting_actions(payload: ActionPlanningInput) -> ActionPlanningResult:
    if not payload.items:
        return ActionPlanningResult(proposed_actions=[])
    items_json = json.dumps([item.model_dump() for item in payload.items], ensure_ascii=True)
    content = await chat(
        system=ACTION_SYSTEM,
        user=ACTION_USER_TEMPLATE.format(
            executive_summary=payload.executive_summary or "",
            items_json=items_json,
            transcript=payload.transcript,
        ),
        response_format_json=True,
        temperature=0.1,
        max_tokens=8192,
    )
    parsed = parse_json_response(content)
    return ActionPlanningResult(proposed_actions=_coerce_actions(parsed, payload.meeting_id))
