// Workspace types
export interface Workspace {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
}

// Source types
export type SourceType =
  | "PDF"
  | "YOUTUBE"
  | "GITHUB"
  | "WEB"
  | "AUDIO"
  | "VIDEO"
  | "LOOM";

export type SourceStatus =
  | "queued"
  | "ingesting"
  | "ready"
  | "degraded"
  | "re-indexing"
  | "failed";

export interface Source {
  id: string;
  workspace_id: string;
  source_type: SourceType;
  url: string | null;
  title: string | null;
  status: SourceStatus;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface SourceCreate {
  url?: string;
  source_type: SourceType;
  title?: string;
}

// Chat types
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface SourceCitation {
  chunk_id: string;
  score: number;
  text_preview: string;
  source_title?: string;
  source_type?: string;
}

export interface Message {
  id: string;
  workspace_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  confidence?: ConfidenceLevel;
  retry_count: number;
  feedback?: "UP" | "DOWN" | null;
  created_at: string;
}

export interface ChatRequest {
  query: string;
  workspace_id: string;
  source_ids?: string[];
}

// SSE event types
export type SSEEventType =
  | "timeline"
  | "token"
  | "sources"
  | "confidence"
  | "done"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  data?: unknown;
}

// Timeline event types
export type AgentStatus = "active" | "completed" | "retrying" | "failed";

export interface TimelineEvent {
  agent: string;
  status: AgentStatus;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Eval types
export interface EvalScore {
  id: string;
  message_id: string;
  faithfulness: number | null;
  context_precision: number | null;
  answer_relevance: number | null;
  created_at: string;
}

// Analytics types
export interface AnalyticsData {
  workspace_id: string;
  query_count: number;
  source_count: number;
  avg_faithfulness: number;
  avg_context_precision: number;
  hallucination_rate: number;
  retry_rate: number;
  retry_count: number;
  confidence_distribution: {
    high: number;
    total: number;
  };
}

export interface ScoreTrend {
  faithfulness: number | null;
  context_precision: number | null;
  answer_relevance: number | null;
  date: string;
}

// Report types
export interface ActionItem {
  owner?: string;
  deadline?: string;
  priority?: string;
  description: string;
}

export interface Report {
  id: string;
  workspace_id: string;
  title: string;
  summary?: string;
  decisions?: unknown[];
  action_items?: ActionItem[];
  open_questions?: unknown[];
  pdf_url?: string;
  created_at: string;
}
