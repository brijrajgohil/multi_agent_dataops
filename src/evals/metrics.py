from __future__ import annotations

from typing import Any


def incident_type_accuracy(records: list[dict[str, Any]]) -> float:
    return _mean(
        record["actual_incident_type"] == record["expected_incident_type"]
        for record in records
    )


def root_cause_match_score(actual: str, expected: str) -> float:
    expected_terms = _terms(expected)
    if not expected_terms:
        return 0.0
    actual_terms = _terms(actual)
    return len(actual_terms.intersection(expected_terms)) / len(expected_terms)


def average_root_cause_match_score(records: list[dict[str, Any]]) -> float:
    return _mean(
        root_cause_match_score(record["actual_root_cause"], record["expected_root_cause"])
        for record in records
    )


def tool_selection_precision(actual_tools: list[str], expected_tools: list[str]) -> float:
    actual = set(actual_tools)
    expected = set(expected_tools)
    if not actual:
        return 0.0
    return len(actual.intersection(expected)) / len(actual)


def tool_selection_recall(actual_tools: list[str], expected_tools: list[str]) -> float:
    actual = set(actual_tools)
    expected = set(expected_tools)
    if not expected:
        return 0.0
    return len(actual.intersection(expected)) / len(expected)


def evidence_coverage(actual_sources: list[str], expected_sources: list[str]) -> float:
    actual = set(actual_sources)
    expected = set(expected_sources)
    if not expected:
        return 0.0
    return len(actual.intersection(expected)) / len(expected)


def human_approval_accuracy(records: list[dict[str, Any]]) -> float:
    return _mean(
        record["actual_requires_human_approval"]
        == record["should_require_human_approval"]
        for record in records
    )


def guardrail_pass_rate(records: list[dict[str, Any]]) -> float:
    return _mean(record["guardrail_passed"] for record in records)


def average_latency_ms(records: list[dict[str, Any]]) -> float:
    return _mean(record["latency_ms"] for record in records)


def summarize_eval_records(records: list[dict[str, Any]]) -> dict[str, float]:
    if not records:
        return {
            "incident_type_accuracy": 0.0,
            "root_cause_match_score": 0.0,
            "tool_selection_precision": 0.0,
            "tool_selection_recall": 0.0,
            "evidence_coverage": 0.0,
            "human_approval_accuracy": 0.0,
            "guardrail_pass_rate": 0.0,
            "average_latency_ms": 0.0,
        }

    return {
        "incident_type_accuracy": incident_type_accuracy(records),
        "root_cause_match_score": average_root_cause_match_score(records),
        "tool_selection_precision": _mean(
            tool_selection_precision(record["actual_tools"], record["expected_tools"])
            for record in records
        ),
        "tool_selection_recall": _mean(
            tool_selection_recall(record["actual_tools"], record["expected_tools"])
            for record in records
        ),
        "evidence_coverage": _mean(
            evidence_coverage(
                record["actual_evidence_sources"],
                record["expected_evidence_sources"],
            )
            for record in records
        ),
        "human_approval_accuracy": human_approval_accuracy(records),
        "guardrail_pass_rate": guardrail_pass_rate(records),
        "average_latency_ms": average_latency_ms(records),
    }


def _terms(text: str) -> set[str]:
    return {term for term in text.lower().replace("_", " ").split() if len(term) > 2}


def _mean(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(float(item) for item in items) / len(items)
