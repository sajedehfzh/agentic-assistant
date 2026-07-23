"""Generic async repository over a single MongoDB collection.

Concrete repositories subclass `BaseRepository[Model]` and only need to
declare the collection name and Pydantic model. Adding a new collection is
two lines plus the model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_object_id(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value)


class BaseRepository(Generic[T]):
    collection_name: str = ""
    model: type[T]

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        if not self.collection_name:
            raise ValueError(f"{type(self).__name__}.collection_name must be set")
        self._collection: AsyncIOMotorCollection = database[self.collection_name]

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self._collection

    @staticmethod
    def _doc_to_model_dict(doc: dict[str, Any]) -> dict[str, Any]:
        if doc is None:
            return doc
        doc = dict(doc)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    def _to_model(self, doc: dict[str, Any] | None) -> T | None:
        if doc is None:
            return None
        return self.model.model_validate(self._doc_to_model_dict(doc))

    async def create(self, data: dict[str, Any]) -> T:
        payload = dict(data)
        payload.setdefault("created_at", now_utc())
        payload.setdefault("updated_at", now_utc())
        result = await self._collection.insert_one(payload)
        doc = await self._collection.find_one({"_id": result.inserted_id})
        return self._to_model(doc)  # type: ignore[return-value]

    async def get(self, id_: str) -> T | None:
        doc = await self._collection.find_one({"_id": _to_object_id(id_)})
        return self._to_model(doc)

    async def list(
        self,
        filter_: dict[str, Any] | None = None,
        *,
        limit: int = 100,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        cursor = self._collection.find(filter_ or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        return [self._to_model(doc) for doc in await cursor.to_list(length=limit)]  # type: ignore[misc]

    async def update(self, id_: str, data: dict[str, Any]) -> T | None:
        payload = {k: v for k, v in data.items() if v is not None}
        if not payload:
            return await self.get(id_)
        payload["updated_at"] = now_utc()
        await self._collection.update_one(
            {"_id": _to_object_id(id_)},
            {"$set": payload},
        )
        return await self.get(id_)

    async def delete(self, id_: str) -> bool:
        result = await self._collection.delete_one({"_id": _to_object_id(id_)})
        return result.deleted_count > 0

    async def count(self, filter_: dict[str, Any] | None = None) -> int:
        return await self._collection.count_documents(filter_ or {})
