"""Local data folder health checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fibi.engines.memory_engine import DEFAULT_DB_PATH, SCHEMA_PATH
from fibi.engines.types import DataHealthResult
from fibi.paths import data_dir, data_path


class DataHealthEngine:
    def __init__(
        self,
        database_path: Path = DEFAULT_DB_PATH,
        state_path: Path | None = None,
        settings_path: Path | None = None,
        export_dir: Path | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.state_path = Path(state_path) if state_path else data_path("fibi_state.json")
        self.settings_path = Path(settings_path) if settings_path else data_path("fibi_settings.json")
        self.export_dir = Path(export_dir) if export_dir else data_dir() / "exports"

    def check(self) -> DataHealthResult:
        checks: dict[str, bool] = {}
        try:
            folder = data_dir()
            checks["data_dir"] = folder.exists() and folder.is_dir()
            checks["state_file"] = self.state_path.exists()
            checks["settings_file"] = self.settings_path.exists()
            checks["export_folder"] = self.export_dir.exists() or self._mkdir(self.export_dir)
            checks["memory_db"] = self.database_path.exists()
            checks["schema_file"] = SCHEMA_PATH.exists()
            checks.update(self._db_tables())
        except Exception:
            return DataHealthResult(False, "one crumb jar looks cracked.", checks)
        return DataHealthResult(all(checks.values()), "crumbs ok. nest ok. brain local." if all(checks.values()) else "one crumb jar looks cracked.", checks)

    @staticmethod
    def _mkdir(path: Path) -> bool:
        path.mkdir(parents=True, exist_ok=True)
        return path.exists()

    def _db_tables(self) -> dict[str, bool]:
        needed = {"memories", "journal_entries", "inner_life_entries", "fibi_dreams"}
        if not self.database_path.exists():
            return {f"table_{name}": False for name in needed}
        connection = sqlite3.connect(self.database_path, timeout=5)
        try:
            rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            names = {row[0] for row in rows}
        finally:
            connection.close()
        return {f"table_{name}": name in names for name in needed}
