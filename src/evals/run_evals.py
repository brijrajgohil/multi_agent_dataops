from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.agents.investigation_agent import InvestigationAgent
from src.config import PROJECT_ROOT
from src.evals.metrics import summarize_eval_records
from src.evidence.evidence_store import EvidenceStore
from src.tracing.trace_logger import TraceLogger
from src.workflow.graph import WorkflowServices, run_incident_workflow_sync
from src.workflow.state import IncidentRequest


GOLDEN_DATASET_PATH = PROJECT_ROOT / "data" / "evals" / "golden_incidents.jsonl"
EVAL_REPORT_PATH = PROJECT_ROOT / "data" / "evals" / "eval_report.json"


class EvalToolClient:
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "run_sql_query":
            return {"ok": True, "rows": [{"value": 1}], "row_count": 1}
        if name == "check_table_freshness":
            return {
                "ok": True,
                "table_name": arguments["table_name"],
                "status": "stale" if arguments["table_name"] == "payment_events" else "fresh",
            }
        if name == "search_pipeline_logs":
            return {
                "ok": True,
                "matches": [{"line": "ERROR payment_events_ingestion failed"}],
            }
        if name == "lookup_lineage":
            return {
                "ok": True,
                "upstream": ["payment_events"],
                "downstream": ["daily_revenue_dashboard"],
            }
        if name == "search_runbooks":
            return {
                "ok": True,
                "results": [{"runbook": "revenue_dashboard_drop.md", "score": 5}],
            }
        return {"ok": False, "error": f"Unexpected tool {name}"}


def load_golden_incidents(path: Path = GOLDEN_DATASET_PATH) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_evals(
    golden_path: Path = GOLDEN_DATASET_PATH,
    report_path: Path = EVAL_REPORT_PATH,
) -> dict[str, Any]:
    records = []
    for golden in load_golden_incidents(golden_path):
        started = time.perf_counter()
        services = WorkflowServices(
            investigation_agent=InvestigationAgent(tool_client=EvalToolClient()),
            evidence_store=EvidenceStore(root_dir=report_path.parent / "evidence"),
            trace_logger=TraceLogger(path=report_path.parent / "eval_traces.jsonl"),
        )
        request = IncidentRequest(
            incident_id=golden["incident_id"],
            user_query=golden["user_query"],
            metric_name=golden.get("metric_name", "unknown"),
            dashboard_name=golden.get("dashboard_name", "unknown"),
            severity=golden.get("severity", "medium"),
        )
        context = run_incident_workflow_sync(request, services)
        latency_ms = int((time.perf_counter() - started) * 1000)

        response = context.response
        if response is None:
            raise RuntimeError(f"Workflow returned no response for {golden['incident_id']}")

        records.append(
            {
                "incident_id": golden["incident_id"],
                "expected_incident_type": golden["expected_incident_type"],
                "actual_incident_type": response.incident_type,
                "expected_root_cause": golden["expected_root_cause"],
                "actual_root_cause": response.likely_root_cause,
                "expected_tools": golden["expected_tools"],
                "actual_tools": _actual_tools(context),
                "expected_evidence_sources": golden["expected_evidence_sources"],
                "actual_evidence_sources": _actual_evidence_sources(context),
                "should_require_human_approval": golden["should_require_human_approval"],
                "actual_requires_human_approval": response.requires_human_approval,
                "guardrail_passed": any(
                    trace.event_type == "output_guardrail_passed"
                    for trace in context.traces
                ),
                "latency_ms": latency_ms,
            }
        )

    report = {
        "records": records,
        "metrics": summarize_eval_records(records),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _actual_tools(context) -> list[str]:
    return list(dict.fromkeys(item.source_type for item in context.evidence))


def _actual_evidence_sources(context) -> list[str]:
    sources = []
    for item in context.evidence:
        sources.append(item.source_name)
        if item.source_type == "search_runbooks":
            sources.append("runbooks")
    return list(dict.fromkeys(sources))


if __name__ == "__main__":
    print(json.dumps(run_evals(), indent=2))
