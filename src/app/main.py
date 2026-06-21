from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from src.workflow.graph import WorkflowServices, run_incident_workflow
from src.workflow.state import IncidentRequest, Severity


class InvestigateIncidentPayload(BaseModel):
    user_query: str
    metric_name: str = "unknown"
    dashboard_name: str = "unknown"
    severity: Severity = "medium"


def create_app(services: WorkflowServices | None = None) -> FastAPI:
    app = FastAPI(title="AI DataOps Incident Agent")
    app.state.workflow_services = services or WorkflowServices()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/incidents/investigate")
    async def investigate(payload: InvestigateIncidentPayload) -> dict:
        incident_request = IncidentRequest(
            incident_id=f"inc_{uuid4().hex[:8]}",
            user_query=payload.user_query,
            metric_name=payload.metric_name,
            dashboard_name=payload.dashboard_name,
            severity=payload.severity,
        )
        context = await run_incident_workflow(
            incident_request,
            app.state.workflow_services,
        )

        return {
            "incident_id": incident_request.incident_id,
            "response": context.response.model_dump(mode="json") if context.response else None,
            "evidence": [item.model_dump(mode="json") for item in context.evidence],
            "traces": [trace.model_dump(mode="json") for trace in context.traces],
        }

    @app.get("/incidents/{incident_id}/trace")
    def get_trace(incident_id: str) -> dict:
        trace_logger = app.state.workflow_services.trace_logger
        return {
            "incident_id": incident_id,
            "traces": trace_logger.load_records(incident_id),
        }

    @app.get("/incidents/{incident_id}/evidence")
    def get_evidence(incident_id: str) -> dict:
        evidence_store = app.state.workflow_services.evidence_store
        return {
            "incident_id": incident_id,
            "evidence": evidence_store.summary(incident_id),
        }

    return app


app = create_app()
