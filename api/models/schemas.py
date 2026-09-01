"""Pydantic v2 schemas for all API requests and responses."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class TechnologyType(str, Enum):
    TERRAFORM = "terraform"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    JENKINS = "jenkins"
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    LINUX = "linux"
    DATABASE = "database"
    NETWORKING = "networking"
    API = "api"
    IAM = "iam"
    SSL_TLS = "ssl_tls"
    DNS = "dns"
    OTHER = "other"


class EnvironmentType(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Request models ────────────────────────────────────────────────────────────

class StartInvestigationRequest(BaseModel):
    problem_title: str = Field(..., min_length=3, max_length=200,
                               description="Short title describing the DevOps issue")
    problem_description: str = Field(..., min_length=10, max_length=5000,
                                     description="Detailed description of the problem")
    technology: str = Field(..., description="Primary technology involved")
    environment: str = Field(default="unknown", description="Deployment environment")
    recent_changes: Optional[str] = Field(default=None, max_length=2000,
                                          description="Recent infrastructure or code changes")
    logs: Optional[str] = Field(default=None, max_length=50000,
                                description="Error logs or output")
    configuration: Optional[str] = Field(default=None, max_length=30000,
                                         description="Terraform, K8s YAML, Dockerfile, or CI/CD config")

    @field_validator("problem_title", "problem_description")
    @classmethod
    def no_null_bytes(cls, v: str) -> str:
        return v.replace("\x00", "")


class ContinueInvestigationRequest(BaseModel):
    investigation_token: str = Field(..., description="HMAC-signed state token from previous response")
    diagnostic_output: str = Field(..., min_length=1, max_length=10000,
                                   description="Output from running the suggested diagnostic commands")


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class LogAnalysisRequest(BaseModel):
    logs: str = Field(..., min_length=1, max_length=50000)
    technology: Optional[str] = Field(default=None)


class ConfigAnalysisRequest(BaseModel):
    configuration: str = Field(..., min_length=1, max_length=30000)
    config_type: str = Field(..., description="terraform | kubernetes | dockerfile | cicd")


# ── Sub-models ────────────────────────────────────────────────────────────────

class AgentMessage(BaseModel):
    agent_name: str
    phase: str
    status: str = Field(description="running | complete | error | skipped")
    message: str
    timestamp: str
    duration_ms: Optional[int] = None


class Citation(BaseModel):
    filename: str
    section: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: Optional[str] = None


class LogFinding(BaseModel):
    level: str = Field(description="ERROR | WARNING | INFO | CRITICAL")
    message: str
    line_number: Optional[int] = None
    context: str = Field(description="Surrounding context")
    implication: str = Field(description="What this finding suggests")
    is_root_indicator: bool = False


class ConfigFinding(BaseModel):
    finding_type: str = Field(description="error | warning | misconfiguration | missing")
    location: str = Field(description="Where in the config (line, block, key)")
    description: str
    recommendation: str


class RootCause(BaseModel):
    rank: int
    cause: str
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 confidence score")
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    confirmation_check: str = Field(description="Command or check to confirm this cause")
    expected_result: str = Field(description="What you expect to see if this is the cause")


class DiagnosticStep(BaseModel):
    step_number: int
    purpose: str
    command: str
    expected_result: str
    interpretation: str = Field(description="How to interpret the output")
    risk_level: RiskLevel
    requires_approval: bool
    approval_reason: Optional[str] = None
    is_safe_readonly: bool = True


class RecommendedFix(BaseModel):
    title: str
    description: str
    steps: List[str]
    rollback_steps: List[str]
    risk_level: RiskLevel
    requires_approval: bool
    estimated_impact: str


# ── Main response models ──────────────────────────────────────────────────────

class InvestigationResponse(BaseModel):
    session_id: str
    request_id: str
    phase: str
    issue_category: str
    severity: str
    missing_info: List[str]
    affected_services: List[str]
    error_codes: List[str]
    agent_messages: List[AgentMessage]
    diagnostic_plan: List[str]
    log_findings: List[LogFinding]
    config_findings: List[ConfigFinding]
    runbook_citations: List[Citation]
    probable_causes: List[RootCause]
    diagnostic_steps: List[DiagnosticStep]
    recommended_fixes: List[RecommendedFix]
    flagged_items: List[str]
    report: Optional[Dict[str, Any]] = None
    investigation_token: str
    llm_configured: bool
    iteration: int = 1


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_configured: bool
    llm_provider: str
    llm_model: str
    request_id: str


class RAGSearchResponse(BaseModel):
    query: str
    results: List[Citation]
    total_found: int


class AnalysisResponse(BaseModel):
    findings: List[Dict[str, Any]]
    summary: str
    severity: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: str
