"""Simple local pattern detection from sampled journal and memory data."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from fibi.engines.journal_engine import JournalEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.types import DetectedPattern, JournalEntry, MemoryCategory, Observation, ProjectAffinity

CODE_APPS = {"code", "vscode", "devenv"}


class PatternEngine:
    """Notice repeated behavior without recording continuous activity."""

    def __init__(self, memory: MemoryEngine, journal: JournalEngine) -> None:
        self.memory = memory
        self.journal = journal

    def detect(
        self,
        observation: Observation | None = None,
        entries: list[JournalEntry] | None = None,
    ) -> list[DetectedPattern]:
        recent = entries if entries is not None else self.journal.recent(limit=150)
        patterns: list[DetectedPattern] = []

        late_code = sum(
            1
            for entry in recent
            if (
                entry.event_type == "late_night_session"
                or (
                    entry.metadata.get("time_of_day") in {"night", "late_night"}
                    and str(entry.metadata.get("active_app", "")).lower() in CODE_APPS
                )
            )
        )
        if late_code >= 2:
            patterns.append(
                self._pattern(
                    "late_night_coding",
                    late_code,
                    "User often works on code late at night.",
                    "eepy dev hours again.",
                )
            )

        vscode_count = sum(
            1 for entry in recent if str(entry.metadata.get("active_app", "")).lower() in CODE_APPS
        )
        if vscode_count >= 3:
            patterns.append(
                self._pattern(
                    "frequent_vscode_usage",
                    vscode_count,
                    "VS Code appears often in sampled activity.",
                    "building again?",
                )
            )

        project_counts = Counter(
            entry.related_project.lower()
            for entry in recent
            if entry.related_project and entry.event_type in {"project_detected", "user_message", "idle_reaction"}
        )
        project_memories = self.memory.retrieve("", categories=[MemoryCategory.PROJECT], limit=10)
        for memory in project_memories:
            for project in list(project_counts):
                if project in memory.content.lower():
                    project_counts[project] += 1
        if project_counts:
            project, count = project_counts.most_common(1)[0]
            if count >= 2:
                patterns.append(
                    self._pattern(
                        "repeated_project",
                        count,
                        f"The project {project} keeps coming up.",
                        f"{project} again?",
                    )
                )

        errors = sum(1 for entry in recent if entry.event_type == "error_seen")
        if errors >= 2:
            patterns.append(
                self._pattern(
                    "repeated_error_frustration",
                    errors,
                    "Errors and frustration have appeared repeatedly.",
                    "the bugs are being loud again.",
                )
            )

        long_idles = sum(
            1
            for entry in recent
            if entry.event_type == "idle_reaction" and float(entry.metadata.get("idle_seconds", 0) or 0) >= 900
        )
        if long_idles >= 2:
            patterns.append(
                self._pattern(
                    "long_idle_periods",
                    long_idles,
                    "Long quiet gaps happen regularly.",
                    "did you evaporate again?",
                )
            )

        greetings = sum(
            1
            for entry in recent
            if entry.event_type == "user_message" and bool(entry.metadata.get("is_greeting"))
        )
        if greetings >= 3:
            patterns.append(
                self._pattern(
                    "frequent_greetings",
                    greetings,
                    "The user often checks in with a greeting.",
                    "hii again.",
                )
            )

        long_returns = sum(
            1
            for entry in recent
            if entry.event_type == "startup" and float(entry.metadata.get("gap_hours", 0) or 0) >= 3
        )
        if long_returns >= 2:
            patterns.append(
                self._pattern(
                    "long_break_returns",
                    long_returns,
                    "The user often returns after long breaks.",
                    "you vanished again.",
                )
            )

        return sorted(patterns, key=lambda item: item.confidence, reverse=True)

    def update_project_affinity(self, project: str, event: str = "interaction") -> ProjectAffinity | None:
        """Update affinity only for a project already discovered by Fibi."""
        name = project.strip()
        if not name or not self._is_known_project(name):
            return None
        success = 1 if event == "success" else 0
        frustration = 1 if event == "frustration" else 0
        affinity_delta = 0.05 if success else (-0.02 if frustration else 0.01)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        with self.journal._connection() as connection:
            connection.execute(
                """
                INSERT INTO project_affinity(
                    project_name, mention_count, last_seen_at, affection_weight,
                    frustration_weight, success_weight
                ) VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(project_name) DO UPDATE SET
                    mention_count=project_affinity.mention_count + 1,
                    last_seen_at=excluded.last_seen_at
                    ,affection_weight=MIN(1.0, MAX(0.0, project_affinity.affection_weight + ?))
                    ,frustration_weight=project_affinity.frustration_weight + excluded.frustration_weight
                    ,success_weight=project_affinity.success_weight + excluded.success_weight
                """,
                (name, now, max(0.0, min(1.0, 0.5 + affinity_delta)), frustration, success, affinity_delta),
            )
            row = connection.execute("SELECT * FROM project_affinity WHERE project_name = ?", (name,)).fetchone()
        return self._row_to_affinity(row) if row else None

    def favorite_project(self) -> ProjectAffinity | None:
        with self.journal._connection() as connection:
            row = connection.execute(
                """SELECT * FROM project_affinity
                ORDER BY affection_weight DESC, mention_count DESC LIMIT 1"""
            ).fetchone()
        return self._row_to_affinity(row) if row else None

    def _is_known_project(self, project: str) -> bool:
        project_lower = project.lower()
        memories = self.memory.retrieve(project, categories=[MemoryCategory.PROJECT], limit=5)
        if any(project_lower in memory.content.lower() for memory in memories):
            return True
        return any(
            entry.related_project and entry.related_project.lower() == project_lower
            for entry in self.journal.recent(limit=100)
        )

    @staticmethod
    def _row_to_affinity(row) -> ProjectAffinity:
        return ProjectAffinity(
            project_name=str(row["project_name"]), mention_count=int(row["mention_count"]),
            last_seen_at=row["last_seen_at"], affection_weight=float(row["affection_weight"]),
            frustration_weight=float(row["frustration_weight"]), success_weight=float(row["success_weight"]),
        )

    @staticmethod
    def strongest(patterns: list[DetectedPattern]) -> DetectedPattern | None:
        return patterns[0] if patterns else None

    @staticmethod
    def _pattern(name: str, count: int, summary: str, reaction: str) -> DetectedPattern:
        confidence = min(0.95, 0.5 + count * 0.08)
        return DetectedPattern(name, round(confidence, 2), summary, reaction)
