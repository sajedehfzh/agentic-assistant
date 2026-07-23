"""Audio upload route. Persists meeting recordings after consent confirmation."""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import (
    get_audit_event_repo,
    get_meeting_item_repo,
    get_meeting_repo,
    get_proposed_action_repo,
)
from app.auth.middleware import get_current_user
from app.auth.provider import AuthenticatedUser
from app.config import Settings, get_settings
from app.models.audit_event import AuditEventCreate, AuditEventType
from app.models.meeting import Meeting, MeetingStatus
from app.repositories.audit_event_repo import AuditEventRepository
from app.repositories.meeting_item_repo import MeetingItemRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.proposed_action_repo import ProposedActionRepository
from app.services.upload_policy import (
    UploadPolicyError,
    ensure_audio_size_limit,
    require_recording_consent,
    validate_audio_content_type,
    validate_audio_filename,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/{meeting_id}/upload", response_model=Meeting)
async def upload_audio(
    meeting_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    repo: Annotated[MeetingRepository, Depends(get_meeting_repo)],
    items_repo: Annotated[MeetingItemRepository, Depends(get_meeting_item_repo)],
    actions_repo: Annotated[ProposedActionRepository, Depends(get_proposed_action_repo)],
    audit_repo: Annotated[AuditEventRepository, Depends(get_audit_event_repo)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
) -> Meeting:
    meeting = await repo.get(meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")

    try:
        require_recording_consent(consent_confirmed)
        suffix = validate_audio_filename(file.filename)
        validate_audio_content_type(file.content_type)
    except UploadPolicyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    max_bytes = settings.max_audio_upload_mb * 1024 * 1024
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{meeting_id}-{uuid.uuid4().hex}{suffix}"
    target_path = uploads_dir / unique_name

    size_bytes = 0
    digest = hashlib.sha256()
    try:
        async with aiofiles.open(target_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size_bytes += len(chunk)
                try:
                    ensure_audio_size_limit(size_bytes, max_bytes)
                except UploadPolicyError:
                    await out.close()
                    target_path.unlink(missing_ok=True)
                    raise
                digest.update(chunk)
                await out.write(chunk)
    except UploadPolicyError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            str(exc),
        ) from exc

    audio_sha256 = digest.hexdigest()
    logger.info("Saved meeting audio %s (%d bytes)", target_path, size_bytes)

    audio_changed = meeting.audio_sha256 != audio_sha256
    if audio_changed:
        await items_repo.delete_for_meeting(meeting_id)
        await actions_repo.delete_for_meeting(meeting_id)
        if meeting.audio_file_path and meeting.audio_file_path != str(target_path):
            try:
                Path(meeting.audio_file_path).unlink(missing_ok=True)
            except OSError:
                pass

    updated = await repo.update(
        meeting_id,
        {
            "audio_file_path": str(target_path),
            "audio_sha256": audio_sha256,
            "status": MeetingStatus.UPLOADED.value,
            "failure_reason": "",
            **(
                {
                    "transcript": "",
                    "executive_summary": "",
                    "temporal_workflow_id": "",
                }
                if audio_changed
                else {}
            ),
        },
    )
    await audit_repo.create(
        AuditEventCreate(
            meeting_id=meeting_id,
            event_type=AuditEventType.CONSENT_CONFIRMED,
            actor=current_user.username,
            details={
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": size_bytes,
                "audio_sha256": audio_sha256,
            },
        ).model_dump()
    )
    assert updated is not None
    return updated
