"""Validation helpers for meeting-audio uploads."""

from __future__ import annotations

from pathlib import Path

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "application/octet-stream",
    "audio/aac",
    "audio/flac",
    "audio/m4a",
    "audio/mp3",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "video/mp4",
    "video/ogg",
    "video/webm",
}


class UploadPolicyError(ValueError):
    """Raised when an upload violates meeting-audio policy."""


def require_recording_consent(consent_confirmed: bool) -> None:
    if not consent_confirmed:
        raise UploadPolicyError(
            "Upload requires confirmation that all recorded participants consented."
        )


def validate_audio_filename(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower() or ".webm"
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        raise UploadPolicyError(f"Unsupported audio format: {suffix}. Allowed: {allowed}.")
    return suffix


def validate_audio_content_type(content_type: str | None) -> None:
    if not content_type:
        return
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized in ALLOWED_AUDIO_CONTENT_TYPES:
        return
    if normalized.startswith("audio/"):
        return
    raise UploadPolicyError(f"Unsupported media type: {normalized}.")


def ensure_audio_size_limit(size_bytes: int, max_bytes: int) -> None:
    if size_bytes > max_bytes:
        raise UploadPolicyError(
            f"Audio file is too large ({size_bytes} bytes). Maximum allowed is {max_bytes} bytes."
        )
