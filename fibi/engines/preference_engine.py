"""Slow local preferences for Fibi.

Preferences are tiny creature inclinations, not profiles. They update only
from repeated local behavior and stay on the user's machine.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import JournalEntry, NestState, PreferenceState, ProjectAffinity


class PreferenceEngine:
    """Maintain small stable preferences with slow confidence changes."""

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

    def update_from_context(
        self,
        nest: NestState | None = None,
        favorite_project: ProjectAffinity | None = None,
        recent_journal: list[JournalEntry] | None = None,
    ) -> list[PreferenceState]:
        """Apply cautious preference updates from repeated evidence."""
        recent_journal = recent_journal or []
        updates: list[PreferenceState] = []

        if nest and nest.position and nest.confidence >= 0.65:
            updates.append(
                self.upsert(
                    "favorite_nest_spot",
                    f"{nest.position.x},{nest.position.y}",
                    min(1.0, nest.confidence),
                    "repeated_desktop_placement",
                )
            )

        if favorite_project and favorite_project.mention_count >= 2:
            confidence = min(1.0, 0.35 + favorite_project.mention_count * 0.06)
            updates.append(
                self.upsert(
                    "favorite_project_to_watch",
                    favorite_project.project_name,
                    confidence,
                    "repeated_project_mentions",
                )
            )

        times = [
            str(entry.metadata.get("time_of_day", ""))
            for entry in recent_journal
            if entry.metadata.get("time_of_day")
        ]
        for time_of_day in {"morning", "afternoon", "evening", "night", "late_night"}:
            count = times.count(time_of_day)
            if count >= 3:
                updates.append(
                    self.upsert(
                        "preferred_time_of_day",
                        time_of_day,
                        min(1.0, 0.25 + count * 0.05),
                        "repeated_interaction_time",
                    )
                )
                break

        if sum(1 for entry in recent_journal if entry.event_type == "pet_interaction" and entry.metadata.get("spammed")) >= 2:
            updates.append(self.upsert("disliked_repeated_pokes", "true", 0.65, "repeated_poke_spam"))

        if sum(1 for entry in recent_journal if entry.event_type == "celebration") >= 2:
            updates.append(self.upsert("likes_success_moments", "true", 0.6, "repeated_celebrations"))

        if sum(1 for entry in recent_journal if entry.event_type == "late_night_session") >= 2:
            updates.append(self.upsert("dislikes_late_night_overwork", "true", 0.6, "late_night_pattern"))

        return updates

    def upsert(
        self,
        preference_key: str,
        value: str,
        confidence: float,
        formed_from: str,
    ) -> PreferenceState:
        """Blend new confidence into the existing preference instead of jumping."""
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        new_confidence = max(0.0, min(1.0, confidence))
        with self._connection() as connection:
            row = connection.execute(
                "SELECT confidence FROM preferences WHERE preference_key = ?",
                (preference_key,),
            ).fetchone()
            if row:
                new_confidence = min(1.0, float(row["confidence"]) * 0.8 + new_confidence * 0.2 + 0.03)
            connection.execute(
                """
                INSERT INTO preferences(preference_key, value, confidence, formed_from, last_updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(preference_key) DO UPDATE SET
                    value=excluded.value,
                    confidence=excluded.confidence,
                    formed_from=excluded.formed_from,
                    last_updated_at=excluded.last_updated_at
                """,
                (preference_key, value, new_confidence, formed_from, now),
            )
        return PreferenceState(preference_key, value, round(new_confidence, 3), formed_from, now)

    def get(self, preference_key: str) -> PreferenceState | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM preferences WHERE preference_key = ?",
                (preference_key,),
            ).fetchone()
        return self._row_to_preference(row) if row else None

    def list_preferences(self, limit: int = 20) -> list[PreferenceState]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM preferences
                ORDER BY confidence DESC, last_updated_at DESC LIMIT ?
                """,
                (max(1, min(50, limit)),),
            ).fetchall()
        return [self._row_to_preference(row) for row in rows]

    @staticmethod
    def _row_to_preference(row: sqlite3.Row) -> PreferenceState:
        return PreferenceState(
            str(row["preference_key"]),
            str(row["value"]),
            float(row["confidence"]),
            str(row["formed_from"]),
            str(row["last_updated_at"]),
        )
