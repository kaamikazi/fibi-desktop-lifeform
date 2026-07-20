"""Local append-only action journal for Fibi manual actions."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import ActionJournalEntry
from fibi.paths import data_path

ACTION_JOURNAL_PATH = data_path("action_journal.jsonl")


class ActionJournalEngine:
    """Write compact local action history entries."""

    def __init__(self, journal_path: Path = ACTION_JOURNAL_PATH) -> None:
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action_type: str,
        target: str,
        risk_level: str,
        allowed: bool,
        blocked: bool,
        required_confirmation: bool,
        confirmed: bool,
        result_summary: str,
        user_initiated: bool,
    ) -> ActionJournalEntry:
        safe_target = self._safe_text(target)
        entry = ActionJournalEntry(
            datetime.now().astimezone().isoformat(timespec="seconds"),
            action_type,
            safe_target,
            risk_level,
            allowed,
            blocked,
            required_confirmation,
            confirmed,
            self._safe_text(result_summary),
            user_initiated,
        )
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def recent(self, limit: int = 10) -> list[ActionJournalEntry]:
        try:
            lines = self.journal_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(ActionJournalEntry(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
        return entries

    @staticmethod
    def _safe_text(value: str) -> str:
        text = str(value or "")
        for marker in ("api_key=", "token=", "password=", "secret="):
            if marker in text.lower():
                return "[redacted]"
        return text[:160]
