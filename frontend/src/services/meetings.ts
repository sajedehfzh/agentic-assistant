import { api } from './api';
import type { Meeting, MeetingItem, ProposedAction, ToolType } from '../types';

export interface MeetingCreate {
  title: string;
  meeting_date?: string;
  duration_seconds?: number;
  participants: string[];
  notes?: string;
}

export type MeetingUpdate = Partial<MeetingCreate>;

export async function listMeetings(): Promise<Meeting[]> {
  const { data } = await api.get<Meeting[]>('/api/meetings');
  return data;
}

export async function createMeeting(payload: MeetingCreate): Promise<Meeting> {
  const { data } = await api.post<Meeting>('/api/meetings', payload);
  return data;
}

export async function getMeeting(id: string): Promise<Meeting> {
  const { data } = await api.get<Meeting>(`/api/meetings/${id}`);
  return data;
}

export async function updateMeeting(id: string, payload: MeetingUpdate): Promise<Meeting> {
  const { data } = await api.patch<Meeting>(`/api/meetings/${id}`, payload);
  return data;
}

export async function deleteMeeting(id: string): Promise<void> {
  await api.delete(`/api/meetings/${id}`);
}

export async function uploadMeetingAudio(
  id: string,
  file: Blob,
  filename = 'recording.webm',
  consentConfirmed: boolean,
): Promise<Meeting> {
  const form = new FormData();
  form.append('file', file, filename);
  form.append('consent_confirmed', consentConfirmed ? 'true' : 'false');
  const { data } = await api.post<Meeting>(`/api/audio/${id}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export interface AnalysisStartResponse {
  meeting_id: string;
  workflow_id: string;
  status: string;
}

export async function startAnalysis(id: string): Promise<AnalysisStartResponse> {
  const { data } = await api.post<AnalysisStartResponse>(`/api/analysis/${id}/start`);
  return data;
}

export interface AnalysisResult {
  meeting: Meeting;
  items: MeetingItem[];
  proposed_actions: ProposedAction[];
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  const { data } = await api.get<AnalysisResult>(`/api/analysis/${id}`);
  return data;
}

export interface ActionEdit {
  tool_type?: ToolType;
  title?: string;
  payload?: Record<string, unknown>;
  source_item_ids?: string[];
}

export async function editAction(id: string, payload: ActionEdit): Promise<ProposedAction> {
  const { data } = await api.patch<ProposedAction>(`/api/actions/${id}`, payload);
  return data;
}

export async function approveAction(id: string): Promise<ProposedAction> {
  const { data } = await api.post<ProposedAction>(`/api/actions/${id}/approve`);
  return data;
}

export async function rejectAction(id: string): Promise<ProposedAction> {
  const { data } = await api.post<ProposedAction>(`/api/actions/${id}/reject`);
  return data;
}

export async function retryAction(id: string): Promise<ProposedAction> {
  const { data } = await api.post<ProposedAction>(`/api/actions/${id}/retry`);
  return data;
}

export async function bulkApproveMeetingActions(meetingId: string): Promise<ProposedAction[]> {
  const { data } = await api.post<ProposedAction[]>('/api/actions/bulk-approve', {
    meeting_id: meetingId,
  });
  return data;
}
