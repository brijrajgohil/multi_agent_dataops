from __future__ import annotations

from src.workflow.state import CheckType, IncidentRequest, IncidentType, InvestigationPlan, Severity


class TriagePlanningAgent:
    def create_plan(self, request: IncidentRequest) -> InvestigationPlan:
        query = request.user_query.lower()
        incident_type = self._classify_incident(query)
        required_checks = self._required_checks(query, incident_type)
        table_names = self._table_names(query, request.metric_name)
        pipeline_names = self._pipeline_names(query, table_names)

        return InvestigationPlan(
            incident_id=request.incident_id,
            incident_type=incident_type,
            metric_name=request.metric_name,
            dashboard_name=request.dashboard_name,
            table_names=table_names,
            pipeline_names=pipeline_names,
            date_range=self._date_range(query),
            required_checks=required_checks,
            severity=self._severity(request.severity, query),
            steps=self._steps(required_checks),
        )

    def _classify_incident(self, query: str) -> IncidentType:
        if any(term in query for term in ["schema", "column", "type mismatch"]):
            return "schema_drift"
        if any(term in query for term in ["null", "missing values", "quality"]):
            return "data_quality_issue"
        if any(term in query for term in ["freshness", "stale", "late", "delay"]):
            return "freshness_issue"
        if any(term in query for term in ["pipeline", "job", "failed", "failure"]):
            return "pipeline_failure"
        if any(term in query for term in ["drop", "dropped", "spike", "anomaly", "metric", "revenue"]):
            return "metric_anomaly"
        return "unknown"

    def _required_checks(self, query: str, incident_type: IncidentType) -> list[CheckType]:
        checks: list[CheckType] = []

        if incident_type in {"metric_anomaly", "unknown"}:
            checks.append("sql_metric_check")
        if incident_type in {"metric_anomaly", "freshness_issue", "pipeline_failure"}:
            checks.append("freshness_check")
            checks.append("log_check")
        if incident_type in {"metric_anomaly", "freshness_issue", "pipeline_failure"}:
            checks.append("lineage_check")
        if incident_type in {
            "metric_anomaly",
            "freshness_issue",
            "pipeline_failure",
            "schema_drift",
            "data_quality_issue",
        }:
            checks.append("runbook_check")
        if incident_type == "schema_drift" or "schema" in query:
            checks.append("schema_check")

        return _dedupe(checks)

    def _table_names(self, query: str, metric_name: str) -> list[str]:
        tables: list[str] = []
        if "revenue" in query or metric_name == "revenue":
            tables.extend(["fact_orders", "payment_events", "daily_revenue_summary"])
        if "orders" in query:
            tables.append("fact_orders")
        if "payment" in query:
            tables.append("payment_events")
        if "daily_revenue_summary" in query:
            tables.append("daily_revenue_summary")
        return _dedupe(tables)

    def _pipeline_names(self, query: str, table_names: list[str]) -> list[str]:
        pipelines: list[str] = []
        if "payment_events" in table_names or "payment" in query:
            pipelines.append("payment_events_ingestion")
        if "fact_orders" in table_names or "orders" in query:
            pipelines.append("orders_ingestion")
        if "daily_revenue_summary" in table_names or "revenue" in query:
            pipelines.append("daily_revenue_summary")
        return _dedupe(pipelines)

    def _date_range(self, query: str) -> str | None:
        if "today" in query:
            return "today"
        if "yesterday" in query:
            return "yesterday"
        if "last 7" in query or "last seven" in query:
            return "last_7_days"
        return None

    def _severity(self, requested_severity: Severity, query: str) -> Severity:
        if requested_severity in {"high", "critical"}:
            return requested_severity
        if any(term in query for term in ["40%", "50%", "critical", "outage"]):
            return "high"
        return requested_severity

    def _steps(self, checks: list[CheckType]) -> list[str]:
        descriptions = {
            "sql_metric_check": "Compare recent metric values against source tables.",
            "freshness_check": "Check freshness for affected tables.",
            "log_check": "Search pipeline logs for failures or warnings.",
            "lineage_check": "Review upstream and downstream dependencies.",
            "runbook_check": "Search runbooks for relevant troubleshooting guidance.",
            "schema_check": "Check schema metadata for drift.",
        }
        return [descriptions[check] for check in checks]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
