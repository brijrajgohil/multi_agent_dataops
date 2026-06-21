from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.config import PROJECT_ROOT


TICKET_DIR = PROJECT_ROOT / "data" / "tickets"
TICKET_PATH = TICKET_DIR / "tickets.json"


def create_incident_ticket(summary: str, severity: str) -> dict[str, Any]:
    if not summary.strip():
        return {"ok": False, "error": "summary is required"}
    if not severity.strip():
        return {"ok": False, "error": "severity is required"}

    TICKET_DIR.mkdir(parents=True, exist_ok=True)
    if TICKET_PATH.exists():
        tickets = json.loads(TICKET_PATH.read_text(encoding="utf-8"))
    else:
        tickets = []

    ticket = {
        "ticket_id": f"ticket_{uuid4().hex[:8]}",
        "summary": summary,
        "severity": severity,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tickets.append(ticket)
    TICKET_PATH.write_text(json.dumps(tickets, indent=2) + "\n", encoding="utf-8")

    return {"ok": True, **ticket}
