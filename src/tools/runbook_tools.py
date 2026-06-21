from __future__ import annotations

from typing import Any

from src.config import PROJECT_ROOT


RUNBOOK_DIR = PROJECT_ROOT / "data" / "runbooks"


def search_runbooks(query: str, max_results: int = 5) -> dict[str, Any]:
    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        return {"ok": False, "error": "query is required", "results": []}

    results: list[dict[str, Any]] = []
    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        lowered = content.lower()
        score = sum(lowered.count(term) for term in terms)
        if score == 0:
            continue

        lines = content.splitlines()
        snippet = "\n".join(lines[: min(len(lines), 12)])
        results.append(
            {
                "runbook": path.name,
                "score": score,
                "snippet": snippet,
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return {"ok": True, "query": query, "results": results[:max_results]}
