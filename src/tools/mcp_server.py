from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from src.tools.log_tools import search_pipeline_logs as search_pipeline_logs_impl
from src.tools.metadata_tools import check_table_freshness as check_table_freshness_impl
from src.tools.metadata_tools import lookup_lineage as lookup_lineage_impl
from src.tools.runbook_tools import search_runbooks as search_runbooks_impl
from src.tools.sql_tools import run_sql_query as run_sql_query_impl
from src.tools.ticket_tools import create_incident_ticket as create_incident_ticket_impl
from src.tools.constants import EXPECTED_TOOL_NAMES


mcp = FastMCP("dataops-incident-tools")


@mcp.tool()
def run_sql_query(query: str) -> dict[str, Any]:
    return run_sql_query_impl(query)


@mcp.tool()
def check_table_freshness(table_name: str) -> dict[str, Any]:
    return check_table_freshness_impl(table_name)


@mcp.tool()
def search_pipeline_logs(query: str) -> dict[str, Any]:
    return search_pipeline_logs_impl(query)


@mcp.tool()
def lookup_lineage(asset_name: str) -> dict[str, Any]:
    return lookup_lineage_impl(asset_name)


@mcp.tool()
def search_runbooks(query: str) -> dict[str, Any]:
    return search_runbooks_impl(query)


@mcp.tool()
def create_incident_ticket(summary: str, severity: str) -> dict[str, Any]:
    return create_incident_ticket_impl(summary, severity)


if __name__ == "__main__":
    mcp.run(transport="stdio")
