"""Thin wrapper around the Temporal client used by API routes.

Routes never talk to Temporal directly — they go through this service so
swapping or stubbing the workflow engine stays trivial.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.contrib.pydantic import pydantic_data_converter

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class TemporalService:
    _client: Optional[Client] = None

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    async def _get_client(self) -> Client:
        if self._client is None:
            logger.info("Connecting to Temporal at %s", self._settings.temporal_address)
            self._client = await Client.connect(
                self._settings.temporal_address,
                namespace=self._settings.temporal_namespace,
                data_converter=pydantic_data_converter,
            )
        return self._client

    async def start_meeting_processing(
        self,
        *,
        meeting_id: str,
        audio_path: str,
    ) -> str:
        """Kick off the MeetingProcessingWorkflow. Returns the workflow id.

        If a workflow with the same id is already running (e.g. user clicked
        "restart" while a previous attempt was in flight), it is terminated
        atomically and a new run is started. Completed/failed runs are simply
        replaced.
        """
        client = await self._get_client()
        workflow_id = f"meeting-processing-{meeting_id}"
        await client.start_workflow(
            "MeetingProcessingWorkflow",
            {
                "meeting_id": meeting_id,
                "audio_path": audio_path,
            },
            id=workflow_id,
            task_queue=self._settings.temporal_task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.TERMINATE_EXISTING,
        )
        logger.info(
            "Started workflow %s for meeting %s on queue %s",
            workflow_id,
            meeting_id,
            self._settings.temporal_task_queue,
        )
        return workflow_id

    async def signal_action_update(self, workflow_id: str) -> None:
        """Notify a waiting meeting workflow that action approvals changed."""
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("action_update")

    async def describe_workflow(self, workflow_id: str) -> dict[str, Any]:
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        return {
            "workflow_id": desc.id,
            "run_id": desc.run_id,
            "status": desc.status.name if desc.status else None,
            "task_queue": desc.task_queue,
        }


_temporal_service: TemporalService | None = None


def get_temporal_service() -> TemporalService:
    global _temporal_service
    if _temporal_service is None:
        _temporal_service = TemporalService()
    return _temporal_service
