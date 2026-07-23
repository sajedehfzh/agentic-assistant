"""MeetingProcessingWorkflow.

Durably orchestrates meeting processing:

1. transcribe audio, reusing existing transcript when present
2. summarize the transcript into an executive summary
3. extract structured meeting information
4. plan useful external actions without executing them
5. wait for human approvals via Temporal signal
6. execute only approved actions through idempotent tool activities
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.meeting_analysis import (
        ActionPlanningInput,
        ExtractMeetingInformationInput,
        extract_meeting_information,
        plan_meeting_actions,
    )
    from activities.storage import (
        StorageInput,
        ToolExecutionRecordInput,
        UpdateMeetingStatusInput,
        action_status_summary,
        fetch_actions_for_execution,
        fetch_meeting_context,
        mark_action_executing,
        record_tool_execution,
        store_meeting_results,
        update_meeting_status,
    )
    from activities.summarization import SummarizeInput, summarize_transcript
    from activities.tools import ToolExecutionInput, execute_tool_action
    from activities.transcription import TranscribeInput, transcribe_audio


class MeetingProcessingInput(BaseModel):
    meeting_id: str
    audio_path: str
    language: str | None = None


class MeetingProcessingResult(BaseModel):
    meeting_id: str
    status: str
    item_count: int
    proposed_action_count: int


DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
)

LLM_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=300),
    maximum_attempts=6,
)


@workflow.defn
class MeetingProcessingWorkflow:
    def __init__(self) -> None:
        self._action_update_count = 0

    @workflow.signal
    async def action_update(self) -> None:
        self._action_update_count += 1

    @workflow.run
    async def run(self, data: MeetingProcessingInput) -> MeetingProcessingResult:
        item_count = 0
        proposed_action_count = 0
        try:
            await workflow.execute_activity(
                update_meeting_status,
                UpdateMeetingStatusInput(meeting_id=data.meeting_id, status="validating"),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )

            context = await workflow.execute_activity(
                fetch_meeting_context,
                data.meeting_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )
            title = context.get("title")
            meeting_date = context.get("meeting_date")
            participants = context.get("participants") or []
            existing_transcript = context.get("existing_transcript")
            existing_summary = context.get("existing_executive_summary")

            if existing_transcript:
                transcript_text = existing_transcript
                await self._set_status(data.meeting_id, "summarizing")
            else:
                await self._set_status(data.meeting_id, "transcribing")
                transcribe_result = await workflow.execute_activity(
                    transcribe_audio,
                    TranscribeInput(audio_path=data.audio_path, language=data.language),
                    start_to_close_timeout=timedelta(minutes=60),
                    retry_policy=DEFAULT_RETRY,
                    heartbeat_timeout=timedelta(minutes=5),
                )
                transcript_text = transcribe_result.text
                await workflow.execute_activity(
                    store_meeting_results,
                    StorageInput(
                        meeting_id=data.meeting_id,
                        transcript=transcript_text,
                        final_status="summarizing",
                    ),
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=DEFAULT_RETRY,
                )

            if existing_summary:
                executive_summary = existing_summary
                await self._set_status(data.meeting_id, "extracting_information")
            else:
                summarize_result = await workflow.execute_activity(
                    summarize_transcript,
                    SummarizeInput(
                        transcript=transcript_text,
                        title=title,
                        meeting_date=meeting_date,
                        participants=participants,
                    ),
                    start_to_close_timeout=timedelta(minutes=10),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=LLM_RETRY,
                )
                executive_summary = summarize_result.summary
                await workflow.execute_activity(
                    store_meeting_results,
                    StorageInput(
                        meeting_id=data.meeting_id,
                        executive_summary=executive_summary,
                        final_status="extracting_information",
                    ),
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=DEFAULT_RETRY,
                )

            extracted = await workflow.execute_activity(
                extract_meeting_information,
                ExtractMeetingInformationInput(
                    transcript=transcript_text,
                    title=title,
                    meeting_date=meeting_date,
                    participants=participants,
                ),
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=LLM_RETRY,
            )
            item_count = len(extracted.items)
            await workflow.execute_activity(
                store_meeting_results,
                StorageInput(
                    meeting_id=data.meeting_id,
                    items=extracted.items,
                    final_status="planning_actions",
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=DEFAULT_RETRY,
            )

            planned = await workflow.execute_activity(
                plan_meeting_actions,
                ActionPlanningInput(
                    meeting_id=data.meeting_id,
                    transcript=transcript_text,
                    executive_summary=executive_summary,
                    items=extracted.items,
                ),
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=LLM_RETRY,
            )
            proposed_action_count = len(planned.proposed_actions)
            final_status = "awaiting_approval" if planned.proposed_actions else "completed"
            await workflow.execute_activity(
                store_meeting_results,
                StorageInput(
                    meeting_id=data.meeting_id,
                    proposed_actions=planned.proposed_actions,
                    final_status=final_status,
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=DEFAULT_RETRY,
            )

            if not planned.proposed_actions:
                return MeetingProcessingResult(
                    meeting_id=data.meeting_id,
                    status="completed",
                    item_count=item_count,
                    proposed_action_count=0,
                )

            completed_status = await self._approval_loop(data.meeting_id)
            return MeetingProcessingResult(
                meeting_id=data.meeting_id,
                status=completed_status,
                item_count=item_count,
                proposed_action_count=proposed_action_count,
            )

        except Exception as exc:  # noqa: BLE001
            reason = _root_cause_message(exc)
            await workflow.execute_activity(
                update_meeting_status,
                UpdateMeetingStatusInput(
                    meeting_id=data.meeting_id,
                    status="failed",
                    failure_reason=reason[:500],
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )
            raise

    async def _set_status(self, meeting_id: str, status: str) -> None:
        await workflow.execute_activity(
            update_meeting_status,
            UpdateMeetingStatusInput(meeting_id=meeting_id, status=status),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY,
        )

    async def _approval_loop(self, meeting_id: str) -> str:
        seen_signal_count = self._action_update_count
        while True:
            summary = await workflow.execute_activity(
                action_status_summary,
                meeting_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )
            if (
                summary.get("proposed", 0) == 0
                and summary.get("approved", 0) == 0
                and summary.get("executing", 0) == 0
            ):
                final_status = (
                    "completed_with_action_failures"
                    if summary.get("failed", 0) > 0
                    else "completed"
                )
                await self._set_status(meeting_id, final_status)
                return final_status

            approved = await workflow.execute_activity(
                fetch_actions_for_execution,
                meeting_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )
            if approved:
                await self._set_status(meeting_id, "executing_actions")
                for action in approved:
                    await workflow.execute_activity(
                        mark_action_executing,
                        action.action_id,
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=DEFAULT_RETRY,
                    )
                    result = await workflow.execute_activity(
                        execute_tool_action,
                        ToolExecutionInput(
                            action_id=action.action_id,
                            meeting_id=action.meeting_id,
                            tool_type=action.tool_type,
                            title=action.title,
                            payload=action.payload,
                            idempotency_key=action.idempotency_key,
                        ),
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY,
                    )
                    await workflow.execute_activity(
                        record_tool_execution,
                        ToolExecutionRecordInput(
                            action_id=action.action_id,
                            meeting_id=action.meeting_id,
                            success=result.success,
                            result=result.result,
                            failure_reason=result.failure_reason,
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=DEFAULT_RETRY,
                    )
                await self._set_status(meeting_id, "awaiting_approval")
                continue

            await workflow.wait_condition(
                lambda: self._action_update_count > seen_signal_count
            )
            seen_signal_count = self._action_update_count


def _root_cause_message(exc: BaseException) -> str:
    current: BaseException = exc
    while current.__cause__ is not None:
        current = current.__cause__
    return str(current) or type(current).__name__
