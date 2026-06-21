from __future__ import annotations

from typing import Any

from src.config import PROJECT_ROOT


LOG_DIR = PROJECT_ROOT / "data" / "logs"


def search_pipeline_logs(query: str, max_matches: int = 10) -> dict[str, Any]:
    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        return {"ok": False, "error": "query is required", "matches": []}

    matches: list[dict[str, Any]] = []
    for path in sorted(LOG_DIR.glob("*.log")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            if any(term in lowered for term in terms):
                matches.append(
                    {
                        "file": path.name,
                        "line_number": line_number,
                        "line": line,
                    }
                )
                if len(matches) >= max_matches:
                    return {"ok": True, "query": query, "matches": matches}

    return {"ok": True, "query": query, "matches": matches}
