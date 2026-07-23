"""FastAPI dependencies — wire repositories from the MongoDB handle."""

from __future__ import annotations

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.repositories.audit_event_repo import AuditEventRepository
from app.repositories.meeting_item_repo import MeetingItemRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.proposed_action_repo import ProposedActionRepository


def db_dependency() -> AsyncIOMotorDatabase:
    return get_database()


def get_meeting_repo(db: AsyncIOMotorDatabase = Depends(db_dependency)) -> MeetingRepository:
    return MeetingRepository(db)


def get_meeting_item_repo(
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> MeetingItemRepository:
    return MeetingItemRepository(db)


def get_proposed_action_repo(
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> ProposedActionRepository:
    return ProposedActionRepository(db)


def get_audit_event_repo(
    db: AsyncIOMotorDatabase = Depends(db_dependency),
) -> AuditEventRepository:
    return AuditEventRepository(db)
