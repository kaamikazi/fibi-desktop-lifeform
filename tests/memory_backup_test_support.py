"""Fictional temporary persistence fixtures for backup tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fibi.memory_backup.models import BackupRequest, BackupResult
from fibi.memory_backup.service import MemoryBackupService

SYNTHETIC_SENTINEL = "Fictional comet notebook memory."
FIXED_TIME = datetime(2026, 8, 13, 1, 30, tzinfo=timezone.utc)


def create_synthetic_data(root: Path, *, support_files: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 12")
        connection.execute("CREATE TABLE memories(id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
        connection.execute("CREATE TABLE rag_memories(id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
        connection.execute("CREATE TABLE rag_memory_events(id INTEGER PRIMARY KEY, event_type TEXT NOT NULL)")
        connection.execute("INSERT INTO memories(content) VALUES (?)", (SYNTHETIC_SENTINEL,))
        connection.execute("INSERT INTO rag_memories(content) VALUES (?)", ("Fictional RAG comet memory.",))
    if support_files:
        (root / "fibi_state.json").write_text(
            json.dumps(
                {
                    "last_user_message": SYNTHETIC_SENTINEL,
                    "memory_consent": {"memory_learning_enabled": True},
                }
            ),
            encoding="utf-8",
        )
        deletion = root / "memory" / "memory_deletion_log.jsonl"
        deletion.parent.mkdir(parents=True)
        deletion.write_text(json.dumps({"event": "synthetic_delete", "record": 7}) + "\n", encoding="utf-8")
    rag = root / "rag"
    rag.mkdir(exist_ok=True)
    (rag / "fibi_rag.faiss").write_bytes(b"synthetic-derived-index")
    (rag / "fibi_rag_ids.json").write_text("[]", encoding="utf-8")
    (rag / "fibi_rag_manifest.json").write_text("{}", encoding="utf-8")
    (root / "logs").mkdir(exist_ok=True)
    (root / "logs" / "runtime.log").write_text("out of scope", encoding="utf-8")
    return database


def create_backup(data_root: Path, output_root: Path, **service_kwargs: object) -> BackupResult:
    service = MemoryBackupService(
        repository_root=data_root.parent / "fictional-repository",
        id_factory=lambda: "fixture123",
        clock=lambda: FIXED_TIME,
        **service_kwargs,
    )
    result = service.create(
        BackupRequest(
            data_root=data_root,
            output_root=output_root,
            confirm_private_output=True,
        )
    )
    assert result.bundle_path is not None if result.success else True
    return result


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_hash(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def read_manifest(bundle: Path) -> dict:
    return json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(bundle: Path, manifest: dict) -> None:
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
