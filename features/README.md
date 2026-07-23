# Feature Backlog

> The application is now a meeting assistant for consent-based recording
> processing, structured summaries, extracted follow-ups, and approval-gated
> external actions.

## Current

- Create meetings with title, date, duration, participants, and notes
- Upload or record audio after participant-consent confirmation
- Transcribe meeting audio
- Generate executive summaries
- Extract discussion points, decisions, action items, owners, deadlines,
  follow-ups, open questions, risks, blockers, dependencies, dates, and
  references
- Propose external actions only when useful
- Require human approval by default
- Record approval and stub tool execution audit events

## Next

- [ ] Real Google Calendar adapter
- [ ] Real reminder/notification adapter
- [ ] Task-system adapter with idempotent create/update behavior
- [ ] Notion/Jira/document-system adapters
- [ ] Slack/Teams/email draft adapters
- [ ] Per-meeting access controls
- [ ] Configurable retention windows and scheduled deletion
- [ ] Redaction options for sensitive transcript segments
- [ ] Search across meetings, owners, decisions, risks, and references
