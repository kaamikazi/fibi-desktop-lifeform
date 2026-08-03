"""Read-only structural inventory for Fibi's persistent memory ecosystem."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fibi.memory.policy import AuthoritativeOwner, DataClass


@dataclass(frozen=True, slots=True)
class StoreDefinition:
    store_id: str
    relative_path: str
    kind: str
    data_class: DataClass
    target_owner: AuthoritativeOwner
    current_owner_modules: tuple[str, ...]
    tables: tuple[str, ...] = ()
    glob: str = ""
    derived: bool = False


@dataclass(frozen=True, slots=True)
class TableInventory:
    name: str
    row_count: int
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoreInventory:
    store_id: str
    path: str
    kind: str
    data_class: str
    target_owner: str
    current_owner_modules: tuple[str, ...]
    exists: bool
    size_bytes: int = 0
    file_count: int = 0
    tables: tuple[TableInventory, ...] = ()
    warnings: tuple[str, ...] = ()
    derived: bool = False


@dataclass(frozen=True, slots=True)
class MemoryInventoryReport:
    schema_version: int
    stores: tuple[StoreInventory, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_public_dict(self) -> dict[str, Any]:
        """Return structural metadata only; no memory values or absolute paths."""

        return {
            "schema_version": self.schema_version,
            "content_included": False,
            "stores": [asdict(store) for store in self.stores],
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_public_dict(), indent=2)


KNOWN_STORES: tuple[StoreDefinition, ...] = (
    StoreDefinition("legacy_memory", "fibi_memory.db", "sqlite", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, ("fibi.engines.memory_engine", "fibi.engines.memory_care_engine"), ("memories", "conversations")),
    StoreDefinition("rag_memory", "fibi_memory.db", "sqlite", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, ("fibi.rag.repository", "fibi.rag.service"), ("rag_memories", "rag_memory_events")),
    StoreDefinition("document_memory", "fibi_memory.db", "sqlite", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.NOTES_SERVICE, ("fibi.rag.ingestion", "fibi.rag.repository"), ("rag_documents", "rag_document_chunks")),
    StoreDefinition("conversation_journal", "fibi_memory.db", "sqlite", DataClass.TEMPORARY_CONTEXT, AuthoritativeOwner.CONVERSATION_STORE, ("fibi.engines.journal_engine",), ("journal_entries", "daily_summaries")),
    StoreDefinition("derived_preferences", "fibi_memory.db", "sqlite", DataClass.COMPANION_CONFIGURATION, AuthoritativeOwner.COMPANION_STATE_SERVICE, ("fibi.engines.preference_engine", "fibi.engines.pattern_engine"), ("preferences", "project_affinity")),
    StoreDefinition("companion_opinions", "fibi_memory.db", "sqlite", DataClass.COMPANION_CONFIGURATION, AuthoritativeOwner.COMPANION_STATE_SERVICE, ("fibi.engines.opinion_engine",), ("opinions",)),
    StoreDefinition("inner_life", "fibi_memory.db", "sqlite", DataClass.COMPANION_RELATIONSHIP_STATE, AuthoritativeOwner.COMPANION_STATE_SERVICE, ("fibi.engines.inner_life_engine",), ("inner_life_entries", "fibi_dreams")),
    StoreDefinition("companion_state", "fibi_state.json", "json", DataClass.COMPANION_CONFIGURATION, AuthoritativeOwner.COMPANION_STATE_SERVICE, ("fibi.engines.life_engine", "fibi.engines.relationship_engine", "fibi.engines.memory_consent_engine", "fibi.engines.privacy_settings_engine")),
    StoreDefinition("project_workspaces", "project_workspaces.json", "json", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.PROJECT_SERVICE, ("fibi.engines.project_workspace_engine",)),
    StoreDefinition("work_sessions", "work_sessions.json", "json", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.WORK_SESSION_SERVICE, ("fibi.engines.work_session_engine",)),
    StoreDefinition("browser_notes", "browser/browser_notes.jsonl", "jsonl", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.NOTES_SERVICE, ("fibi.engines.browser_helper_engine",)),
    StoreDefinition("browser_sessions", "browser/browser_sessions.jsonl", "jsonl", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.TASK_AUDIT_SERVICE, ("fibi.engines.browser_helper_engine",)),
    StoreDefinition("workflow_state", "workflows/workflow_state.json", "json", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.WORK_SESSION_SERVICE, ("fibi.engines.workflow_recipe_engine",)),
    StoreDefinition("workflow_runs", "workflows/workflow_runs.jsonl", "jsonl", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.TASK_AUDIT_SERVICE, ("fibi.engines.workflow_recipe_engine",)),
    StoreDefinition("action_audit", "action_journal.jsonl", "jsonl", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.TASK_AUDIT_SERVICE, ("fibi.engines.action_journal_engine",)),
    StoreDefinition("memory_deletion_audit", "memory/memory_deletion_log.jsonl", "jsonl", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.PERMISSION_AUDIT_SERVICE, ("fibi.engines.memory_review_engine",)),
    StoreDefinition("rag_index", "rag", "file_set", DataClass.DERIVED_INDEX, AuthoritativeOwner.SEARCH_INDEX, ("fibi.rag.vector_store",), glob="fibi_rag*", derived=True),
    StoreDefinition("memory_exports", "exports", "file_set", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.MEMORY_SERVICE, ("fibi.engines.memory_care_engine",), glob="*.json"),
    StoreDefinition("memory_review_exports", "reports", "file_set", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.MEMORY_SERVICE, ("fibi.engines.memory_review_engine",), glob="memory_export_*"),
    StoreDefinition("migration_reports", "reports", "file_set", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.TASK_AUDIT_SERVICE, ("tools.migrate_legacy_memory_to_rag",), glob="legacy_memory_to_rag_*"),
)


class MemoryInventoryScanner:
    """Inspect paths, schemas, and counts without initializing any store."""

    def __init__(self, data_root: Path, definitions: tuple[StoreDefinition, ...] = KNOWN_STORES) -> None:
        self.data_root = Path(data_root)
        self.definitions = definitions

    def scan(self) -> MemoryInventoryReport:
        sqlite_cache: dict[Path, tuple[dict[str, TableInventory], tuple[str, ...]]] = {}
        stores: list[StoreInventory] = []
        warnings: list[str] = []
        for definition in self.definitions:
            path = self.data_root / definition.relative_path
            table_items: tuple[TableInventory, ...] = ()
            local_warnings: tuple[str, ...] = ()
            file_count = 0
            size_bytes = path.stat().st_size if path.is_file() else 0
            if definition.kind == "sqlite" and path.exists():
                if path not in sqlite_cache:
                    sqlite_cache[path] = self._inspect_sqlite(path)
                table_map, local_warnings = sqlite_cache[path]
                table_items = tuple(table_map[name] for name in definition.tables if name in table_map)
                missing = [name for name in definition.tables if name not in table_map]
                if missing:
                    local_warnings = (*local_warnings, "missing tables: " + ", ".join(missing))
            elif definition.kind == "file_set" and path.is_dir():
                matches = [item for item in path.glob(definition.glob) if item.is_file()]
                file_count = len(matches)
                size_bytes = sum(item.stat().st_size for item in matches)
            stores.append(
                StoreInventory(
                    store_id=definition.store_id,
                    path="data/" + definition.relative_path.replace("\\", "/"),
                    kind=definition.kind,
                    data_class=definition.data_class.value,
                    target_owner=definition.target_owner.value,
                    current_owner_modules=definition.current_owner_modules,
                    exists=path.exists(),
                    size_bytes=size_bytes,
                    file_count=file_count,
                    tables=table_items,
                    warnings=local_warnings,
                    derived=definition.derived,
                )
            )
            warnings.extend(f"{definition.store_id}: {warning}" for warning in local_warnings)
        return MemoryInventoryReport(1, tuple(stores), tuple(warnings))

    @staticmethod
    def _inspect_sqlite(path: Path) -> tuple[dict[str, TableInventory], tuple[str, ...]]:
        table_map: dict[str, TableInventory] = {}
        warnings: list[str] = []
        try:
            connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=2)
            connection.execute("PRAGMA query_only = ON")
            try:
                names = [
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    )
                ]
                for name in names:
                    escaped = name.replace('"', '""')
                    row_count = int(connection.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0])
                    columns = tuple(
                        f"{row[1]}:{row[2]}" for row in connection.execute(f'PRAGMA table_info("{escaped}")')
                    )
                    table_map[name] = TableInventory(name, row_count, columns)
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as error:
            warnings.append(f"sqlite inspection unavailable: {type(error).__name__}")
        return table_map, tuple(warnings)
