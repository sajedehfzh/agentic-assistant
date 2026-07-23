import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import MeetingForm from '../components/MeetingForm';
import { deleteMeeting, listMeetings } from '../services/meetings';
import type { Meeting } from '../types';

function formatDate(value?: string | null): string {
  if (!value) return 'Unscheduled';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatDuration(seconds?: number | null): string {
  if (!seconds) return 'Duration not set';
  const minutes = Math.round(seconds / 60);
  return `${minutes} min`;
}

export default function DashboardPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      setMeetings(await listMeetings());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onDelete(id: string) {
    if (!confirm('Delete this meeting, audio, transcript, summary, actions, and audit records?')) {
      return;
    }
    await deleteMeeting(id);
    await refresh();
  }

  return (
    <div>
      <MeetingForm onCreated={refresh} />

      <h2>Meetings</h2>
      {loading && <p className="muted">Loading...</p>}
      {!loading && meetings.length === 0 && (
        <p className="muted">No meetings yet. Create one above to upload audio.</p>
      )}

      {meetings.map((meeting) => (
        <div key={meeting.id} className="card">
          <div className="meeting-card-header">
            <div>
              <h3 style={{ margin: 0 }}>
                <Link to={`/meetings/${meeting.id}`}>{meeting.title}</Link>
              </h3>
              <div className="muted" style={{ marginTop: '0.25rem' }}>
                {formatDate(meeting.meeting_date)} · {formatDuration(meeting.duration_seconds)}
              </div>
              {meeting.participants.length > 0 && (
                <div className="badge-row" style={{ marginTop: '0.55rem' }}>
                  {meeting.participants.map((participant) => (
                    <span key={participant} className="badge">
                      {participant}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="actions">
              <Link to={`/meetings/${meeting.id}`}>
                <button className="ghost">Open</button>
              </Link>
              <button className="danger" onClick={() => onDelete(meeting.id)}>
                Delete
              </button>
            </div>
          </div>
          <div style={{ marginTop: '0.75rem' }}>
            <span className={`badge status-${meeting.status}`}>{meeting.status}</span>
            {meeting.audio_file_path && (
              <span className="muted" style={{ marginLeft: '0.5rem' }}>
                audio uploaded
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
