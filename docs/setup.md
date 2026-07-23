# Setup

## Requirements

- Docker and Docker Compose
- An LLM provider key compatible with the OpenRouter-style chat endpoint
- Enough disk space for uploaded recordings and the selected Whisper model

## Environment

Copy `.env.example` to `.env`, then set:

- `OPENROUTER_API_KEY`
- `LLM_MODEL`
- `MAX_AUDIO_UPLOAD_MB` if the 200 MB default is not right for your deployment
- production-safe `AUTH_USERNAME`, `AUTH_PASSWORD`, and `JWT_SECRET_KEY`

Never commit `.env` or provider credentials.

## Run

```bash
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Temporal UI: <http://localhost:8080>

## First Meeting

1. Sign in.
2. Create a meeting with a title, optional date, duration, participants, and notes.
3. Open the meeting.
4. Confirm that all recorded participants consented to recording and AI
   processing.
5. Record audio or upload a supported audio file.
6. Start processing and watch the status move through Temporal.
7. Review transcript, executive summary, extracted meeting information, and
   proposed actions.
8. Approve, reject, edit, bulk approve, or retry proposed actions.

## Privacy Checklist

- Obtain consent before recording or uploading.
- Confirm who can sign in to this deployment.
- Confirm whether the selected LLM/transcription providers are approved for the
  meeting data being processed.
- Delete meetings when their recordings/transcripts/summaries are no longer
  needed.
- Do not store access tokens in source code.
