from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT


WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "sample_data.duckdb"
BLOCKED_SQL_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "merge",
    "copy",
    "attach",
    "detach",
}


def is_read_only_select(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    if not normalized.startswith("select"):
        return False
    if ";" in normalized.rstrip(";"):
        return False

    tokens = set(re.findall(r"[a-z_]+", normalized))
    return not tokens.intersection(BLOCKED_SQL_KEYWORDS)


def run_sql_query(query: str, limit: int = 50, warehouse_path: Path = WAREHOUSE_PATH) -> dict[str, Any]:
    if not is_read_only_select(query):
        return {
            "ok": False,
            "error": "Only single read-only SELECT queries are allowed.",
            "rows": [],
            "row_count": 0,
        }

    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    if not warehouse_path.exists():
        return {
            "ok": False,
            "error": f"DuckDB warehouse not found at {warehouse_path}",
            "rows": [],
            "row_count": 0,
        }

    try:
        import duckdb
    except ModuleNotFoundError:
        return {
            "ok": False,
            "error": "duckdb is not installed. Run `python -m pip install -r requirements.txt`.",
            "rows": [],
            "row_count": 0,
        }

    try:
        with duckdb.connect(str(warehouse_path), read_only=True) as connection:
            wrapped_query = f"SELECT * FROM ({query.rstrip(';')}) AS tool_query LIMIT {limit}"
            result = connection.execute(wrapped_query)
            columns = [column[0] for column in result.description]
            rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]

        return {
            "ok": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "limit": limit,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "rows": [],
            "row_count": 0,
        }
