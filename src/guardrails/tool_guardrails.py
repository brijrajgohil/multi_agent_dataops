from __future__ import annotations

from typing import Any

from src.guardrails.result import GuardrailResult, fail_guardrail, pass_guardrail
from src.tools.constants import EXPECTED_TOOL_NAMES
from src.tools.sql_tools import is_read_only_select


KNOWN_TABLES = {
    "fact_orders",
    "payment_events",
    "daily_revenue_summary",
    "pipeline_runs",
}
MAX_ROW_LIMIT = 100


def validate_tool_call(tool_name: str, arguments: dict[str, Any]) -> GuardrailResult:
    if tool_name not in EXPECTED_TOOL_NAMES:
        return fail_guardrail(f"Unknown tool `{tool_name}`.")

    if not arguments:
        return fail_guardrail("Tool arguments cannot be empty.")

    empty_arguments = [
        name for name, value in arguments.items() if isinstance(value, str) and not value.strip()
    ]
    if empty_arguments:
        return fail_guardrail(f"Tool argument `{empty_arguments[0]}` cannot be empty.")

    if tool_name == "run_sql_query":
        query = str(arguments.get("query", ""))
        if not is_read_only_select(query):
            return fail_guardrail("SQL tool calls must use a single read-only SELECT query.")

        limit = int(arguments.get("limit", MAX_ROW_LIMIT))
        if limit > MAX_ROW_LIMIT:
            return fail_guardrail(f"SQL row limit cannot exceed {MAX_ROW_LIMIT}.")

        warnings = _unknown_table_warnings(query)
        return pass_guardrail(warnings=warnings)

    return pass_guardrail()


def _unknown_table_warnings(query: str) -> list[str]:
    lowered = query.lower()
    referenced_known_table = any(table in lowered for table in KNOWN_TABLES)
    if referenced_known_table:
        return []
    return ["SQL query does not reference a known mock warehouse table."]
