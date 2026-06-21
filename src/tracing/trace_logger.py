from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT
from src.workflow.state import WorkflowTrace


DEFAULT_TRACE_PATH = PROJECT_ROOT / "data" / "traces" / "traces.jsonl"


class TraceLogger:
    def __init__(self, path: Path = DEFAULT_TRACE_PATH) -> None:
        self.path = path

    def log(self, trace: WorkflowTrace) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(trace.model_dump(mode="json")) + "\n")

    def load_records(self, incident_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        records = [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if incident_id is None:
            return records
        return [record for record in records if record.get("incident_id") == incident_id]

    def load_dataframe(self, incident_id: str | None = None):
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pandas is not installed. Run `python -m pip install -r requirements.txt`."
            ) from exc

        return pd.DataFrame(self.load_records(incident_id))
