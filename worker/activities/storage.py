"""Storage activities for meeting-processing workflows."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from temporalio import activity

from activities.meeting_analysis import ActionPlanDraft, MeetingItemDraft
from config import get_settings

logger = logging.getLogger(__name__)


class StorageInput(BaseModel):
    meeting_id: str
    transcript: str | None = None
    executive_summary: str | None = None
    items: list[MeetingItemDraft] | None = None
    proposed_actions: list[ActionPlanDraft] | None = None
    final_status: str | None = None


class UpdateMeetingStatusInput(BaseModel):
    meeting_id: str
    status: str
    failure_reason: str | None = None


class StoredAction(BaseModel):
    action_id: str
    meeting_id: str
    tool_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str


class ToolExecutionRecordInput(BaseModel):
    action_id: str
    meeting_id: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None


def _client() -> AsyncIOMotorClient:
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongodb_url, uuidRepresentation="standard")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@activity.defn
async def update_meeting_status(payload: UpdateMeetingStatusInput) -> dict[str, Any]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        update: dict[str, Any] = {"status": payload.status, "updated_at": _now()}
        if payload.failure_reason is not None:
            update["failure_reason"] = payload.failure_reason
        result = await db.meetings.update_one(
            {"_id": ObjectId(payload.meeting_id)},
            {"$set": update},
        )
        return {"matched": result.matched_count, "modified": result.modified_count}
    finally:
        client.close()


@activity.defn
async def store_meeting_results(payload: StorageInput) -> dict[str, Any]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]

        update: dict[str, Any] = {"updated_at": _now()}
        if payload.transcript is not None:
            update["transcript"] = payload.transcript
        if payload.executive_summary is not None:
            update["executive_summary"] = payload.executive_summary
        if payload.final_status:
            update["status"] = payload.final_status

        await db.meetings.update_one(
            {"_id": ObjectId(payload.meeting_id)},
            {"$set": update},
        )

        order_to_id: dict[int, str] = {}
        inserted_items = 0
        if payload.items is not None:
            await db.meeting_items.delete_many({"meeting_id": payload.meeting_id})
            docs: list[dict[str, Any]] = []
            for item in payload.items:
                docs.append(
                    {
                        "meeting_id": payload.meeting_id,
                        "order": item.order,
                        "item_type": item.item_type,
                        "title": item.title,
                        "description": item.description,
                        "owner": item.owner,
                        "due_date": item.due_date,
                        "priority": item.priority,
                        "status": item.status,
                        "source_text": item.source_text,
                        "metadata": item.metadata,
                        "created_at": _now(),
                        "updated_at": _now(),
                    }
                )
            if docs:
                result = await db.meeting_items.insert_many(docs)
                inserted_items = len(result.inserted_ids)
                for item, inserted_id in zip(payload.items, result.inserted_ids, strict=False):
                    order_to_id[item.order] = str(inserted_id)

        if payload.proposed_actions is not None:
            if not order_to_id:
                cursor = db.meeting_items.find({"meeting_id": payload.meeting_id})
                existing_items = await cursor.to_list(length=1000)
                order_to_id = {
                    int(item.get("order", 0)): str(item["_id"])
                    for item in existing_items
                    if "order" in item and "_id" in item
                }
            await db.proposed_actions.delete_many({"meeting_id": payload.meeting_id})
            docs = []
            for proposed in payload.proposed_actions:
                docs.append(
                    {
                        "meeting_id": payload.meeting_id,
                        "tool_type": proposed.tool_type,
                        "title": proposed.title,
                        "payload": proposed.payload,
                        "source_item_ids": [
                            order_to_id[order]
                            for order in proposed.source_item_orders
                            if order in order_to_id
                        ],
                        "status": "proposed",
                        "idempotency_key": proposed.idempotency_key,
                        "created_at": _now(),
                        "updated_at": _now(),
                    }
                )
            if docs:
                await db.proposed_actions.insert_many(docs)

        logger.info(
            "Stored meeting results for %s (items=%d, actions=%d)",
            payload.meeting_id,
            inserted_items,
            len(payload.proposed_actions or []),
        )
        return {
            "inserted_items": inserted_items,
            "inserted_actions": len(payload.proposed_actions or []),
        }
    finally:
        client.close()


@activity.defn
async def fetch_meeting_context(meeting_id: str) -> dict[str, Any]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
        if not meeting:
            return {
                "title": None,
                "meeting_date": None,
                "participants": [],
                "existing_transcript": None,
                "existing_executive_summary": None,
            }
        meeting_date = meeting.get("meeting_date")
        return {
            "title": meeting.get("title"),
            "meeting_date": meeting_date.isoformat() if meeting_date else None,
            "participants": meeting.get("participants") or [],
            "existing_transcript": meeting.get("transcript"),
            "existing_executive_summary": meeting.get("executive_summary"),
        }
    finally:
        client.close()


@activity.defn
async def fetch_actions_for_execution(meeting_id: str) -> list[StoredAction]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        cursor = db.proposed_actions.find(
            {"meeting_id": meeting_id, "status": "approved"}
        ).sort("created_at", 1)
        actions = await cursor.to_list(length=200)
        return [
            StoredAction(
                action_id=str(action["_id"]),
                meeting_id=action["meeting_id"],
                tool_type=action["tool_type"],
                title=action["title"],
                payload=action.get("payload") or {},
                idempotency_key=action["idempotency_key"],
            )
            for action in actions
        ]
    finally:
        client.close()


@activity.defn
async def action_status_summary(meeting_id: str) -> dict[str, int]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        statuses = ["proposed", "approved", "rejected", "executing", "executed", "failed"]
        return {
            status: await db.proposed_actions.count_documents(
                {"meeting_id": meeting_id, "status": status}
            )
            for status in statuses
        }
    finally:
        client.close()


@activity.defn
async def mark_action_executing(action_id: str) -> dict[str, Any]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        result = await db.proposed_actions.update_one(
            {"_id": ObjectId(action_id), "status": "approved"},
            {"$set": {"status": "executing", "updated_at": _now()}},
        )
        return {"matched": result.matched_count, "modified": result.modified_count}
    finally:
        client.close()


@activity.defn
async def record_tool_execution(payload: ToolExecutionRecordInput) -> dict[str, Any]:
    settings = get_settings()
    client = _client()
    try:
        db = client[settings.mongodb_database]
        status = "executed" if payload.success else "failed"
        update = {
            "status": status,
            "execution_result": payload.result,
            "failure_reason": payload.failure_reason,
            "executed_at": _now(),
            "updated_at": _now(),
        }
        result = await db.proposed_actions.update_one(
            {"_id": ObjectId(payload.action_id)},
            {"$set": update},
        )
        await db.audit_events.insert_one(
            {
                "meeting_id": payload.meeting_id,
                "action_id": payload.action_id,
                "event_type": "action_executed" if payload.success else "action_failed",
                "actor": "temporal-worker",
                "details": payload.result if payload.success else {"failure": payload.failure_reason},
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
        return {"matched": result.matched_count, "modified": result.modified_count}
    finally:
        client.close()
