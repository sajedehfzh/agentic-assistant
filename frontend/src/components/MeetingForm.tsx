import { useState } from 'react';
import { createMeeting } from '../services/meetings';
import type { Meeting } from '../types';

interface Props {
  onCreated: (meeting: Meeting) => void;
}

function parseParticipants(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function MeetingForm({ onCreated }: Props) {
  const [title, setTitle] = useState('');
  const [meetingDate, setMeetingDate] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');
  const [participants, setParticipants] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await createMeeting({
        title,
        meeting_date: meetingDate ? new Date(meetingDate).toISOString() : undefined,
        duration_seconds: durationMinutes
          ? Math.max(0, Math.round(Number(durationMinutes) * 60))
          : undefined,
        participants: parseParticipants(participants),
        notes: notes || undefined,
      });
      onCreated(created);
      setTitle('');
      setMeetingDate('');
      setDurationMinutes('');
      setParticipants('');
      setNotes('');
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to create meeting';
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card">
      <h2>New meeting</h2>
      {error && <div className="error-banner">{error}</div>}
      <div className="row">
        <div>
          <label>Title *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Product planning sync"
            required
          />
        </div>
        <div>
          <label>Date and time</label>
          <input
            type="datetime-local"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
          />
        </div>
        <div>
          <label>Duration minutes</label>
          <input
            type="number"
            min={0}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            placeholder="45"
          />
        </div>
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label>Participants</label>
        <input
          value={participants}
          onChange={(e) => setParticipants(e.target.value)}
          placeholder="Sara, Leo, Priya"
        />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label>Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional context for the meeting"
          rows={3}
        />
      </div>
      <div className="actions" style={{ marginTop: '0.75rem' }}>
        <button type="submit" disabled={submitting || !title.trim()}>
          {submitting ? 'Saving...' : 'Create meeting'}
        </button>
      </div>
    </form>
  );
}
