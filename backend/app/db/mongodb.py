"""Async MongoDB client lifecycle.

A single `MongoDB` singleton is initialized at app startup and disposed at
shutdown. Repositories receive a Database handle via FastAPI dependency
injection rather than reaching for globals — that keeps tests easy.
"""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import Settings

logger = logging.getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


mongodb = MongoDB()


async def connect_to_mongo(settings: Settings) -> None:
    logger.info("Connecting to MongoDB at %s", settings.mongodb_url)
    mongodb.client = AsyncIOMotorClient(settings.mongodb_url, uuidRepresentation="standard")
    mongodb.database = mongodb.client[settings.mongodb_database]
    await mongodb.client.admin.command("ping")
    logger.info("MongoDB connection established (db=%s)", settings.mongodb_database)
    await _ensure_indexes()


async def close_mongo_connection() -> None:
    if mongodb.client is not None:
        mongodb.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if mongodb.database is None:
        raise RuntimeError("MongoDB has not been initialized")
    return mongodb.database


async def _ensure_indexes() -> None:
    """Create indexes that we rely on for query performance."""
    db = get_database()
    await db.meetings.create_index("meeting_date")
    await db.meetings.create_index("audio_sha256")
    await db.meeting_items.create_index("meeting_id")
    await db.meeting_items.create_index("item_type")
    await db.meeting_items.create_index("owner")
    await db.proposed_actions.create_index("meeting_id")
    await db.proposed_actions.create_index("status")
    await db.proposed_actions.create_index("idempotency_key", unique=True)
    await db.audit_events.create_index("meeting_id")
    await db.audit_events.create_index("action_id")
