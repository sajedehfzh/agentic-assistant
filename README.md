# Meeting Assistant (iwasist)

> Upload or record meeting audio, transcribe it, summarize it, extract decisions
> and action items, and prepare approval-gated follow-up actions.

This project is a self-hosted meeting assistant built with FastAPI, React,
MongoDB, Whisper, and Temporal. It processes meeting recordings into:

- transcript and executive summary
- discussion points, decisions, action items, owners, deadlines, risks, blockers,
  dependencies, open questions, important dates, and external references
- proposed actions such as calendar events, reminders, tasks, tickets, notes,
  email drafts, and team messages
- audit records for consent, approvals, edits, rejections, retries, and tool
  execution attempts

External actions are not executed automatically. By default, the app creates an
approval queue. A user must approve, reject, or edit proposed actions before the
Temporal workflow records a stub execution. Real provider integrations can be
added behind the same tool interface later. See
[Real Tool Integrations](docs/tool-integrations.md) for the Gmail-style adapter
path and [Agentic Meeting And Event Assistant](docs/agentic-meeting-events.md)
for the meeting/event action rules.

## Consent And Privacy

Only upload or record a meeting after all participants whose voices are captured
have agreed to both recording and AI processing. The application includes a
required confirmation checkbox before any audio upload.

Access is protected by the app's authentication layer. Anyone who can sign in to
this deployment can access meetings, recordings, transcripts, summaries,
extracted items, proposed actions, and audit records unless you add stricter
authorization rules.

Recordings are stored in the configured uploads directory or Docker volume.
Transcripts, summaries, extracted meeting items, proposed actions, and audit
events are stored in MongoDB. Data is retained until the user deletes the
meeting. Deleting a meeting removes meeting metadata, transcript, summary,
extracted items, proposed actions, audit records, and the stored audio file when
the file is still available.

The default stack uses a local Whisper service for transcription and sends
transcripts to the configured LLM provider for summarization, information
extraction, and action planning. In the provided `.env.example`, that provider
is OpenRouter. Do not record or upload sensitive, confidential, regulated, or
personal information unless you are authorized to do so and your deployment's
provider configuration is approved for that data.

Secrets and provider tokens must not be committed to source code. Use `.env`,
deployment secrets, or your platform's secret manager, and grant external tools
the minimum permissions needed.

## Architecture

The backend stores meetings in MongoDB and starts `MeetingProcessingWorkflow` on
Temporal. The workflow is durable, retryable, and safe to resume after worker
failures. Deterministic workflow code coordinates non-deterministic activities:

1. validate and store uploaded audio
2. transcribe via Whisper
3. summarize with an LLM
4. extract structured meeting information
5. plan useful external actions
6. wait for human approval via Temporal signal
7. execute approved actions through idempotent stub tool activities
8. persist results and audit events

The React frontend lets users create meetings, upload or record audio after
consent confirmation, start processing, review extracted information, and manage
the approval queue.

## Quick Start

1. Copy environment settings:

   ```bash
   cp .env.example .env
   ```

2. Fill in `OPENROUTER_API_KEY` or configure another compatible LLM endpoint.

3. Start the stack:

   ```bash
   docker compose up --build
   ```

4. Open:

   - Frontend: <http://localhost:3000>
   - Backend API: <http://localhost:8000/docs>
   - Temporal UI: <http://localhost:8080>

5. Sign in with the default development credentials from `.env.example`
   (`admin` / `admin`) and replace them before sharing the deployment.

## Main Workflow

1. Create a meeting with title, optional date, duration, participants, and notes.
2. Open the meeting.
3. Confirm participant consent.
4. Record audio in the browser or upload an audio file.
5. Start processing.
6. Review the transcript, executive summary, extracted meeting information, and
   proposed actions.
7. Approve, reject, edit, bulk approve, or retry proposed actions.

Supported upload extensions: `mp3`, `wav`, `m4a`, `mp4`, `webm`, `ogg`, and
`flac`. The default max upload size is 200 MB (`MAX_AUDIO_UPLOAD_MB`).
