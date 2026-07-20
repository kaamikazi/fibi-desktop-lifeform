"""Migrate legacy Fibi memories into the RAG memory tables.

Dry-run is the default:
    python tools/migrate_legacy_memory_to_rag.py --dry-run

Apply writes:
    python tools/migrate_legacy_memory_to_rag.py --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.paths import data_path
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade


def legacy_rows(database_path: Path) -> list[sqlite3.Row]:
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "memories" not in tables:
            return []
        return list(connection.execute("SELECT * FROM memories ORDER BY id ASC").fetchall())
    finally:
        connection.close()


def migrate(database_path: Path, apply: bool) -> dict:
    rag = RAGMemoryServiceFacade(database_path=database_path)
    report = {"database": str(database_path), "apply": apply, "seen": 0, "migrated": 0, "skipped_duplicates": 0}
    for row in legacy_rows(database_path):
        report["seen"] += 1
        content = str(row["content"]).strip()
        duplicate = rag.service.detect_duplicate(content)
        if duplicate.is_duplicate:
            report["skipped_duplicates"] += 1
            continue
        if apply:
            metadata = {}
            try:
                metadata = json.loads(row["metadata_json"])
            except (KeyError, TypeError, json.JSONDecodeError):
                metadata = {}
            metadata["legacy_memory_id"] = int(row["id"])
            metadata["emotional_weight"] = float(row["emotional_weight"]) if "emotional_weight" in row.keys() else float(row["importance"])
            rag.service.add_memory(
                content,
                category=str(row["category"]),
                source=str(row["source"]),
                source_id=f"legacy-memory:{row['id']}",
                importance=float(row["importance"]),
                confidence=float(row["confidence"]) if "confidence" in row.keys() else float(row["importance"]),
                metadata=metadata,
                provenance={"migrated_from": "legacy.memories", "legacy_id": int(row["id"])},
                allow_duplicate=False,
            )
            report["migrated"] += 1
    report_dir = data_path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"legacy_memory_to_rag_{stamp}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy Fibi memories to RAG.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Scan only. This is the default.")
    mode.add_argument("--apply", action="store_true", help="Write missing legacy memories into RAG.")
    parser.add_argument("--database", type=Path, default=data_path("fibi_memory.db"))
    args = parser.parse_args()
    report = migrate(args.database, apply=bool(args.apply))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
