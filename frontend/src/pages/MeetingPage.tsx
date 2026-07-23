import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import AnalysisView from '../components/AnalysisView';
import AudioRecorder from '../components/AudioRecorder';
import FileUpload from '../components/FileUpload';
import {
  approveAction,
  bulkApproveMeetingActions,
  editAction,
  getAnalysis,
  rejectAction,
  retryAction,
  startAnalysis,
  uploadMeetingAudio,
} from '../services/meetings';
import type { Meeting, MeetingItem, ProposedAction } from '../types';

const TERMINAL_STATUSES: Meeting['status'][] = [
  'completed',
  'completed_with_action_failures',
  'failed',
];

const IN_FLIGHT_STATUSES: Meeting['status'][] = [
  'validating',
  'transcribing',
  'summarizing',
  'extracting_information',
  'planning_actions',
  'executing_actions',
];

export default function MeetingPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [items, setItems] = useState<MeetingItem[]>([]);
  const [actions, setActions] = useState<ProposedAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    if (!meetingId) return;
    const result = await getAnalysis(meetingId);
    setMeeting(result.meeting);
    setItems(result.items);
    setActions(result.proposed_actions);
  }, [meetingId]);

  useEffect(() => {
    setLoading(true);
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    if (!meeting) return;
    if (TERMINAL_STATUSES.includes(meeting.status)) {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }
    if (meeting.status === 'created') return;

    if (!pollRef.current) {
      pollRef.current = window.setInterval(() => {
        refresh().catch(() => {});
      }, 4000);
    }
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [meeting, refresh]);

  async function handleUpload(blob: Blob, filename: string) {
    if (!meetingId) return;
    if (!consentConfirmed) {
      setError('Confirm participant consent before uploading meeting audio.');
      return;
    }
    setUploading(true);
    setError(null);
    setInfo(null);
    try {
      const updated = await uploadMeetingAudio(meetingId, blob, filename, consentConfirmed);
      setMeeting(updated);
      setItems([]);
      setActions([]);
      setInfo('Audio uploaded. You can start processing now.');
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Upload failed';
      setError(detail);
    } finally {
      setUploading(false);
    }
  }

  async function handleStart() {
    if (!meetingId) return;
    setStarting(true);
    setError(null);
    setInfo(null);
    try {
      await startAnalysis(meetingId);
      setInfo('Processing started. Temporal will update the meeting as each step completes.');
      await refresh();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to start processing';
      setError(detail);
    } finally {
      setStarting(false);
    }
  }

  async function handleActionChange() {
    await refresh();
  }

  if (loading || !meeting) return <p className="muted">Loading...</p>;

  const canStart =
    meeting.audio_file_path != null &&
    !IN_FLIGHT_STATUSES.includes(meeting.status);

  return (
    <div>
      <p>
        <Link to="/">Back to dashboard</Link>
      </p>

      <div className="card">
        <div className="meeting-card-header">
          <div>
            <h2 style={{ margin: 0 }}>{meeting.title}</h2>
            <div className="muted" style={{ marginTop: '0.25rem' }}>
              {meeting.meeting_date
                ? new Intl.DateTimeFormat(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(meeting.meeting_date))
                : 'Date not set'}
              {meeting.duration_seconds ? ` · ${Math.round(meeting.duration_seconds / 60)} min` : ''}
            </div>
          </div>
          <span className={`badge status-${meeting.status}`}>{meeting.status}</span>
        </div>
        {meeting.participants.length > 0 && (
          <div className="badge-row" style={{ marginTop: '0.75rem' }}>
            {meeting.participants.map((participant) => (
              <span key={participant} className="badge">
                {participant}
              </span>
            ))}
          </div>
        )}
        {meeting.notes && <p className="muted">{meeting.notes}</p>}
        {meeting.failure_reason && (
          <div className="error-banner" style={{ marginTop: '0.75rem' }}>
            {meeting.failure_reason}
          </div>
        )}
      </div>

      <div className="card">
        <h3>Audio</h3>
        {error && <div className="error-banner">{error}</div>}
        {info && <div className="success-banner">{info}</div>}
        {uploading && <p className="muted">Uploading...</p>}

        <label className="checkbox-line">
          <input
            type="checkbox"
            checked={consentConfirmed}
            onChange={(e) => setConsentConfirmed(e.target.checked)}
          />
          <span>
            I confirm that all participants whose voices are recorded consented to this
            recording and AI processing.
          </span>
        </label>

        {meeting.audio_file_path ? (
          <p className="muted">
            File on server: <code>{meeting.audio_file_path.split('/').pop()}</code>
          </p>
        ) : (
          <p className="muted">No audio uploaded yet.</p>
        )}

        <h4>Record</h4>
        <AudioRecorder
          disabled={uploading || !consentConfirmed}
          onRecorded={(blob, mime) => {
            const ext = mime.includes('webm')
              ? 'webm'
              : mime.includes('ogg')
                ? 'ogg'
                : mime.includes('mp4')
                  ? 'mp4'
                  : 'webm';
            void handleUpload(blob, `meeting-recording-${Date.now()}.${ext}`);
          }}
        />

        <h4 style={{ marginTop: '1rem' }}>Upload an audio file</h4>
        <FileUpload
          disabled={uploading || !consentConfirmed}
          onSelected={(file) => void handleUpload(file, file.name)}
        />
      </div>

      <div className="card">
        <h3>Processing</h3>
        <div className="actions" style={{ marginBottom: '0.75rem' }}>
          <button onClick={handleStart} disabled={!canStart || starting}>
            {starting ? 'Starting...' : 'Start / restart processing'}
          </button>
          <button className="ghost" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
        {!meeting.audio_file_path && <p className="muted">Upload audio above first.</p>}
      </div>

      <AnalysisView
        meeting={meeting}
        items={items}
        actions={actions}
        onApprove={async (id) => {
          await approveAction(id);
          await handleActionChange();
        }}
        onReject={async (id) => {
          await rejectAction(id);
          await handleActionChange();
        }}
        onRetry={async (id) => {
          await retryAction(id);
          await handleActionChange();
        }}
        onBulkApprove={async () => {
          await bulkApproveMeetingActions(meeting.id);
          await handleActionChange();
        }}
        onEdit={async (id, update) => {
          await editAction(id, update);
          await handleActionChange();
        }}
      />
    </div>
  );
}
