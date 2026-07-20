"""Local beta feedback capture for Fibi."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from fibi.build_info import APP_VERSION
from fibi.paths import data_path
from fibi.runtime_paths import reports_dir

FEEDBACK_TYPES = {"bug", "confusion", "feature_request", "personality", "performance", "packaging", "general"}


@dataclass(slots=True)
class FeedbackRecord:
    feedback_id: str
    created_at: str
    app_version: str
    feedback_type: str
    message: str
    rating_optional: int | None = None
    tags: list[str] = field(default_factory=list)
    linked_issue_id: str = ""
    exported: bool = False


class BetaFeedbackEngine:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else data_path("issues/feedback.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create(self, message: str, feedback_type: str = "general", tags: list[str] | None = None, linked_issue_id: str = "") -> FeedbackRecord:
        record = FeedbackRecord(
            feedback_id="FDB-" + uuid.uuid4().hex[:8],
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            app_version=APP_VERSION,
            feedback_type=feedback_type if feedback_type in FEEDBACK_TYPES else "general",
            message=message.strip()[:4000] or "beta feedback",
            tags=tags or [],
            linked_issue_id=linked_issue_id,
        )
        self._append(record)
        return record

    def list(self, limit: int = 20) -> list[FeedbackRecord]:
        return self._read()[-limit:]

    def export(self) -> Path:
        records = self._read()
        target = reports_dir() / "fibi_feedback_export.json"
        target.write_text(json.dumps([asdict(record) for record in records], indent=2), encoding="utf-8")
        for record in records:
            record.exported = True
        self._write_all(records)
        return target

    def clear_exported(self, confirm: bool = False) -> int:
        if not confirm:
            return 0
        records = [record for record in self._read() if not record.exported]
        removed = len(self._read()) - len(records)
        self._write_all(records)
        return removed

    def _append(self, record: FeedbackRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _read(self) -> list[FeedbackRecord]:
        if not self.path.exists():
            return []
        records: list[FeedbackRecord] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                records.append(FeedbackRecord(**json.loads(line)))
            except (TypeError, json.JSONDecodeError):
                continue
        return records

    def _write_all(self, records: list[FeedbackRecord]) -> None:
        self.path.write_text("\n".join(json.dumps(asdict(record), ensure_ascii=False) for record in records) + ("\n" if records else ""), encoding="utf-8")

