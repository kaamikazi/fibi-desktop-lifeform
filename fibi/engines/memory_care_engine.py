"""User-facing local memory management for Fibi."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fibi.paths import data_dir
from fibi.paths import data_path
from fibi.engines.life_engine import STATE_PATH
from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import (
    MemoryCareResult,
    MemorySourceInfo,
    NotebookEntry,
    PrivacySettings,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = data_dir() / "exports"
MEMORY_CATEGORIES = {
    "facts": "fact",
    "events": "event",
    "projects": "project",
    "habits": "habit",
    "beliefs": "belief",
    "goals": "goal",
    "important_moments": "important_moment",
}


class MemoryCareEngine:
    """Provide safe local inspection, export, edit, forget, and reset actions."""

    def __init__(self, database_path: Path = DEFAULT_DB_PATH, state_path: Path = STATE_PATH) -> None:
        self.database_path = Path(database_path)
        self.state_path = Path(state_path)
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
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(memories)").fetchall()}
            if "confidence" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN confidence REAL NOT NULL DEFAULT 0.5")
            if "emotional_weight" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN emotional_weight REAL NOT NULL DEFAULT 0.5")
            if "updated_at" not in columns:
                connection.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
            connection.execute("UPDATE memories SET confidence = importance WHERE confidence = 0.5")
            connection.execute("UPDATE memories SET emotional_weight = importance WHERE emotional_weight = 0.5")
            connection.execute("UPDATE memories SET updated_at = created_at WHERE updated_at = ''")

    def list_memories(self, category: str | None = None, limit: int = 25) -> MemoryCareResult:
        where = ""
        params: list[object] = []
        if category:
            category_value = self._category_value(category)
            if category_value is None:
                return MemoryCareResult(False, "unknown memory pile.")
            where = "WHERE category = ?"
            params.append(category_value)
        params.append(max(1, min(100, limit)))
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM memories {where} ORDER BY importance DESC, updated_at DESC LIMIT ?",
                params,
            ).fetchall()
        entries = [self._memory_entry(row) for row in rows]
        return MemoryCareResult(True, "tiny memory pile.", entries, changed_count=len(entries))

    def search_memories(self, query: str, limit: int = 20) -> MemoryCareResult:
        text = query.strip()
        if not text:
            return MemoryCareResult(False, "search crumb missing.")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM memories
                WHERE LOWER(content) LIKE ?
                ORDER BY importance DESC, updated_at DESC LIMIT ?
                """,
                (f"%{text.lower()}%", max(1, min(50, limit))),
            ).fetchall()
            if rows:
                ids = [int(row["id"]) for row in rows]
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"UPDATE memories SET access_count = access_count + 1, last_accessed_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
                    ids,
                )
        return MemoryCareResult(True, "found these crumbs.", [self._memory_entry(row) for row in rows], changed_count=len(rows))

    def inspect_memory(self, memory_id: int) -> MemoryCareResult:
        row = self._memory_row(memory_id)
        if row is None:
            return MemoryCareResult(False, "crumb not found.")
        return MemoryCareResult(True, "crumb details.", [self._memory_entry(row)], changed_count=1)

    def edit_memory(self, memory_id: int, new_text: str, confidence: float | None = None) -> MemoryCareResult:
        cleaned = " ".join(new_text.strip().split())
        if not cleaned:
            return MemoryCareResult(False, "empty crumb rejected.")
        row = self._memory_row(memory_id)
        if row is None:
            return MemoryCareResult(False, "crumb not found.")
        new_confidence = self._clamp(confidence if confidence is not None else float(row["confidence"]) * 0.95)
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE memories
                SET content = ?, confidence = ?, importance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (cleaned, new_confidence, new_confidence, memory_id),
            )
        return MemoryCareResult(True, "edited the crumb.", changed_count=1)

    def delete_memory(self, memory_id: int, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "say confirm first.")
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return MemoryCareResult(True, "forgot one crumb.", changed_count=cursor.rowcount)

    def forget_matching(self, text: str, confirm: bool = True) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "say confirm first.")
        query = text.strip().lower()
        if not query:
            return MemoryCareResult(False, "which crumb?")
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE LOWER(content) LIKE ?",
                (f"%{query}%",),
            )
        count = int(cursor.rowcount)
        return MemoryCareResult(True, "forgot the matching crumbs." if count else "couldn't find that crumb.", changed_count=count)

    def forget_category(self, category: str, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "category wipe needs confirm.")
        category_value = self._category_value(category)
        if category_value is None:
            return MemoryCareResult(False, "unknown memory pile.")
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE category = ?", (category_value,))
        return MemoryCareResult(True, f"cleared {category}.", changed_count=int(cursor.rowcount))

    def mark_important(self, memory_id: int) -> MemoryCareResult:
        return self._set_importance(memory_id, 0.9, "marked strong crumb.")

    def reduce_importance(self, memory_id: int) -> MemoryCareResult:
        row = self._memory_row(memory_id)
        if row is None:
            return MemoryCareResult(False, "crumb not found.")
        return self._set_importance(memory_id, max(0.1, float(row["importance"]) - 0.25), "softened that crumb.")

    def clear_dreams(self, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "dream wipe needs confirm.")
        with self._connection() as connection:
            dreams = connection.execute("DELETE FROM fibi_dreams").rowcount
            thoughts = connection.execute("DELETE FROM inner_life_entries WHERE category = 'dream_fragment'").rowcount
        return MemoryCareResult(True, "dream crumbs cleared.", changed_count=int(dreams + thoughts))

    def clear_journal(self, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "journal wipe needs confirm.")
        with self._connection() as connection:
            journal = connection.execute("DELETE FROM journal_entries").rowcount
            summaries = connection.execute("DELETE FROM daily_summaries").rowcount
        return MemoryCareResult(True, "journal packed away.", changed_count=int(journal + summaries))

    def clear_patterns_preferences(self, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "preference wipe needs confirm.")
        with self._connection() as connection:
            prefs = connection.execute("DELETE FROM preferences").rowcount
            affinity = connection.execute("DELETE FROM project_affinity").rowcount
            opinions = connection.execute("DELETE FROM opinions").rowcount
        return MemoryCareResult(True, "preferences reset.", changed_count=int(prefs + affinity + opinions))

    def reset_all(self, confirmation: str = "", create_backup: bool = True) -> MemoryCareResult:
        if confirmation != "reset fibi confirm":
            return MemoryCareResult(False, "new tiny life needs exact confirm.")
        export_path = self.export_bundle().export_path if create_backup else None
        with self._connection() as connection:
            for table in (
                "memories",
                "conversations",
                "journal_entries",
                "daily_summaries",
                "project_affinity",
                "inner_life_entries",
                "fibi_dreams",
                "preferences",
                "opinions",
            ):
                connection.execute(f"DELETE FROM {table}")
        state = self._read_state()
        privacy = state.get("privacy_settings", {})
        self.state_path.write_text(json.dumps({"privacy_settings": privacy}, indent=2), encoding="utf-8")
        return MemoryCareResult(True, "okay. old crumbs packed away.", export_path=export_path)

    def export_bundle(self, privacy_settings: PrivacySettings | dict | None = None) -> MemoryCareResult:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        path = EXPORT_DIR / f"fibi_export_{stamp}.json"
        bundle = {
            "version": "0.08",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "memories": self._rows("memories"),
            "journal_summaries": self._rows("daily_summaries"),
            "dreams": self._rows("fibi_dreams"),
            "preferences": self._rows("preferences"),
            "project_affinity": self._rows("project_affinity"),
            "life_state": self._safe_life_state(),
            "privacy_settings": privacy_settings
            if isinstance(privacy_settings, dict)
            else asdict(privacy_settings)
            if is_dataclass(privacy_settings)
            else {},
            "relationship_state": self._safe_life_state().get("relationship_state", {}),
            "quiet_mode": self._safe_life_state().get("quiet_mode", {}),
            "boundary_state": self._safe_life_state().get("boundary_state", {}),
            "app_settings": self._safe_settings(),
        }
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        return MemoryCareResult(True, "export packed locally.", export_path=str(path))

    def validate_import_bundle(self, path: Path) -> MemoryCareResult:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return MemoryCareResult(False, "import bundle looks broken.")
        if not isinstance(data, dict):
            return MemoryCareResult(False, "import bundle is not a bundle.")
        memories = data.get("memories", [])
        if not isinstance(memories, list):
            return MemoryCareResult(False, "memory list looks strange.")
        for item in memories:
            if not isinstance(item, dict) or item.get("category") not in set(MEMORY_CATEGORIES.values()):
                return MemoryCareResult(False, "memory category rejected.")
            if not str(item.get("content", "")).strip():
                return MemoryCareResult(False, "empty imported crumb rejected.")
        return MemoryCareResult(True, "bundle looks safe enough.")

    def import_memories_from_json(self, path: Path, confirm: bool = False) -> MemoryCareResult:
        if not confirm:
            return MemoryCareResult(False, "import needs confirm.")
        validation = self.validate_import_bundle(path)
        if not validation.ok:
            return validation
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        count = 0
        with self._connection() as connection:
            for item in data.get("memories", []):
                connection.execute(
                    """
                    INSERT INTO memories(category, content, importance, confidence, emotional_weight, source, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["category"],
                        str(item["content"]).strip(),
                        self._clamp(float(item.get("importance", 0.5))),
                        self._clamp(float(item.get("confidence", item.get("importance", 0.5)))),
                        self._clamp(float(item.get("emotional_weight", item.get("importance", 0.5)))),
                        str(item.get("source", "import")),
                        json.dumps(item.get("metadata_json", {})),
                    ),
                )
                count += 1
        return MemoryCareResult(True, "imported local crumbs.", changed_count=count)

    def notebook_entries(self, section: str, limit: int = 50) -> list[NotebookEntry]:
        section = section.lower().strip()
        if section == "memories":
            return self.list_memories(limit=limit).entries
        if section == "journal":
            return self._table_entries("journal_entries", "journal", "short_summary", limit)
        if section == "dreams":
            return self._table_entries("fibi_dreams", "dreams", "dream_text", limit)
        if section == "preferences":
            return self._table_entries("preferences", "preferences", "value", limit, key_column="preference_key")
        if section == "projects":
            return self._table_entries("project_affinity", "projects", "project_name", limit, key_column="project_name")
        if section == "relationship":
            state = self._safe_life_state()
            relation = state.get("relationship_state", {})
            quiet = state.get("quiet_mode", {})
            boundary = state.get("boundary_state", {})
            return [
                NotebookEntry("relationship", "relationship", "relationship", f"style: {relation.get('interaction_style', 'shy')}; warmth: {relation.get('social_warmth', 20)}"),
                NotebookEntry("quiet", "relationship", "quiet mode", "on" if quiet.get("active") else "off"),
                NotebookEntry("boundary", "relationship", "boundary", f"{boundary.get('level', '')} {boundary.get('last_phrase', '')}".strip() or "none"),
            ]
        return []

    def _set_importance(self, memory_id: int, value: float, message: str) -> MemoryCareResult:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET importance = ?, confidence = ?, emotional_weight = MAX(emotional_weight, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (self._clamp(value), self._clamp(value), self._clamp(value), memory_id),
            )
        return MemoryCareResult(cursor.rowcount > 0, message if cursor.rowcount else "crumb not found.", changed_count=int(cursor.rowcount))

    def _memory_row(self, memory_id: int) -> sqlite3.Row | None:
        with self._connection() as connection:
            return connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

    def _memory_entry(self, row: sqlite3.Row) -> NotebookEntry:
        strength = "strong crumb" if float(row["confidence"]) >= 0.75 else "soft crumb" if float(row["confidence"]) >= 0.4 else "faint crumb"
        category = str(row["category"])
        return NotebookEntry(
            int(row["id"]),
            "memories",
            str(row["content"])[:80],
            f"{category} memory - {strength}.",
            MemorySourceInfo(
                category,
                str(row["source"]),
                float(row["confidence"]),
                float(row["emotional_weight"]),
                str(row["created_at"]),
                str(row["updated_at"]),
                str(row["last_accessed_at"]),
            ),
        )

    def _table_entries(
        self,
        table: str,
        section: str,
        body_column: str,
        limit: int,
        key_column: str = "id",
    ) -> list[NotebookEntry]:
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT ?",
                (max(1, min(100, limit)),),
            ).fetchall()
        entries: list[NotebookEntry] = []
        for row in rows:
            title = str(row[key_column]) if key_column in row.keys() else str(row["id"])
            entries.append(NotebookEntry(row[key_column] if key_column in row.keys() else row["id"], section, title[:80], str(row[body_column])[:240]))
        return entries

    def _rows(self, table: str) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(f"SELECT * FROM {table}").fetchall()
        return [{key: row[key] for key in row.keys()} for row in rows]

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _safe_life_state(self) -> dict:
        state = self._read_state()
        return {key: value for key, value in state.items() if "clipboard" not in key.lower() and "token" not in key.lower() and "key" not in key.lower()}

    @staticmethod
    def _safe_settings() -> dict:
        try:
            return json.loads(data_path("fibi_settings.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _category_value(category: str) -> str | None:
        normalized = category.lower().strip()
        if normalized in MEMORY_CATEGORIES.values():
            return normalized
        return MEMORY_CATEGORIES.get(normalized)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
