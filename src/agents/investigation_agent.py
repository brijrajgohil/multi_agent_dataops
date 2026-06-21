from __future__ import annotations

from typing import Any, Protocol

from src.guardrails.tool_guardrails import validate_tool_call
from src.tools.mcp_client import LocalMCPClient
from src.workflow.state import Confidence, EvidenceItem, InvestigationPlan


class ToolClient(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...


class InvestigationAgent:
    def __init__(self, tool_client: ToolClient | None = None, evidence_store: Any | None = None) -> None:
        self.tool_client = tool_client or LocalMCPClient()
        self.evidence_store = evidence_store

    async def investigate(self, plan: InvestigationPlan) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []

        for tool_name, arguments in self._tool_calls_for_plan(plan):
            guardrail = validate_tool_call(tool_name, arguments)
            if not guardrail.ok:
                evidence.append(
                    self._new_evidence(
                        evidence,
                        source_type="guardrail",
                        source_name=tool_name,
                        summary=f"Tool call blocked: {guardrail.reason}",
                        raw_value={"tool_name": tool_name, "arguments": arguments},
                        confidence="high",
                        supports_root_cause=False,
                    )
                )
                continue

            result = await self.tool_client.call_tool(tool_name, arguments)
            evidence.append(self._evidence_from_tool_result(evidence, tool_name, arguments, result))

        if self.evidence_store is not None and hasattr(self.evidence_store, "save_many"):
            self.evidence_store.save_many(plan.incident_id, evidence)

        return evidence

    def _tool_calls_for_plan(self, plan: InvestigationPlan) -> list[tuple[str, dict[str, Any]]]:
        calls: list[tuple[str, dict[str, Any]]] = []

        if "sql_metric_check" in plan.required_checks:
            calls.extend(
                [
                    (
                        "run_sql_query",
                        {
                            "query": """
                            SELECT order_date, COUNT(*) AS orders, SUM(order_amount) AS order_value
                            FROM fact_orders
                            GROUP BY order_date
                            ORDER BY order_date DESC
                            LIMIT 7
                            """,
                        },
                    ),
                    (
                        "run_sql_query",
                        {
                            "query": """
                            SELECT payment_date, COUNT(*) AS payments, SUM(payment_amount) AS payment_value
                            FROM payment_events
                            GROUP BY payment_date
                            ORDER BY payment_date DESC
                            LIMIT 7
                            """,
                        },
                    ),
                    (
                        "run_sql_query",
                        {
                            "query": """
                            SELECT summary_date, revenue
                            FROM daily_revenue_summary
                            ORDER BY summary_date DESC
                            LIMIT 7
                            """,
                        },
                    ),
                ]
            )

        if "freshness_check" in plan.required_checks:
            calls.extend(
                ("check_table_freshness", {"table_name": table_name})
                for table_name in plan.table_names
            )

        if "log_check" in plan.required_checks:
            log_query = " ".join(plan.pipeline_names) if plan.pipeline_names else plan.metric_name or "failed"
            calls.append(("search_pipeline_logs", {"query": log_query}))

        if "lineage_check" in plan.required_checks:
            lineage_assets = plan.table_names + ([plan.dashboard_name] if plan.dashboard_name else [])
            calls.extend(
                ("lookup_lineage", {"asset_name": asset_name})
                for asset_name in _dedupe(lineage_assets)
            )

        if "runbook_check" in plan.required_checks:
            runbook_query = " ".join(
                item
                for item in [plan.metric_name, plan.dashboard_name, *plan.table_names, *plan.pipeline_names]
                if item
            )
            calls.append(("search_runbooks", {"query": runbook_query or plan.incident_type}))

        return calls

    def _evidence_from_tool_result(
        self,
        existing: list[EvidenceItem],
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> EvidenceItem:
        ok = bool(result.get("ok", False))
        source_name = _source_name(tool_name, arguments)
        summary = _summary(tool_name, arguments, result)
        supports_root_cause = _supports_root_cause(result)

        return self._new_evidence(
            existing,
            source_type=tool_name,
            source_name=source_name,
            summary=summary,
            raw_value=result,
            confidence="high" if ok and supports_root_cause else "medium",
            supports_root_cause=supports_root_cause,
        )

    def _new_evidence(
        self,
        existing: list[EvidenceItem],
        source_type: str,
        source_name: str,
        summary: str,
        raw_value: dict[str, Any],
        confidence: Confidence,
        supports_root_cause: bool,
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=f"ev_{len(existing) + 1:03d}",
            source_type=source_type,
            source_name=source_name,
            summary=summary,
            raw_value=raw_value,
            confidence=confidence,
            supports_root_cause=supports_root_cause,
        )


def _source_name(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "run_sql_query":
        return "duckdb"
    if tool_name == "check_table_freshness":
        return str(arguments.get("table_name", "unknown_table"))
    if tool_name == "search_pipeline_logs":
        return "pipeline_logs"
    if tool_name == "lookup_lineage":
        return str(arguments.get("asset_name", "unknown_asset"))
    if tool_name == "search_runbooks":
        return "runbooks"
    return tool_name


def _summary(tool_name: str, arguments: dict[str, Any], result: dict[str, Any]) -> str:
    if not result.get("ok", False):
        return f"{tool_name} failed: {result.get('error', 'unknown error')}"

    if tool_name == "check_table_freshness":
        return f"{arguments['table_name']} freshness status is {result.get('status', 'unknown')}."
    if tool_name == "search_pipeline_logs":
        return f"Found {len(result.get('matches', []))} matching pipeline log lines."
    if tool_name == "lookup_lineage":
        return (
            f"{arguments['asset_name']} has {len(result.get('upstream', []))} upstream "
            f"and {len(result.get('downstream', []))} downstream dependencies."
        )
    if tool_name == "search_runbooks":
        return f"Found {len(result.get('results', []))} relevant runbooks."
    if tool_name == "run_sql_query":
        return f"SQL query returned {result.get('row_count', 0)} rows."
    return f"{tool_name} completed."


def _supports_root_cause(result: dict[str, Any]) -> bool:
    text = str(result).lower()
    return any(term in text for term in ["stale", "failed", "error", "503", "under-reporting"])


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
