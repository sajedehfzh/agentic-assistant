export type MeetingStatus =
  | 'created'
  | 'uploaded'
  | 'validating'
  | 'transcribing'
  | 'summarizing'
  | 'extracting_information'
  | 'planning_actions'
  | 'awaiting_approval'
  | 'executing_actions'
  | 'completed'
  | 'completed_with_action_failures'
  | 'failed';

export interface Meeting {
  id: string;
  title: string;
  meeting_date?: string | null;
  duration_seconds?: number | null;
  participants: string[];
  notes?: string | null;
  status: MeetingStatus;
  audio_file_path?: string | null;
  audio_sha256?: string | null;
  transcript?: string | null;
  executive_summary?: string | null;
  temporal_workflow_id?: string | null;
  failure_reason?: string | null;
  created_at?: string;
  updated_at?: string;
}

export type MeetingItemType =
  | 'discussion_point'
  | 'decision'
  | 'action_item'
  | 'follow_up'
  | 'open_question'
  | 'risk'
  | 'blocker'
  | 'dependency'
  | 'important_date'
  | 'reference';

export type MeetingItemPriority = 'low' | 'medium' | 'high' | 'urgent';
export type MeetingItemStatus = 'open' | 'in_progress' | 'done' | 'blocked';

export interface MeetingItem {
  id: string;
  meeting_id: string;
  order: number;
  item_type: MeetingItemType;
  title: string;
  description?: string | null;
  owner?: string | null;
  due_date?: string | null;
  priority?: MeetingItemPriority | null;
  status: MeetingItemStatus;
  source_text?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export type ToolType =
  | 'calendar_event'
  | 'reminder'
  | 'task'
  | 'notion_page'
  | 'jira_ticket'
  | 'email'
  | 'slack_message'
  | 'teams_message'
  | 'document_note';

export type ProposedActionStatus =
  | 'proposed'
  | 'approved'
  | 'rejected'
  | 'executing'
  | 'executed'
  | 'failed';

export interface ProposedAction {
  id: string;
  meeting_id: string;
  tool_type: ToolType;
  title: string;
  payload: Record<string, unknown>;
  source_item_ids: string[];
  status: ProposedActionStatus;
  idempotency_key: string;
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  execution_result?: Record<string, unknown> | null;
  failure_reason?: string | null;
  executed_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AuthProviderInfo {
  name: string;
  label: string;
  supports_password_login: boolean;
  enabled: boolean;
}

export interface AuthProvidersResponse {
  active: string;
  providers: AuthProviderInfo[];
}

export interface CurrentUser {
  username: string;
  provider: string;
  is_admin: boolean;
  email?: string | null;
  full_name?: string | null;
}
