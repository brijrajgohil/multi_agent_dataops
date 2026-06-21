from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT


METADATA_DIR = PROJECT_ROOT / "data" / "metadata"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_table_freshness(table_name: str) -> dict[str, Any]:
    if not table_name.strip():
        return {"ok": False, "error": "table_name is required"}

    path = METADATA_DIR / "table_freshness.json"
    freshness = _read_json(path)
    record = freshness.get(table_name)
    if record is None:
        return {
            "ok": False,
            "error": f"No freshness metadata found for table `{table_name}`.",
            "table_name": table_name,
        }

    return {
        "ok": True,
        "table_name": table_name,
        **record,
    }


def lookup_lineage(asset_name: str) -> dict[str, Any]:
    if not asset_name.strip():
        return {"ok": False, "error": "asset_name is required"}

    path = METADATA_DIR / "lineage.json"
    lineage = _read_json(path)
    record = lineage.get(asset_name)
    if record is None:
        return {
            "ok": False,
            "error": f"No lineage metadata found for asset `{asset_name}`.",
            "asset_name": asset_name,
        }

    return {
        "ok": True,
        "asset_name": asset_name,
        "upstream": record.get("upstream", []),
        "downstream": record.get("downstream", []),
    }
