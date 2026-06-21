from __future__ import annotations

import json
import re
from pathlib import Path

from src.config import PROJECT_ROOT
from src.workflow.state import EvidenceItem


DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "data" / "evidence"


class EvidenceStore:
    def __init__(self, root_dir: Path = DEFAULT_EVIDENCE_DIR) -> None:
        self.root_dir = root_dir
        self._items_by_incident: dict[str, list[EvidenceItem]] = {}

    def save(self, incident_id: str, evidence: EvidenceItem) -> None:
        items = self._items_by_incident.setdefault(incident_id, [])
        items.append(evidence)
        self.persist(incident_id)

    def save_many(self, incident_id: str, evidence: list[EvidenceItem]) -> None:
        items = self._items_by_incident.setdefault(incident_id, [])
        items.extend(evidence)
        self.persist(incident_id)

    def get(self, incident_id: str) -> list[EvidenceItem]:
        if incident_id not in self._items_by_incident:
            self._items_by_incident[incident_id] = self.load(incident_id)
        return list(self._items_by_incident[incident_id])

    def persist(self, incident_id: str) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for_incident(incident_id)
        payload = [
            item.model_dump(mode="json")
            for item in self._items_by_incident.get(incident_id, [])
        ]
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self, incident_id: str) -> list[EvidenceItem]:
        path = self._path_for_incident(incident_id)
        if not path.exists():
            return []

        payload = json.loads(path.read_text(encoding="utf-8"))
        return [EvidenceItem.model_validate(item) for item in payload]

    def summary(self, incident_id: str) -> list[dict[str, object]]:
        return [
            {
                "evidence_id": item.evidence_id,
                "source_type": item.source_type,
                "source_name": item.source_name,
                "summary": item.summary,
                "confidence": item.confidence,
                "supports_root_cause": item.supports_root_cause,
            }
            for item in self.get(incident_id)
        ]

    def _path_for_incident(self, incident_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", incident_id)
        return self.root_dir / f"{safe_id}.json"
