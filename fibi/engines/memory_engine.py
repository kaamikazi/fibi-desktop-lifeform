"""Local SQLite memory for Fibi."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fibi.paths import data_path
from fibi.engines.types import Memory, MemoryCategory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = data_path("fibi_memory.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class MemoryEngine:
    """Save and retrieve memories without sending data anywhere."""

    def __init__(self, database_path: Path = DEFAULT_DB_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Commit/rollback and always release the SQLite file handle."""
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connection() as connection:
            connection.executescript(schema)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(memories)").fetchall()
            }
            if "confidence" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN confidence REAL NOT NULL DEFAULT 0.5")
            if "emotional_weight" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN emotional_weight REAL NOT NULL DEFAULT 0.5")
            if "updated_at" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
            connection.execute("UPDATE memories SET confidence = importance WHERE confidence = 0.5")
            connection.execute("UPDATE memories SET emotional_weight = importance WHERE emotional_weight = 0.5")
            connection.execute("UPDATE memories SET updated_at = created_at WHERE updated_at = ''")

    def save(
        self,
        category: MemoryCategory | str,
        content: str,
        importance: float = 0.5,
        source: str = "conversation",
        metadata: dict | None = None,
    ) -> int | None:
        """Save one memory, skipping empty and exact duplicate entries."""
        category_value = MemoryCategory(category).value
        cleaned_content = content.strip()
        if not cleaned_content:
            return None

        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM memories WHERE category = ? AND content = ? LIMIT 1",
                (category_value, cleaned_content),
            ).fetchone()
            if existing:
                return int(existing["id"])

            cursor = connection.execute(
                """
                INSERT INTO memories(
                    category, content, importance, confidence, emotional_weight,
                    source, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_value,
                    cleaned_content,
                    max(0.0, min(1.0, importance)),
                    max(0.0, min(1.0, importance)),
                    max(0.0, min(1.0, importance)),
                    source,
                    json.dumps(metadata or {}),
                ),
            )
            return int(cursor.lastrowid)

    def retrieve(
        self,
        query: str = "",
        categories: list[MemoryCategory | str] | None = None,
        limit: int = 6,
    ) -> list[Memory]:
        """Retrieve relevant memories using conservative local SQL matching."""
        clauses: list[str] = []
        params: list[object] = []

        terms = [term for term in re.findall(r"[a-zA-Z0-9_]{3,}", query.lower())[:5]]
        if terms:
            clauses.append("(" + " OR ".join("LOWER(content) LIKE ?" for _ in terms) + ")")
            params.extend(f"%{term}%" for term in terms)

        if categories:
            values = [MemoryCategory(category).value for category in categories]
            clauses.append("category IN (" + ",".join("?" for _ in values) + ")")
            params.extend(values)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max(1, min(limit, 20)))

        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                {where}
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

            if rows:
                ids = [int(row["id"]) for row in rows]
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"""
                    UPDATE memories
                    SET access_count = access_count + 1,
                        last_accessed_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                    """,
                    ids,
                )

        return [self._row_to_memory(row) for row in rows]

    def summarize(self, memories: list[Memory], max_characters: int = 700) -> str:
        """Create compact model context without another model call."""
        lines: list[str] = []
        used = 0
        for memory in memories:
            line = f"- {memory.category.value}: {memory.content}"
            if used + len(line) > max_characters:
                break
            lines.append(line)
            used += len(line)
        return "\n".join(lines)

    def save_conversation(self, role: str, content: str, mood: str | None = None) -> None:
        if role not in {"user", "fibi"} or not content.strip():
            return
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO conversations(role, content, mood) VALUES (?, ?, ?)",
                (role, content.strip(), mood),
            )

    def learn_from_message(self, user_message: str) -> list[int]:
        """Capture only clear user-stated memories; avoid speculative profiling."""
        patterns = [
            (MemoryCategory.FACT, r"\bmy name is\s+([^.!?]+)", 0.9),
            (MemoryCategory.PROJECT, r"\b(?:working on|building)\s+([^.!?]+)", 0.8),
            (MemoryCategory.GOAL, r"\b(?:i want to|my goal is)\s+([^.!?]+)", 0.8),
            (MemoryCategory.HABIT, r"\bi (?:usually|often|always)\s+([^.!?]+)", 0.7),
            (MemoryCategory.BELIEF, r"\bi believe\s+([^.!?]+)", 0.8),
        ]
        saved_ids: list[int] = []
        for category, pattern, importance in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if not match:
                continue
            memory_id = self.save(category, match.group(0).strip(), importance)
            if memory_id is not None:
                saved_ids.append(memory_id)
        return saved_ids

    def seed_from_json(self, path: Path) -> int:
        """Import sample memories explicitly; never runs without being called."""
        try:
            entries = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0

        count = 0
        for entry in entries:
            memory_id = self.save(
                entry.get("category", "fact"),
                entry.get("content", ""),
                float(entry.get("importance", 0.5)),
                entry.get("source", "sample"),
            )
            count += int(memory_id is not None)
        return count

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return Memory(
            id=int(row["id"]),
            category=MemoryCategory(row["category"]),
            content=str(row["content"]),
            importance=float(row["importance"]),
            source=str(row["source"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]) if "updated_at" in row.keys() else str(row["created_at"]),
            last_accessed_at=str(row["last_accessed_at"]),
            access_count=int(row["access_count"]),
            confidence=float(row["confidence"]) if "confidence" in row.keys() else float(row["importance"]),
            emotional_weight=float(row["emotional_weight"]) if "emotional_weight" in row.keys() else float(row["importance"]),
            metadata=metadata,
        )
