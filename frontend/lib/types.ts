// ── Shared types matching the FastAPI backend schemas ─────────────────────────

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'unknown';
export type RiskLevel     = 'critical' | 'high' | 'medium' | 'low';
export type AgentStatus   = 'running' | 'complete' | 'error' | 'skipped';

export interface AgentMessage {
  agent_name:   string;
  phase:        string;
  status:       AgentStatus;
  message:      string;
  timestamp:    string;
  duration_ms?: number;
}

export interface Citation {
  filename:        string;
  section:         string;
  relevance_score: number;
  snippet?:        string;
}

export interface LogFinding {
  level:            'ERROR' | 'WARNING' | 'CRITICAL' | 'INFO';
  message:          string;
  line_number?:     number;
  context:          string;
  implication:      string;
  is_root_indicator: boolean;
}

export interface ConfigFinding {
  finding_type:  'error' | 'warning' | 'misconfiguration' | 'missing';
  location:      string;
  description:   string;
  recommendation: string;
}

export interface RootCause {
  rank:                  number;
  cause:                 string;
  confidence:            number;          // 0–1
  supporting_evidence:   string[];
  contradicting_evidence: string[];
  confirmation_check:    string;
  expected_result:       string;
}

export interface DiagnosticStep {
  step_number:      number;
  purpose:          string;
  command:          string;
  expected_result:  string;
  interpretation:   string;
  risk_level:       RiskLevel;
  requires_approval: boolean;
  is_safe_readonly:  boolean;
  approval_reason?:  string;
}

export interface RecommendedFix {
  title:             string;
  description:       string;
  steps:             string[];
  rollback_steps:    string[];
  risk_level:        RiskLevel;
  requires_approval: boolean;
  estimated_impact:  string;
}

export interface InvestigationResponse {
  session_id:          string;
  request_id:          string;
  phase:               string;
  issue_category:      string;
  severity:            SeverityLevel;
  missing_info:        string[];
  affected_services:   string[];
  error_codes:         string[];
  agent_messages:      AgentMessage[];
  diagnostic_plan:     string[];
  log_findings:        LogFinding[];
  config_findings:     ConfigFinding[];
  runbook_citations:   Citation[];
  probable_causes:     RootCause[];
  diagnostic_steps:    DiagnosticStep[];
  recommended_fixes:   RecommendedFix[];
  flagged_items:       string[];
  report?:             Record<string, unknown>;
  investigation_token: string;
  llm_configured:      boolean;
  iteration:           number;
}

export interface StartInvestigationRequest {
  problem_title:       string;
  problem_description: string;
  technology:          string;
  environment:         string;
  recent_changes?:     string;
  logs?:               string;
  configuration?:      string;
}

export interface HealthResponse {
  status:          string;
  version:         string;
  llm_configured:  boolean;
  llm_provider:    string;
  llm_model:       string;
  request_id:      string;
}
