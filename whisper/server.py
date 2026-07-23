"""Lightweight Whisper transcription service.

Wraps `faster-whisper` behind a tiny FastAPI app. Two endpoints:

- `POST /transcribe` — multipart upload of an audio file, returns the transcript
- `POST /transcribe-path` — JSON `{ "path": "/uploads/foo.wav" }` to transcribe
  a file already mounted into the container (used by the Temporal worker, which
  shares the `uploads` volume with the API). Avoids re-uploading megabytes of
  audio over the local network.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from faster_whisper import WhisperModel
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("whisper")

MODEL_NAME = os.environ.get("WHISPER_MODEL", "base")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

logger.info("Loading Whisper model %s (device=%s, compute_type=%s)", MODEL_NAME, DEVICE, COMPUTE_TYPE)
model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)
logger.info("Whisper model loaded")

app = FastAPI(title="iwasist Whisper Service", version="0.1.0")


class TranscribePathRequest(BaseModel):
    path: str
    language: str | None = None


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None
    duration: float | None
    segments: list[TranscriptionSegment]


def _transcribe_file(path: str, language: str | None = None) -> dict[str, Any]:
    segments, info = model.transcribe(path, language=language, vad_filter=True)
    seg_list: list[TranscriptionSegment] = []
    full_text_parts: list[str] = []
    for seg in segments:
        seg_list.append(
            TranscriptionSegment(start=seg.start, end=seg.end, text=seg.text.strip())
        )
        full_text_parts.append(seg.text.strip())
    return {
        "text": " ".join(full_text_parts).strip(),
        "language": info.language,
        "duration": info.duration,
        "segments": [s.model_dump() for s in seg_list],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = None,
) -> TranscriptionResponse:
    suffix = Path(file.filename or "").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
    try:
        logger.info("Transcribing uploaded file %s", file.filename)
        result = _transcribe_file(tmp_path, language=language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return TranscriptionResponse(**result)


@app.post("/transcribe-path", response_model=TranscriptionResponse)
async def transcribe_path(payload: TranscribePathRequest) -> TranscriptionResponse:
    if not Path(payload.path).is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {payload.path}")
    logger.info("Transcribing local file %s", payload.path)
    result = _transcribe_file(payload.path, language=payload.language)
    return TranscriptionResponse(**result)
