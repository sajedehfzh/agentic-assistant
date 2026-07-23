# Real Tool Integrations

The app already has the safe control plane for tool calling:

1. `plan_meeting_actions` proposes useful tool actions from the transcript.
2. The user approves, rejects, or edits proposed actions in the UI.
3. The backend records an audit event and signals `MeetingProcessingWorkflow`.
4. The workflow fetches approved actions and calls `execute_tool_action`.
5. Today, `execute_tool_action` is a stub. Real integrations replace or route
   inside that activity.

Keep this invariant: the LLM may propose actions, but it must not execute
external side effects directly. External systems are called only after user
approval and only from Temporal activities.

## Implementation Checklist

For each real tool:

- Add credentials and feature flags to `.env.example`, backend config if needed,
  and worker config.
- Add a provider adapter under `worker/activities/` or a small
  `worker/integrations/` package.
- Route by `tool_type` inside `execute_tool_action`.
- Validate the action payload with a Pydantic model before calling the provider.
- Use `idempotency_key` to prevent duplicate emails, tasks, tickets, events, or
  messages on retries.
- Store provider response identifiers in `execution_result`.
- Return a failed `ToolExecutionResult` instead of raising for optional provider
  failures that should not fail the whole meeting workflow.
- Add tests for payload validation, idempotency behavior, provider errors, and
  audit persistence.

## Gmail Example

Use Gmail as the first real integration only for approved `email` actions.
Start with draft creation rather than direct send. It is safer, easier to
review, and fits the approval-first product model.

### Google Setup

1. Create or choose a Google Cloud project.
2. Enable the Gmail API in that project.
3. Configure the OAuth consent screen.
4. Create OAuth credentials for the app.
5. Choose the narrowest Gmail scope that supports the behavior:
   - Draft-only first pass: `https://www.googleapis.com/auth/gmail.compose`
   - Direct send later: `https://www.googleapis.com/auth/gmail.send`
6. Keep client secrets, refresh tokens, and access tokens outside source code.

Google classifies broad Gmail access carefully. Some Gmail scopes are sensitive
or restricted and can require OAuth verification or security review, especially
for public apps or server-side storage/transmission of restricted-scope data.

Official references:

- [Google Workspace API setup](https://developers.google.com/workspace/guides/get-started)
- [Create Google Workspace credentials](https://developers.google.com/workspace/guides/create-credentials)
- [Gmail API Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [Create and send Gmail messages](https://developers.google.com/workspace/gmail/api/guides/sending)

### Environment

Add these values to `.env` when implementing Gmail:

```dotenv
GMAIL_ENABLED=false
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REDIRECT_URI=http://localhost:8000/api/integrations/google/oauth/callback
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.compose
GMAIL_TOKEN_ENCRYPTION_KEY=
```

For development, you can store a test refresh token manually in your secret
store. For production, add a real OAuth connect flow so each user authorizes
their own mailbox.

### Proposed Payload Shape

Action planning should produce email payloads like this:

```json
{
  "to": ["sara@example.com"],
  "cc": [],
  "subject": "Follow-up from product planning sync",
  "body": "Hi Sara,\n\nHere are the agreed next steps...",
  "mode": "draft"
}
```

Reject `email` actions missing `to`, `subject`, or `body`. Default to
`mode=draft`; require a separate explicit setting before allowing `send`.

### Adapter Sketch

Replace the stub path for `tool_type == "email"`:

1. Load and decrypt the user's Gmail credentials.
2. Refresh the access token if needed.
3. Build an RFC 2822/MIME email.
4. Base64URL encode the message.
5. Call Gmail `users.drafts.create` for `mode=draft`.
6. Store `draft_id`, `message_id`, provider name, and idempotency key in
   `execution_result`.

Do not send email directly until the UI and API distinguish "approve draft
creation" from "approve sending".

### Recommended Code Changes

- Add `google-api-python-client`, `google-auth`, and
  `google-auth-oauthlib` to `worker/pyproject.toml`.
- Add `GmailEmailPayload` and `GmailToolAdapter`.
- Update `execute_tool_action` to call the Gmail adapter when:
  - `GMAIL_ENABLED=true`
  - `payload.tool_type == "email"`
  - payload validation succeeds
- Keep the existing stub fallback when Gmail is disabled.
- Add tests using a fake Gmail client; do not call Google in unit tests.

## Other Tools

Follow the same pattern:

- `calendar_event`: Google Calendar or Outlook Calendar, usually create/update
  event with an idempotency key in the event metadata.
- `task`: project-management adapter, usually create/update task and store the
  provider task id.
- `slack_message` / `teams_message`: post approved messages only, store channel
  and message ids.
- `notion_page` / `document_note`: create or update a notes page and store the
  page/document id.
- `jira_ticket`: create issue only after approval, store issue key and URL.

Each tool should use least-privilege credentials, explicit payload validation,
audited approval, idempotent execution, and retry-safe error handling.
