"""Metadata-only project check history."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import ProjectCheckHistoryEntry, ProjectCheckResult
from fibi.paths import data_path


class ProjectCheckHistoryEngine:
    """Record check results without storing full output in history."""

    def __init__(self, history_path: Path | None = None) -> None:
        self.history_path = Path(history_path) if history_path is not None else data_path("project_check_history.jsonl")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: ProjectCheckResult, duration_ms: float = 0.0) -> ProjectCheckHistoryEntry:
        entry = ProjectCheckHistoryEntry(
            result.check_id,
            result.project_id,
            result.command_key,
            " ".join(result.command_args),
            result.exit_code,
            duration_ms,
            result.summary,
            result.output_path,
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def recent(self, limit: int = 5) -> list[dict]:
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        rows: list[dict] = []
        for line in lines[-max(1, limit):]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows
