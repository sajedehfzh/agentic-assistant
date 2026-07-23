"""Shared model helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MongoModel(BaseModel):
    """Base model for documents persisted in MongoDB.

    `id` is the string form of MongoDB's `_id`. Repositories convert `_id` →
    `id` when hydrating models (see `BaseRepository._doc_to_model_dict`), so
    the field name is the canonical form on the wire too. We deliberately do
    NOT alias to `_id` here, otherwise FastAPI's default `by_alias=True`
    response serialization would leak Mongo's internal name to clients.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    id: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any):  # type: ignore[override]
        if isinstance(obj, dict) and "_id" in obj and "id" not in obj:
            obj = {**obj, "id": str(obj.pop("_id"))}
        return super().model_validate(obj, **kwargs)
