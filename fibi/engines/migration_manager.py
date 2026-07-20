"""Central idempotent SQLite migration tracking."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

LOGGER = logging.getLogger(__name__)
Migration = Callable[[sqlite3.Connection], None]


class MigrationManager:
    """Apply named SQLite migrations once per database."""

    def __init__(self, database_path: Path, namespace: str = "fibi") -> None:
        self.database_path = Path(database_path)
        self.namespace = namespace
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def apply(self, migrations: dict[str, Migration]) -> list[str]:
        applied: list[str] = []
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        namespace TEXT NOT NULL,
                        version TEXT NOT NULL,
                        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY(namespace, version)
                    )
                    """
                )
                existing = {
                    row[0]
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations WHERE namespace = ?",
                        (self.namespace,),
                    ).fetchall()
                }
                for version, migration in migrations.items():
                    if version in existing:
                        continue
                    migration(connection)
                    connection.execute(
                        "INSERT INTO schema_migrations(namespace, version) VALUES (?, ?)",
                        (self.namespace, version),
                    )
                    applied.append(version)
                    LOGGER.info("Applied migration %s:%s", self.namespace, version)
        finally:
            connection.close()
        return applied
