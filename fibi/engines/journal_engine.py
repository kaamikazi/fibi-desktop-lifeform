"""Local daily journal for Fibi's sampled experiences."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import DailySummary, JournalEntry


class JournalEngine:
    """Store small local events without creating a surveillance timeline."""

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
        """Run CREATE IF NOT EXISTS statements as a safe migration."""
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connection() as connection:
            connection.executescript(schema)

    def record(
        self,
        event_type: str,
        mood: str,
        presence_state: str,
        short_summary: str,
        related_project: str | None = None,
        emotional_weight: float = 0.5,
        source: str = "engine",
        metadata: dict | None = None,
        timestamp: str | None = None,
    ) -> int | None:
        """Record one meaningful sampled event."""
        summary = short_summary.strip()
        if not event_type.strip() or not summary:
            return None

        event_timestamp = timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO journal_entries(
                    timestamp, event_type, mood, presence_state, short_summary,
                    related_project, emotional_weight, source, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_timestamp,
                    event_type.strip(),
                    mood.strip() or "idle",
                    presence_state.strip() or "idle",
                    summary,
                    related_project.strip() if related_project else None,
                    max(0.0, min(1.0, emotional_weight)),
                    source.strip() or "engine",
                    json.dumps(metadata or {}),
                ),
            )
            return int(cursor.lastrowid)

    def recent(
        self,
        limit: int = 20,
        event_types: list[str] | None = None,
        since_hours: float | None = None,
    ) -> list[JournalEntry]:
        clauses: list[str] = []
        params: list[object] = []

        if event_types:
            clauses.append("event_type IN (" + ",".join("?" for _ in event_types) + ")")
            params.extend(event_types)

        if since_hours is not None:
            cutoff = datetime.now().astimezone() - timedelta(hours=max(0.0, since_hours))
            clauses.append("timestamp >= ?")
            params.append(cutoff.isoformat(timespec="seconds"))

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max(1, min(limit, 200)))

        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM journal_entries {where} ORDER BY timestamp DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def count(self, event_type: str, since_hours: float | None = None) -> int:
        clauses = ["event_type = ?"]
        params: list[object] = [event_type]
        if since_hours is not None:
            cutoff = datetime.now().astimezone() - timedelta(hours=max(0.0, since_hours))
            clauses.append("timestamp >= ?")
            params.append(cutoff.isoformat(timespec="seconds"))
        with self._connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM journal_entries WHERE " + " AND ".join(clauses),
                params,
            ).fetchone()
        return int(row["total"] if row else 0)

    def summarize_day(self, day: str | None = None) -> str:
        """Create a short local summary without calling a language model."""
        target = day or datetime.now().astimezone().date().isoformat()
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT event_type, COUNT(*) AS total
                FROM journal_entries
                WHERE SUBSTR(timestamp, 1, 10) = ?
                GROUP BY event_type
                ORDER BY total DESC
                """,
                (target,),
            ).fetchall()
            projects = connection.execute(
                """
                SELECT related_project, COUNT(*) AS total
                FROM journal_entries
                WHERE SUBSTR(timestamp, 1, 10) = ? AND related_project IS NOT NULL
                GROUP BY related_project
                ORDER BY total DESC
                LIMIT 2
                """,
                (target,),
            ).fetchall()

        if not rows:
            return "quiet day. mostly blinking."
        event_summary = ", ".join(f"{row['total']} {row['event_type']}" for row in rows[:4])
        project_summary = ", projects: " + ", ".join(row["related_project"] for row in projects) if projects else ""
        return f"{target}: {event_summary}{project_summary}."

    def create_daily_summary(self, day: str | None = None) -> DailySummary:
        """Build and persist a deterministic summary from sampled journal events."""
        target = day or datetime.now().astimezone().date().isoformat()
        with self._connection() as connection:
            events = connection.execute(
                """
                SELECT event_type, short_summary, mood, related_project, emotional_weight
                FROM journal_entries WHERE SUBSTR(timestamp, 1, 10) = ?
                ORDER BY emotional_weight DESC, timestamp DESC
                """,
                (target,),
            ).fetchall()
        mood_counts: dict[str, int] = {}
        projects: list[str] = []
        for row in events:
            mood = str(row["mood"] or "idle")
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
            project = row["related_project"]
            if project and project not in projects:
                projects.append(str(project))
        dominant = max(mood_counts, key=mood_counts.get) if mood_counts else "idle"
        notable = [str(row["short_summary"]) for row in events[:5]]
        event_types = {str(row["event_type"]) for row in events}
        if "error_seen" in event_types:
            summary_text = "you fought bugs. tiny log survived."
        elif "celebration" in event_types:
            summary_text = "we survived another build."
        elif projects:
            summary_text = f"the day was very {projects[0]}-shaped."
        elif events:
            summary_text = "tiny log: you did not do nothing."
        else:
            summary_text = "quiet day. mostly blinking."
        emotional_weight = min(10, round(sum(float(row["emotional_weight"]) for row in events)))
        result = DailySummary(
            target, dominant, projects[0] if projects else None, len(events),
            summary_text, emotional_weight, notable, projects[:5],
        )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO daily_summaries(
                    date, main_mood, notable_project, interaction_count, tiny_summary,
                    emotional_weight, notable_events_json, projects_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    main_mood=excluded.main_mood,
                    notable_project=excluded.notable_project,
                    interaction_count=excluded.interaction_count,
                    tiny_summary=excluded.tiny_summary,
                    emotional_weight=excluded.emotional_weight,
                    notable_events_json=excluded.notable_events_json,
                    projects_json=excluded.projects_json
                """,
                (
                    target, dominant, result.notable_project, result.interaction_count,
                    summary_text, emotional_weight, json.dumps(notable), json.dumps(projects[:5]),
                ),
            )
        return result

    def get_daily_summary(self, day: str) -> DailySummary | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM daily_summaries WHERE date = ?", (day,)).fetchone()
        if row is None:
            return None
        try:
            notable = json.loads(row["notable_events_json"])
            projects = json.loads(row["projects_json"])
        except (TypeError, json.JSONDecodeError):
            notable, projects = [], []
        return DailySummary(
            str(row["date"]), str(row["main_mood"]), row["notable_project"],
            int(row["interaction_count"]), str(row["tiny_summary"]),
            int(row["emotional_weight"]), list(notable), list(projects),
        )

    def yesterday_reference(self) -> str | None:
        yesterday = (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
        summary = self.get_daily_summary(yesterday)
        if summary is None:
            summary = self.create_daily_summary(yesterday)
        if summary.interaction_count == 0:
            return None
        if summary.projects:
            return f"yesterday had {summary.projects[0]} and a mostly {summary.main_mood} creature."
        return f"yesterday was mostly {summary.main_mood}."

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> JournalEntry:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return JournalEntry(
            id=int(row["id"]),
            timestamp=str(row["timestamp"]),
            event_type=str(row["event_type"]),
            mood=str(row["mood"]),
            presence_state=str(row["presence_state"]),
            short_summary=str(row["short_summary"]),
            related_project=str(row["related_project"]) if row["related_project"] else None,
            emotional_weight=float(row["emotional_weight"]),
            source=str(row["source"]),
            metadata=metadata,
        )
