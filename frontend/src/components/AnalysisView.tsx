import { useMemo, useState } from 'react';
import type { Meeting, MeetingItem, MeetingItemType, ProposedAction, ToolType } from '../types';
import Markdown from './Markdown';

interface ActionEditPayload {
  tool_type?: ToolType;
  title?: string;
  payload?: Record<string, unknown>;
}

interface Props {
  meeting: Meeting;
  items: MeetingItem[];
  actions: ProposedAction[];
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onRetry: (id: string) => Promise<void>;
  onBulkApprove: () => Promise<void>;
  onEdit: (id: string, update: ActionEditPayload) => Promise<void>;
}

const ITEM_LABELS: Record<MeetingItemType, string> = {
  discussion_point: 'Discussion points',
  decision: 'Decisions',
  action_item: 'Action items',
  follow_up: 'Follow-ups',
  open_question: 'Open questions',
  risk: 'Risks',
  blocker: 'Blockers',
  dependency: 'Dependencies',
  important_date: 'Important dates',
  reference: 'References',
};

const TOOL_LABELS: Record<ToolType, string> = {
  calendar_event: 'Calendar event',
  reminder: 'Reminder',
  task: 'Task',
  notion_page: 'Notion page',
  jira_ticket: 'Jira ticket',
  email: 'Email',
  slack_message: 'Slack message',
  teams_message: 'Teams message',
  document_note: 'Document note',
};

const TOOL_OPTIONS = Object.keys(TOOL_LABELS) as ToolType[];

export default function AnalysisView({
  meeting,
  items,
  actions,
  onApprove,
  onReject,
  onRetry,
  onBulkApprove,
  onEdit,
}: Props) {
  const grouped = useMemo(() => {
    const result = new Map<MeetingItemType, MeetingItem[]>();
    for (const item of items) {
      const bucket = result.get(item.item_type) ?? [];
      bucket.push(item);
      result.set(item.item_type, bucket);
    }
    return result;
  }, [items]);

  const pendingCount = actions.filter((action) => action.status === 'proposed').length;

  return (
    <div>
      {meeting.executive_summary && (
        <div className="card">
          <h3>Executive summary</h3>
          <Markdown>{meeting.executive_summary}</Markdown>
        </div>
      )}

      {items.length > 0 && (
        <div className="card">
          <h3>Extracted meeting information</h3>
          {[...grouped.entries()].map(([type, bucket]) => (
            <section key={type} className="item-section">
              <h4>{ITEM_LABELS[type]}</h4>
              <div className="item-list">
                {bucket.map((item) => (
                  <MeetingItemRow key={item.id} item={item} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {actions.length > 0 && (
        <div className="card">
          <div className="section-header">
            <h3>Proposed actions</h3>
            {pendingCount > 0 && (
              <button className="ghost" onClick={() => void onBulkApprove()}>
                Approve all proposed
              </button>
            )}
          </div>
          <div className="action-list">
            {actions.map((action) => (
              <ActionRow
                key={action.id}
                action={action}
                onApprove={onApprove}
                onReject={onReject}
                onRetry={onRetry}
                onEdit={onEdit}
              />
            ))}
          </div>
        </div>
      )}

      {meeting.transcript && (
        <details className="card">
          <summary>
            <strong>Full transcript</strong>
          </summary>
          <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.75rem' }}>
            {meeting.transcript}
          </p>
        </details>
      )}
    </div>
  );
}

function MeetingItemRow({ item }: { item: MeetingItem }) {
  return (
    <div className="meeting-item">
      <div className="meeting-item-title">
        <strong>{item.title}</strong>
        {item.priority && <span className={`badge priority-${item.priority}`}>{item.priority}</span>}
        <span className={`badge item-status-${item.status}`}>{item.status}</span>
      </div>
      {item.description && <p>{item.description}</p>}
      <div className="meeting-item-meta">
        {item.owner && <span>Owner: {item.owner}</span>}
        {item.due_date && <span>Due: {item.due_date}</span>}
      </div>
      {item.source_text && <p className="muted">Source: {item.source_text}</p>}
    </div>
  );
}

function ActionRow({
  action,
  onApprove,
  onReject,
  onRetry,
  onEdit,
}: {
  action: ProposedAction;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onRetry: (id: string) => Promise<void>;
  onEdit: (id: string, update: ActionEditPayload) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [toolType, setToolType] = useState<ToolType>(action.tool_type);
  const [title, setTitle] = useState(action.title);
  const [payloadText, setPayloadText] = useState(JSON.stringify(action.payload, null, 2));
  const [error, setError] = useState<string | null>(null);
  const canApprove = action.status === 'proposed' || action.status === 'failed';
  const canReject =
    action.status === 'proposed' || action.status === 'approved' || action.status === 'failed';
  const canEdit = action.status === 'proposed' || action.status === 'failed';

  async function saveEdit() {
    setError(null);
    try {
      const parsed = JSON.parse(payloadText) as Record<string, unknown>;
      await onEdit(action.id, { tool_type: toolType, title, payload: parsed });
      setEditing(false);
    } catch (err) {
      setError(err instanceof SyntaxError ? 'Payload must be valid JSON.' : 'Failed to save action.');
    }
  }

  return (
    <div className="proposed-action">
      <div className="section-header">
        <div>
          <strong>{action.title}</strong>
          <div className="muted">
            {TOOL_LABELS[action.tool_type]} · {action.status}
          </div>
        </div>
        <span className={`badge action-status-${action.status}`}>{action.status}</span>
      </div>

      {editing ? (
        <div className="edit-action">
          {error && <div className="error-banner">{error}</div>}
          <label>Tool</label>
          <select value={toolType} onChange={(e) => setToolType(e.target.value as ToolType)}>
            {TOOL_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {TOOL_LABELS[option]}
              </option>
            ))}
          </select>
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
          <label>Payload JSON</label>
          <textarea
            rows={7}
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
          />
          <div className="actions">
            <button onClick={() => void saveEdit()}>Save</button>
            <button className="ghost" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <pre className="payload-preview">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      )}

      {action.failure_reason && <div className="error-banner">{action.failure_reason}</div>}
      {action.execution_result && (
        <div className="success-banner">
          {String(action.execution_result.message ?? 'Stub action recorded.')}
        </div>
      )}

      <div className="actions">
        {canApprove && (
          <button onClick={() => void onApprove(action.id)}>Approve</button>
        )}
        {canReject && (
          <button className="danger" onClick={() => void onReject(action.id)}>
            Reject
          </button>
        )}
        {canEdit && (
          <button className="ghost" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
        {action.status === 'failed' && (
          <button className="ghost" onClick={() => void onRetry(action.id)}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
