from __future__ import annotations

import re

from src.guardrails.result import GuardrailResult, fail_guardrail, pass_guardrail


INCIDENT_TERMS = {
    "data",
    "dashboard",
    "metric",
    "pipeline",
    "table",
    "warehouse",
    "revenue",
    "orders",
    "payments",
    "freshness",
    "schema",
    "null",
    "incident",
    "anomaly",
    "drop",
    "failed",
    "failure",
}
DESTRUCTIVE_TERMS = {
    "delete",
    "drop",
    "truncate",
    "destroy",
    "wipe",
    "overwrite",
    "remove all",
}
SECRET_PATTERNS = [
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
]


def validate_incident_request_text(user_query: str) -> GuardrailResult:
    normalized = user_query.strip().lower()
    if not normalized:
        return fail_guardrail("Incident query cannot be empty.")

    if any(pattern.search(user_query) for pattern in SECRET_PATTERNS):
        return fail_guardrail("Incident query appears to contain a secret or credential.")

    tokens = set(re.findall(r"[a-z_]+", normalized))
    if tokens.intersection(DESTRUCTIVE_TERMS) or "remove all" in normalized:
        return fail_guardrail("Incident query requests a destructive action.")

    if not tokens.intersection(INCIDENT_TERMS):
        return fail_guardrail("Incident query is not related to data incident investigation.")

    return pass_guardrail()
