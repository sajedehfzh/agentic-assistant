# API

All application routes except auth require a Bearer token.

## Meetings

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/meetings` | List recent meetings |
| `POST` | `/api/meetings` | Create a meeting |
| `GET` | `/api/meetings/{meeting_id}` | Get one meeting |
| `PATCH` | `/api/meetings/{meeting_id}` | Update meeting metadata/status fields |
| `DELETE` | `/api/meetings/{meeting_id}` | Delete meeting data, derived records, audit rows, and stored audio |

Meeting records include `title`, `meeting_date`, `duration_seconds`,
`participants`, `notes`, `status`, `audio_file_path`, `audio_sha256`,
`transcript`, `executive_summary`, `temporal_workflow_id`, and
`failure_reason`.

## Audio

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/audio/{meeting_id}/upload` | Multipart upload with `file` and `consent_confirmed=true` |

The upload route validates extension, content type, and size. It streams the
file into the uploads volume while computing SHA-256. If the audio hash changes,
previous transcript, summary, extracted items, proposed actions, and workflow id
are cleared so the next processing run reflects the new recording.

## Analysis

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/analysis/{meeting_id}/start` | Start or restart `MeetingProcessingWorkflow` |
| `GET` | `/api/analysis/{meeting_id}` | Return `{meeting, items, proposed_actions}` |
| `GET` | `/api/analysis/{meeting_id}/workflow` | Describe the associated Temporal workflow |

Meeting statuses are `created`, `uploaded`, `validating`, `transcribing`,
`summarizing`, `extracting_information`, `planning_actions`,
`awaiting_approval`, `executing_actions`, `completed`,
`completed_with_action_failures`, and `failed`.

## Proposed Actions

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/actions?meeting_id=...` | List proposed actions |
| `PATCH` | `/api/actions/{action_id}` | Edit tool type, title, payload, or source item ids |
| `POST` | `/api/actions/{action_id}/approve` | Approve one proposed or failed action |
| `POST` | `/api/actions/{action_id}/reject` | Reject one proposed, approved, or failed action |
| `POST` | `/api/actions/{action_id}/retry` | Move a failed action back to approved for retry |
| `POST` | `/api/actions/bulk-approve` | Approve all proposed/failed actions for a meeting or selected ids |

Supported `tool_type` values are `calendar_event`, `reminder`, `task`,
`notion_page`, `jira_ticket`, `email`, `slack_message`, `teams_message`, and
`document_note`. Current adapters are approval-gated stubs and do not call live
external providers. See [Real Tool Integrations](tool-integrations.md) before
turning any `tool_type` into a live provider call.
