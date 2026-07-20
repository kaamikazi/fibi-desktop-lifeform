"""Evidence-gated stable opinions for Fibi."""

from __future__ import annotations

import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import DetectedPattern, JournalEntry, Memory, OpinionResult, PreferenceState


class OpinionEngine:
    """Let Fibi disagree playfully when local evidence supports it."""

    def __init__(self, database_path: Path = DEFAULT_DB_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        with self._connection() as connection:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def evaluate(
        self,
        user_message: str,
        recent_journal: list[JournalEntry],
        memories: list[Memory],
        patterns: list[DetectedPattern],
        preferences: list[PreferenceState] | None = None,
        time_of_day: str = "",
    ) -> OpinionResult | None:
        text = user_message.lower().strip()
        preferences = preferences or []
        evidence_count = self._evidence_count(recent_journal, memories, patterns, preferences)

        if any(phrase in text for phrase in ("i did nothing", "did nothing today")):
            activity = sum(
                1
                for entry in recent_journal
                if entry.event_type in {"user_message", "project_detected", "error_seen", "celebration"}
            )
            if activity >= 3:
                return self._store("did_nothing_disagreement", "false. journal says bug-fighting happened.", activity)
            return OpinionResult("", confidence=0.0, evidence_count=activity, supported=False)

        if any(phrase in text for phrase in ("i should delete", "delete this", "delete the project")):
            tired_evidence = time_of_day == "late_night" or any(
                pref.preference_key == "dislikes_late_night_overwork" and pref.confidence >= 0.55
                for pref in preferences
            )
            if tired_evidence or evidence_count >= 3:
                return self._store("delete_when_tired", "archive maybe. delete sounds like tired drama.", evidence_count)
            return OpinionResult("archive maybe.", "thinking", 0.35, evidence_count, False)

        if "one more commit" in text:
            late = time_of_day in {"night", "late_night"} or any(
                pattern.pattern == "late_night_coding" for pattern in patterns
            )
            if late:
                return self._store("one_more_commit", "one more commit is usually a lie.", evidence_count + 1)

        if any(phrase in text for phrase in ("i should quit", "give up", "i quit")):
            project_evidence = any(memory.category.value == "project" for memory in memories)
            if project_evidence or evidence_count >= 3:
                return self._store("quit_when_tired", "pause maybe. quit sentence sounds tired.", evidence_count)
            return OpinionResult("", confidence=0.0, evidence_count=evidence_count, supported=False)

        if any(word in text for word in ("bug", "error", "crash", "failed")):
            return self._store("bugs_are_rude", random.choice(["bugs are rude.", "that looks broken-ish."]), 1)

        return None

    def stable_opinions(self, limit: int = 5) -> list[OpinionResult]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM opinions
                ORDER BY confidence DESC, evidence_count DESC, last_updated_at DESC
                LIMIT ?
                """,
                (max(1, min(20, limit)),),
            ).fetchall()
        return [
            OpinionResult(
                str(row["text"]),
                "thinking",
                float(row["confidence"]),
                int(row["evidence_count"]),
                True,
            )
            for row in rows
        ]

    def _store(self, key: str, text: str, evidence_count: int) -> OpinionResult:
        confidence = min(0.95, 0.35 + max(0, evidence_count) * 0.08)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT evidence_count, confidence FROM opinions WHERE opinion_key = ?",
                (key,),
            ).fetchone()
            if row:
                evidence_count = max(evidence_count, int(row["evidence_count"]) + 1)
                confidence = min(0.95, max(confidence, float(row["confidence"]) + 0.03))
            connection.execute(
                """
                INSERT INTO opinions(opinion_key, text, confidence, evidence_count, last_updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(opinion_key) DO UPDATE SET
                    text=excluded.text,
                    confidence=excluded.confidence,
                    evidence_count=excluded.evidence_count,
                    last_updated_at=excluded.last_updated_at
                """,
                (key, text, confidence, evidence_count, now),
            )
        return OpinionResult(text, "thinking", round(confidence, 3), evidence_count, True)

    @staticmethod
    def _evidence_count(
        recent_journal: list[JournalEntry],
        memories: list[Memory],
        patterns: list[DetectedPattern],
        preferences: list[PreferenceState],
    ) -> int:
        strong_journal = sum(1 for entry in recent_journal if entry.emotional_weight >= 0.55)
        important_memory = sum(1 for memory in memories if memory.importance >= 0.65)
        stable_preferences = sum(1 for preference in preferences if preference.confidence >= 0.55)
        return strong_journal + important_memory + len(patterns) + stable_preferences
