"""Entry point for the Temporal worker process."""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from activities.meeting_analysis import (
    extract_meeting_information,
    plan_meeting_actions,
)
from activities.storage import (
    action_status_summary,
    fetch_actions_for_execution,
    fetch_meeting_context,
    mark_action_executing,
    record_tool_execution,
    store_meeting_results,
    update_meeting_status,
)
from activities.summarization import summarize_transcript
from activities.tools import execute_tool_action
from activities.transcription import transcribe_audio
from config import get_settings
from workflows.meeting_processing import MeetingProcessingWorkflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")


async def main() -> None:
    settings = get_settings()
    logger.info(
        "Connecting to Temporal at %s (namespace=%s, queue=%s)",
        settings.temporal_address,
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[MeetingProcessingWorkflow],
        activities=[
            transcribe_audio,
            summarize_transcript,
            extract_meeting_information,
            plan_meeting_actions,
            store_meeting_results,
            update_meeting_status,
            fetch_meeting_context,
            fetch_actions_for_execution,
            action_status_summary,
            mark_action_executing,
            execute_tool_action,
            record_tool_execution,
        ],
    )
    logger.info("Worker started — polling task queue %s", settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
