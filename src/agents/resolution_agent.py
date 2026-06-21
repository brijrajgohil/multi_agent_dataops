from __future__ import annotations

from src.workflow.state import EvidenceItem, IncidentResponse, IncidentType


class RootCauseResolutionAgent:
    def generate_response(
        self,
        incident_id: str,
        incident_type: IncidentType,
        evidence: list[EvidenceItem],
    ) -> IncidentResponse:
        supporting_evidence = [
            item.evidence_id for item in evidence if item.supports_root_cause
        ]
        evidence_text = " ".join(
            f"{item.summary} {item.raw_value}" for item in evidence
        ).lower()

        if _has_payment_staleness(evidence_text):
            return IncidentResponse(
                incident_id=incident_id,
                incident_type=incident_type,
                likely_root_cause=(
                    "payment_events table is stale because payment_events_ingestion failed, "
                    "causing revenue to be under-reported."
                ),
                confidence="high" if len(supporting_evidence) >= 2 else "medium",
                supporting_evidence=supporting_evidence or [item.evidence_id for item in evidence[:1]],
                recommended_actions=[
                    "Re-run payment_events_ingestion pipeline",
                    "Validate payment_events row count after reload",
                    "Re-run daily_revenue_summary pipeline",
                    "Refresh revenue dashboard",
                    "Notify finance analytics team",
                ],
                requires_human_approval=True,
                escalation_reason="The recommendation involves re-running data pipelines.",
            )

        if not evidence:
            return IncidentResponse(
                incident_id=incident_id,
                incident_type=incident_type,
                likely_root_cause="Insufficient evidence to determine a likely root cause.",
                confidence="low",
                supporting_evidence=[],
                recommended_actions=["Collect SQL, freshness, log, lineage, and runbook evidence."],
                requires_human_approval=False,
                escalation_reason=None,
            )

        return IncidentResponse(
            incident_id=incident_id,
            incident_type=incident_type,
            likely_root_cause="Evidence is inconclusive; more investigation is needed.",
            confidence="low",
            supporting_evidence=[item.evidence_id for item in evidence],
            recommended_actions=[
                "Review collected evidence with the data owner",
                "Run additional targeted checks for the affected assets",
            ],
            requires_human_approval=False,
            escalation_reason=None,
        )


def _has_payment_staleness(evidence_text: str) -> bool:
    has_payment = "payment_events" in evidence_text
    has_stale = "stale" in evidence_text
    has_failure = "payment_events_ingestion" in evidence_text and any(
        term in evidence_text for term in ["failed", "error", "503"]
    )
    return has_payment and (has_stale or has_failure)
