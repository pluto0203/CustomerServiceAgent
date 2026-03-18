export interface SegmentDistribution {
  [segment: string]: number;
}

export interface SegmentResultDetail {
  segment_code: string;
  segment_name: string;
  recommended_actions: string[];
  metrics: Record<string, number | string | null>;
  summary?: string | null;
  top_signals?: string[];
}

export interface ChurnResultDetail {
  risk_level: string;
  recommended_actions: string[];
  metrics: Record<string, number | string | null>;
  summary?: string | null;
  top_factors?: string[];
  score?: number | null;
  confidence?: number | null;
}

export interface SentimentResultDetail {
  sentiment_label: string;
  recommended_actions: string[];
  topics: string[];
  metrics: Record<string, unknown>;
  summary?: string | null;
  top_signals?: string[];
  score?: number | null;
  confidence?: number | null;
}

export interface CustomerSegmentResult {
  customer_id: string;
  email: string | null;
  churn_risk: number | null;
  sentiment: string | null;
  core_insight: string | null;
  recommendations: string[];
  top_signals: string[];
  churn?: ChurnResultDetail;
  sentiment_detail?: SentimentResultDetail;
  segment: SegmentResultDetail;
  segment_label: string;
  status: string;
}

export interface AnalysisPayload {
  batch_id: string;
  workflow_run_id: string;
  record_count: number;
  records_succeeded: number;
  records_failed: number;
  skills: string[];
  segment_distribution: SegmentDistribution;
  status: string;
  results: CustomerSegmentResult[];
  note?: string;
}

export interface AnalysisResponse {
  message_id: string;
  correlation_id: string | null;
  in_response_to: string;
  status: string;
  payload_type: string;
  payload: AnalysisPayload;
  processing_time_ms?: number;
}
