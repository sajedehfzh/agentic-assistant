"""Tests for consent and file-safety policy on meeting audio uploads."""

from __future__ import annotations

import pytest

from app.services.upload_policy import (
    UploadPolicyError,
    ensure_audio_size_limit,
    require_recording_consent,
    validate_audio_content_type,
    validate_audio_filename,
)


def test_upload_requires_participant_consent() -> None:
    with pytest.raises(UploadPolicyError, match="consent"):
        require_recording_consent(False)

    require_recording_consent(True)


def test_audio_filename_must_use_supported_extension() -> None:
    assert validate_audio_filename("meeting.webm") == ".webm"
    assert validate_audio_filename("meeting.MP3") == ".mp3"

    with pytest.raises(UploadPolicyError, match="Unsupported audio format"):
        validate_audio_filename("notes.txt")


def test_audio_content_type_allows_audio_and_known_video_containers() -> None:
    validate_audio_content_type("audio/webm; codecs=opus")
    validate_audio_content_type("video/mp4")

    with pytest.raises(UploadPolicyError, match="Unsupported media type"):
        validate_audio_content_type("text/plain")


def test_audio_size_limit_is_enforced() -> None:
    ensure_audio_size_limit(10, 10)

    with pytest.raises(UploadPolicyError, match="too large"):
        ensure_audio_size_limit(11, 10)
