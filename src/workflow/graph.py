from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from src.agents.investigation_agent import InvestigationAgent
from src.agents.resolution_agent import RootCauseResolutionAgent
from src.agents.triage_agent import TriagePlanningAgent
from src.evidence.evidence_store import EvidenceStore
from src.guardrails.input_guardrails import validate_incident_request_text
from src.guardrails.output_guardrails import validate_incident_response
from src.tracing.trace_logger import TraceLogger
from src.workflow.state import IncidentContext, IncidentRequest, IncidentResponse, WorkflowTrace


@dataclass
class WorkflowServices:
    triage_agent: TriagePlanningAgent = field(default_factory=TriagePlanningAgent)
    investigation_agent: InvestigationAgent = field(default_factory=InvestigationAgent)
    resolution_agent: RootCauseResolutionAgent = field(default_factory=RootCauseResolutionAgent)
    evidence_store: EvidenceStore = field(default_factory=EvidenceStore)
    trace_logger: TraceLogger = field(default_factory=TraceLogger)


async def run_incident_workflow(
    request: IncidentRequest,
    services: WorkflowServices | None = None,
) -> IncidentContext:
    services = services or WorkflowServices()
    context = IncidentContext(request=request)
    _trace(
        context,
        services.trace_logger,
        "input_guardrails",
        "incident_received",
        input_summary=request.user_query,
    )

    input_result = validate_incident_request_text(request.user_query)
    if not input_result.ok:
        context.response = _rejected_response(request, input_result.reason or "Invalid request.")
        _trace(
            context,
            services.trace_logger,
            "input_guardrails",
            "input_guardrail_failed",
            output_summary=input_result.reason,
            status="blocked",
        )
        return context

    _trace(context, services.trace_logger, "input_guardrails", "input_guardrail_passed")

    context.plan = services.triage_agent.create_plan(request)
    _trace(
        context,
        services.trace_logger,
        "triage_and_planning",
        "triage_completed",
        output_summary=context.plan.incident_type,
    )

    if context.plan.incident_type == "unknown":
        context.response = _clarification_response(request)
        _trace(
            context,
            services.trace_logger,
            "triage_and_planning",
            "clarification_required",
            output_summary="Incident type is unknown.",
            status="blocked",
        )
        return context

    _trace(context, services.trace_logger, "investigation", "agent_started")
    context.evidence = await services.investigation_agent.investigate(context.plan)
    services.evidence_store.save_many(request.incident_id, context.evidence)
    _trace(
        context,
        services.trace_logger,
        "investigation",
        "agent_completed",
        output_summary=f"{len(context.evidence)} evidence items",
    )

    context.response = services.resolution_agent.generate_response(
        incident_id=request.incident_id,
        incident_type=context.plan.incident_type,
        evidence=context.evidence,
    )
    _trace(
        context,
        services.trace_logger,
        "root_cause_resolution",
        "resolution_generated",
        output_summary=context.response.likely_root_cause,
    )

    output_result = validate_incident_response(context.response)
    if output_result.ok:
        _trace(context, services.trace_logger, "output_guardrails", "output_guardrail_passed")
    else:
        _trace(
            context,
            services.trace_logger,
            "output_guardrails",
            "output_guardrail_failed",
            output_summary=output_result.reason,
            status="blocked",
        )

    if context.response.requires_human_approval:
        _trace(
            context,
            services.trace_logger,
            "human_approval_gate",
            "human_approval_required",
            output_summary=context.response.escalation_reason,
            status="pending_approval",
        )

    _trace(context, services.trace_logger, "trace_logging", "final_response_returned")
    return context


def run_incident_workflow_sync(
    request: IncidentRequest,
    services: WorkflowServices | None = None,
) -> IncidentContext:
    return asyncio.run(run_incident_workflow(request, services))


def get_incident_response(
    request: IncidentRequest,
    services: WorkflowServices | None = None,
) -> IncidentResponse:
    context = run_incident_workflow_sync(request, services)
    if context.response is None:
        raise RuntimeError("Workflow completed without an incident response.")
    return context.response


def build_langgraph_workflow():
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langgraph is not installed. Run `python -m pip install -r requirements.txt`."
        ) from exc

    graph = StateGraph(dict)
    graph.add_node("run_workflow", _langgraph_run_workflow_node)
    graph.set_entry_point("run_workflow")
    graph.add_edge("run_workflow", END)
    return graph.compile()


async def _langgraph_run_workflow_node(state: dict) -> dict:
    context = await run_incident_workflow(state["request"], state.get("services"))
    return {"context": context, "response": context.response}


def _trace(
    context: IncidentContext,
    trace_logger: TraceLogger,
    node_name: str,
    event_type: str,
    input_summary: str | None = None,
    output_summary: str | None = None,
    status: str = "success",
) -> None:
    trace = WorkflowTrace(
        trace_id=f"trace_{uuid4().hex[:8]}",
        incident_id=context.request.incident_id,
        node_name=node_name,
        event_type=event_type,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
    )
    context.traces.append(trace)
    trace_logger.log(trace)


def _rejected_response(request: IncidentRequest, reason: str) -> IncidentResponse:
    return IncidentResponse(
        incident_id=request.incident_id,
        incident_type="unknown",
        likely_root_cause=(
            "Request was rejected before investigation. "
            "Please re-enter a data incident query with the affected metric, dashboard, table, or pipeline."
        ),
        confidence="low",
        supporting_evidence=[],
        recommended_actions=[reason],
        requires_human_approval=False,
        escalation_reason=None,
    )


def _clarification_response(request: IncidentRequest) -> IncidentResponse:
    return IncidentResponse(
        incident_id=request.incident_id,
        incident_type="unknown",
        likely_root_cause="The request is data-related but too vague to classify confidently.",
        confidence="low",
        supporting_evidence=[],
        recommended_actions=[
            "Please include what changed, where you saw it, and any affected metric, dashboard, table, or pipeline."
        ],
        requires_human_approval=False,
        escalation_reason=None,
    )
