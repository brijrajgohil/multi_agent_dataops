from __future__ import annotations

import re

from src.guardrails.result import GuardrailResult, fail_guardrail, pass_guardrail
from src.workflow.state import IncidentResponse


RISKY_ACTION_TERMS = {
    "re-run",
    "rerun",
    "reload",
    "backfill",
    "delete",
    "drop",
    "truncate",
    "restart",
}
SENSITIVE_PATTERNS = [
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
]
UNSUPPORTED_ABSOLUTES = {"definitely", "guaranteed", "certainly", "always", "never"}


def validate_incident_response(response: IncidentResponse) -> GuardrailResult:
    if not response.supporting_evidence:
        return fail_guardrail("Final response must include supporting evidence.")

    if not response.confidence:
        return fail_guardrail("Final response must include confidence.")

    combined_text = " ".join(
        [
            response.likely_root_cause,
            *response.recommended_actions,
            response.escalation_reason or "",
        ]
    )

    if any(pattern.search(combined_text) for pattern in SENSITIVE_PATTERNS):
        return fail_guardrail("Final response appears to contain sensitive information.")

    if _has_risky_action(response) and not response.requires_human_approval:
        return fail_guardrail("Risky recommendations must require human approval.")

    lowered = response.likely_root_cause.lower()
    if any(word in lowered for word in UNSUPPORTED_ABSOLUTES) and response.confidence != "high":
        return fail_guardrail("Unsupported absolute claims require high confidence.")

    return pass_guardrail()


def _has_risky_action(response: IncidentResponse) -> bool:
    action_text = " ".join(response.recommended_actions).lower()
    return any(term in action_text for term in RISKY_ACTION_TERMS)
