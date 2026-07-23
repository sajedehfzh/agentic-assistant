"""Summarization activity — sends the meeting transcript to the LLM."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from temporalio import activity

from activities._llm import chat

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are an expert meeting assistant. Produce a clear, structured "
    "executive summary of a meeting transcript. Capture the purpose, main "
    "discussion points, decisions, unresolved questions, risks, and next "
    "steps. Keep it concise and useful for someone who did not attend."
)


class SummarizeInput(BaseModel):
    transcript: str
    title: str | None = None
    meeting_date: str | None = None
    participants: list[str] = Field(default_factory=list)


class SummarizeResult(BaseModel):
    summary: str


@activity.defn
async def summarize_transcript(payload: SummarizeInput) -> SummarizeResult:
    if not payload.transcript.strip():
        return SummarizeResult(summary="(empty transcript)")
    user = (
        f"Meeting title: {payload.title or 'unknown'}\n"
        f"Meeting date: {payload.meeting_date or 'unknown'}\n"
        f"Participants: {', '.join(payload.participants) or 'unknown'}\n\n"
        "Transcript:\n"
        f"{payload.transcript}"
    )
    summary = await chat(system=SYSTEM_PROMPT, user=user, temperature=0.2, max_tokens=900)
    return SummarizeResult(summary=summary.strip())
