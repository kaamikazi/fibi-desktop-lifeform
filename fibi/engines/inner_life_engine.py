"""Fibi's private tiny thoughts and dreams.

Inner life entries are not factual memories. They are small creature-state
artifacts that can be journaled or rarely surfaced as idle bubbles.
"""

from __future__ import annotations

import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import (
    BondState,
    DreamFragment,
    InnerThought,
    JournalEntry,
    Memory,
    NestState,
    ProjectAffinity,
    ThoughtBubbleCandidate,
)

THOUGHT_CATEGORIES = {
    "idle_thought",
    "sleepy_thought",
    "curious_thought",
    "project_thought",
    "memory_thought",
    "nest_thought",
    "dream_fragment",
    "tiny_worry",
    "tiny_pride",
    "silly_thought",
}


class InnerLifeEngine:
    """Create safe, short inner-life fragments from trusted local context."""

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

    def create_thought(
        self,
        mood: str,
        time_of_day: str,
        memories: list[Memory] | None = None,
        recent_journal: list[JournalEntry] | None = None,
        known_projects: list[str] | None = None,
        nest: NestState | None = None,
        source: str = "inner_life_engine",
    ) -> InnerThought:
        """Create and store one tiny thought without inventing user facts."""
        memories = memories or []
        recent_journal = recent_journal or []
        project = self._trusted_project(known_projects or [], memories, recent_journal)
        memory = self._trusted_memory(memories)
        category, text, weight = self._compose_thought(
            mood, time_of_day, project, memory, recent_journal, nest
        )
        should_surface = self._should_surface(category, weight)
        return self.save_thought(
            category,
            mood,
            text,
            related_memory_id=memory.id if memory else None,
            related_project=project,
            emotional_weight=weight,
            should_surface_to_user=should_surface,
            source=source,
        )

    def save_thought(
        self,
        category: str,
        mood: str,
        text: str,
        related_memory_id: int | None = None,
        related_project: str | None = None,
        emotional_weight: float = 0.2,
        should_surface_to_user: bool = False,
        source: str = "inner_life_engine",
    ) -> InnerThought:
        category = category if category in THOUGHT_CATEGORIES else "idle_thought"
        cleaned = self._short(text)
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO inner_life_entries(
                    timestamp, category, mood, text, related_memory_id,
                    related_project, emotional_weight, should_surface_to_user, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    category,
                    mood or "idle",
                    cleaned,
                    related_memory_id,
                    related_project,
                    self._clamp(emotional_weight),
                    1 if should_surface_to_user else 0,
                    source,
                ),
            )
            thought_id = int(cursor.lastrowid)
        return InnerThought(
            thought_id,
            timestamp,
            category,
            mood or "idle",
            cleaned,
            related_memory_id,
            related_project,
            self._clamp(emotional_weight),
            should_surface_to_user,
            source,
        )

    def create_dream(
        self,
        mood: str,
        recent_journal: list[JournalEntry] | None = None,
        known_projects: list[str] | None = None,
        habits: list[str] | None = None,
        nest: NestState | None = None,
        bond: BondState | None = None,
    ) -> DreamFragment:
        """Store a dream as dream data, never as a fact or user memory."""
        recent_journal = recent_journal or []
        project = self._trusted_project(known_projects or [], [], recent_journal)
        comfort = bond.comfort if bond else 30
        text = self._compose_dream(mood, project, habits or [], nest, comfort)
        weight = 0.25 + (0.15 if project else 0.0) + (0.1 if comfort >= 60 else 0.0)
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO fibi_dreams(
                    timestamp, dream_text, mood, related_project,
                    emotional_weight, surfaced_to_user
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (timestamp, text, mood or "sleepy", project, self._clamp(weight)),
            )
            dream_id = int(cursor.lastrowid)
        self.save_thought(
            "dream_fragment",
            mood or "sleepy",
            text,
            related_project=project,
            emotional_weight=weight,
            should_surface_to_user=False,
            source="dream_system",
        )
        return DreamFragment(dream_id, timestamp, text, mood or "sleepy", project, self._clamp(weight), False)

    def maybe_wake_dream_line(self, chance: float = 0.25) -> str | None:
        """Rarely surface the newest unsurfaced dream when Fibi wakes."""
        if random.random() > chance:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM fibi_dreams
                WHERE surfaced_to_user = 0
                ORDER BY timestamp DESC LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE fibi_dreams SET surfaced_to_user = 1 WHERE id = ?",
                (int(row["id"]),),
            )
        text = str(row["dream_text"])
        if "dreamed " in text:
            return text.replace("dreamed ", "", 1)
        return random.choice(["weird dream.", text])

    def thought_bubble_candidate(
        self,
        attention_level: int,
        focused: bool,
        busy: bool,
        mood: str,
        event_source: str = "idle",
        user_text: str = "",
    ) -> ThoughtBubbleCandidate | None:
        """Return a rare thought bubble candidate or silence."""
        if event_source == "user_message" or user_text.strip():
            return None
        if busy or focused or attention_level < 30:
            return None
        if random.random() > 0.18:
            return None
        cutoff = datetime.now().astimezone() - timedelta(minutes=25)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM inner_life_entries
                WHERE should_surface_to_user = 1
                  AND timestamp >= ?
                ORDER BY emotional_weight DESC, timestamp DESC
                LIMIT 1
                """,
                (cutoff.isoformat(timespec="seconds"),),
            ).fetchone()
        if row is None:
            line = random.choice(["hm.", "tiny thought.", "nest status: acceptable."])
            return ThoughtBubbleCandidate(line, self._expression_for(mood), 0.1, "idle_thought", should_display=True)
        return ThoughtBubbleCandidate(
            str(row["text"]),
            self._expression_for(str(row["mood"])),
            float(row["emotional_weight"]),
            str(row["category"]),
            should_display=True,
        )

    def recent_dreams(self, limit: int = 5) -> list[DreamFragment]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM fibi_dreams ORDER BY timestamp DESC LIMIT ?",
                (max(1, min(20, limit)),),
            ).fetchall()
        return [
            DreamFragment(
                int(row["id"]),
                str(row["timestamp"]),
                str(row["dream_text"]),
                str(row["mood"]),
                str(row["related_project"]) if row["related_project"] else None,
                float(row["emotional_weight"]),
                bool(row["surfaced_to_user"]),
            )
            for row in rows
        ]

    def recent_thoughts(self, limit: int = 10) -> list[InnerThought]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM inner_life_entries ORDER BY timestamp DESC LIMIT ?",
                (max(1, min(50, limit)),),
            ).fetchall()
        return [self._row_to_thought(row) for row in rows]

    @staticmethod
    def _compose_thought(
        mood: str,
        time_of_day: str,
        project: str | None,
        memory: Memory | None,
        recent_journal: list[JournalEntry],
        nest: NestState | None,
    ) -> tuple[str, str, float]:
        if project:
            return "project_thought", random.choice([
                f"{project} smells like trouble.",
                f"{project} is making desktop weather.",
                f"watching {project}. suspiciously.",
            ]), 0.35
        if memory and memory.category.value in {"habit", "goal", "important_moment"}:
            return "memory_thought", random.choice([
                "remembered a tiny user pattern.",
                "old thought tapped the window.",
            ]), 0.3
        if nest and nest.position and nest.confidence >= 0.65:
            return "nest_thought", random.choice(["nest is acceptable.", "corner feels claimed."]), 0.25
        if any(entry.event_type == "error_seen" for entry in recent_journal[:10]):
            return "tiny_worry", "bugs are being rude nearby.", 0.4
        if any(entry.event_type == "celebration" for entry in recent_journal[:10]):
            return "tiny_pride", "small progress still counts.", 0.45
        if mood == "sleepy" or time_of_day in {"night", "late_night"}:
            return "sleepy_thought", random.choice(["desktop is quiet.", "eyelids buffering."]), 0.2
        if mood in {"curious", "focused"}:
            return "curious_thought", random.choice(["the cursor keeps escaping.", "what is the user plotting."]), 0.2
        return "silly_thought", random.choice(["desktop weather: suspicious.", "tabs are probably multiplying."]), 0.15

    @staticmethod
    def _compose_dream(
        mood: str,
        project: str | None,
        habits: list[str],
        nest: NestState | None,
        comfort: int,
    ) -> str:
        if project:
            return random.choice([
                f"dreamed {project} blinked back.",
                f"dreamed of guarding {project}. failed.",
            ])
        if any("commit" in habit.lower() for habit in habits):
            return "dreamed of one more commit hiding under the taskbar."
        if nest and nest.position and comfort >= 55:
            return "dreamed the desktop had grass."
        if mood == "annoyed":
            return "dreamed of a compiler with tiny teeth."
        return random.choice([
            "dreamed of tiny tabs.",
            "dreamed your tabs escaped.",
            "dreamed the cursor ran away.",
        ])

    @staticmethod
    def _trusted_project(
        known_projects: list[str],
        memories: list[Memory],
        recent_journal: list[JournalEntry],
    ) -> str | None:
        candidates = [project.strip() for project in known_projects if project and project.strip()]
        for memory in memories:
            if memory.category.value == "project" and memory.content.strip():
                candidates.append(memory.content.strip())
        for entry in recent_journal:
            if entry.related_project:
                candidates.append(entry.related_project.strip())
        for candidate in candidates:
            if candidate:
                return candidate[:80]
        return None

    @staticmethod
    def _trusted_memory(memories: list[Memory]) -> Memory | None:
        trusted = [memory for memory in memories if memory.id is not None and memory.importance >= 0.65]
        return trusted[0] if trusted else None

    @staticmethod
    def _should_surface(category: str, weight: float) -> bool:
        if category in {"tiny_pride", "nest_thought"} and weight >= 0.25:
            return random.random() < 0.2
        if category in {"silly_thought", "sleepy_thought"}:
            return random.random() < 0.08
        return False

    @staticmethod
    def _short(text: str) -> str:
        cleaned = " ".join(text.strip().split())
        return cleaned[:160] or "hm."

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _expression_for(mood: str) -> str:
        return {
            "happy": "happy",
            "excited": "happy",
            "sleepy": "sleepy",
            "annoyed": "angry",
            "focused": "thinking",
            "curious": "thinking",
        }.get(mood, "idle")

    @staticmethod
    def _row_to_thought(row: sqlite3.Row) -> InnerThought:
        return InnerThought(
            int(row["id"]),
            str(row["timestamp"]),
            str(row["category"]),
            str(row["mood"]),
            str(row["text"]),
            int(row["related_memory_id"]) if row["related_memory_id"] is not None else None,
            str(row["related_project"]) if row["related_project"] else None,
            float(row["emotional_weight"]),
            bool(row["should_surface_to_user"]),
            str(row["source"]),
        )
