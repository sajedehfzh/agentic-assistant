"""Transcription activity — calls the local Whisper service.

Whisper transcription can take many minutes (the very first call also triggers
a one-time model download of ~150 MB). Temporal will mark an activity as
heartbeat-timed-out if it goes silent for too long, so we spawn a background
task that heartbeats periodically while the HTTP request is in flight.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel
from temporalio import activity

from config import get_settings

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 15


class TranscribeInput(BaseModel):
    audio_path: str
    language: Optional[str] = None


class TranscribeResult(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


async def _heartbeat_loop(stage: str) -> None:
    """Tell Temporal we're alive every HEARTBEAT_INTERVAL_SECONDS seconds."""
    elapsed = 0
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            elapsed += HEARTBEAT_INTERVAL_SECONDS
            activity.heartbeat({"stage": stage, "elapsed_seconds": elapsed})
    except asyncio.CancelledError:
        return


@activity.defn
async def transcribe_audio(payload: TranscribeInput) -> TranscribeResult:
    settings = get_settings()
    url = f"{settings.whisper_service_url}/transcribe-path"
    logger.info("Transcribing %s via %s", payload.audio_path, url)

    activity.heartbeat({"stage": "starting", "audio_path": payload.audio_path})

    heartbeat_task = asyncio.create_task(_heartbeat_loop("calling_whisper"))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1800.0)) as client:
            response = await client.post(
                url,
                json={"path": payload.audio_path, "language": payload.language},
            )
            response.raise_for_status()
            data = response.json()
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    activity.heartbeat({"stage": "done"})
    return TranscribeResult(
        text=data.get("text", ""),
        language=data.get("language"),
        duration=data.get("duration"),
    )
