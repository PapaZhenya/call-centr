export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type UserRole =
  | "super_admin"
  | "admin"
  | "qa_manager"
  | "team_lead"
  | "reviewer"
  | "agent"
  | "viewer";

export interface CurrentUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  team_id: string | null;
  agent_id: string | null;
}

export interface ManagedUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  team_id: string | null;
  agent_id: string | null;
}

export interface Team {
  id: string;
  name: string;
}

export interface Agent {
  id: string;
  display_name: string;
  external_agent_id: string | null;
  team_id: string | null;
  is_active: boolean;
}

export interface Call {
  id: string;
  agent_id: string;
  call_date: string;
  direction: string | null;
  queue: string | null;
  duration_seconds: number | null;
  original_filename: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSegment {
  speaker: string | null;
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  id: string;
  call_id: string;
  full_text: string;
  segments: TranscriptSegment[];
  engine: string;
  engine_model: string;
  language: string | null;
}

export interface RubricCriterion {
  id: string;
  key: string;
  label: string;
  description: string;
  category: string | null;
  weight: number;
  max_score: number;
  is_required: boolean;
  is_critical: boolean;
  applies_to: "agent" | "client" | "call";
  display_order: number;
  is_active: boolean;
  examples_positive: string[] | null;
  examples_negative: string[] | null;
  required_phrases: string[] | null;
  forbidden_phrases: string[] | null;
}

export interface RubricVersion {
  id: string;
  version_number: number;
  name: string;
  llm_model_id: string;
  is_active: boolean;
}

export interface QAEvaluationScore {
  rubric_criterion_id: string;
  rubric_criterion: { id: string; key: string; label: string; category: string | null };
  score: number;
  rationale: string | null;
  source: "rule" | "local_llm";
  quote: string | null;
  quote_verified: boolean;
  evidence_start: number | null;
  evidence_end: number | null;
  evidence_speaker: string | null;
  manual_score: number | null;
  manual_comment: string | null;
  corrected_at: string | null;
}

export interface QAEvaluation {
  id: string;
  call_id: string;
  rubric_version_id: string;
  overall_score: number | null;
  notes: string | null;
  flags: string[] | null;
  status: string;
  error_message: string | null;
  scores: QAEvaluationScore[];
}

export interface AgentSummary {
  agent_id: string;
  call_count: number;
  average_score: number | null;
}

export interface ScoreByCriterion {
  rubric_criterion_id: string;
  key: string;
  label: string;
  average_score: number | null;
  count: number;
}

export interface TrendPoint {
  period: string;
  average_score: number | null;
  call_count: number;
}

export interface AnalyticsOverview {
  total_calls: number;
  average_score: number | null;
  worst_criterion: { key: string; label: string; average_score: number | null } | null;
  best_criterion: { key: string; label: string; average_score: number | null } | null;
  criteria: { key: string; label: string; average_score: number | null }[];
}
