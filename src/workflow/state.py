from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


Severity = Literal["low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]
IncidentType = Literal[
    "metric_anomaly",
    "freshness_issue",
    "pipeline_failure",
    "schema_drift",
    "data_quality_issue",
    "unknown",
]
CheckType = Literal[
    "sql_metric_check",
    "freshness_check",
    "log_check",
    "lineage_check",
    "runbook_check",
    "schema_check",
]
ToolStatus = Literal["success", "blocked", "error"]


class IncidentRequest(BaseModel):
    incident_id: str
    user_query: str
    metric_name: str
    dashboard_name: str
    severity: Severity = "medium"
    created_at: datetime = Field(default_factory=utc_now)


class InvestigationPlan(BaseModel):
    incident_id: str
    incident_type: IncidentType = "unknown"
    metric_name: str | None = None
    dashboard_name: str | None = None
    table_names: list[str] = Field(default_factory=list)
    pipeline_names: list[str] = Field(default_factory=list)
    date_range: str | None = None
    required_checks: list[CheckType] = Field(default_factory=list)
    severity: Severity = "medium"
    steps: list[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolStatus = "success"
    result_summary: str | None = None
    error: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    source_name: str
    summary: str
    raw_value: dict[str, Any] | list[Any] | str | int | float | bool | None = None
    confidence: Confidence = "medium"
    supports_root_cause: bool = False


class IncidentFinding(BaseModel):
    finding_id: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = "medium"


class IncidentRecommendation(BaseModel):
    action: str
    rationale: str
    requires_human_approval: bool = False


class WorkflowTrace(BaseModel):
    trace_id: str
    incident_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    node_name: str
    event_type: str
    input_summary: str | None = None
    output_summary: str | None = None
    latency_ms: int | None = None
    tool_name: str | None = None
    status: str = "success"
    error: str | None = None


class IncidentResponse(BaseModel):
    incident_id: str
    incident_type: IncidentType
    likely_root_cause: str
    confidence: Confidence
    supporting_evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    escalation_reason: str | None = None


class IncidentContext(BaseModel):
    request: IncidentRequest
    plan: InvestigationPlan | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    findings: list[IncidentFinding] = Field(default_factory=list)
    recommendations: list[IncidentRecommendation] = Field(default_factory=list)
    response: IncidentResponse | None = None
    traces: list[WorkflowTrace] = Field(default_factory=list)
