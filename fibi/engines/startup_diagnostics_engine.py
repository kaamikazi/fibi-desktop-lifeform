"""Startup diagnostics for Fibi desktop reliability."""

from __future__ import annotations

import importlib.util
import json
import platform
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from fibi.paths import data_dir, data_path
from fibi.runtime_paths import bundled_assets_dir, runtime_info, voice_models_dir
from fibi.version import APP_NAME, APP_VERSION, BUILD_CHANNEL


@dataclass(slots=True)
class DiagnosticCheck:
    name: str
    ok: bool
    message: str
    optional: bool = False


@dataclass(slots=True)
class StartupDiagnostics:
    app_name: str
    app_version: str
    build_channel: str
    created_at: str
    checks: list[DiagnosticCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok or check.optional for check in self.checks)


class StartupDiagnosticsEngine:
    """Check required and optional desktop runtime pieces without crashing."""

    OPTIONAL_IMPORTS = ("edge_tts", "pygame", "ollama", "emoji", "speech_recognition", "google.genai")

    def __init__(self, report_path: Path | None = None) -> None:
        self.report_path = Path(report_path) if report_path is not None else data_path("startup_diagnostics.json")
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_result: StartupDiagnostics | None = None

    def run(self) -> StartupDiagnostics:
        checks: list[DiagnosticCheck] = []
        checks.append(DiagnosticCheck("python_version", sys.version_info >= (3, 11), platform.python_version()))
        checks.append(DiagnosticCheck("pyqt6", self._has_import("PyQt6"), "PyQt6 available" if self._has_import("PyQt6") else "PyQt6 missing"))
        info = runtime_info()
        checks.append(DiagnosticCheck("runtime_mode", True, "packaged" if info.packaged else "source"))
        checks.append(DiagnosticCheck("portable_mode", True, "on" if info.portable else "off", optional=True))
        checks.append(self._check_data_dir())
        checks.append(self._check_sqlite(data_path("fibi_memory.db")))
        checks.append(self._path_check("rag_vector_dir", data_dir() / "rag_vectors", optional=True, make=True))
        checks.append(self._path_check("assets", bundled_assets_dir(), optional=False, make=False))
        checks.append(self._path_check("voice_models_dir", voice_models_dir(), optional=True, make=True))
        checks.append(self._json_check("voice_settings", data_path("voice_settings.json"), optional=True))
        checks.append(self._json_check("rvc_settings", data_path("voice_skin_settings.json"), optional=True))
        checks.append(self._json_check("app_settings", data_path("fibi_settings.json"), optional=True))
        for name in self.OPTIONAL_IMPORTS:
            checks.append(DiagnosticCheck(f"optional_{name}", self._has_import(name), "available" if self._has_import(name) else "optional missing", optional=True))
        checks.append(self._unclean_marker_check())
        result = StartupDiagnostics(APP_NAME, APP_VERSION, BUILD_CHANNEL, datetime.now().astimezone().isoformat(timespec="seconds"), checks)
        self.last_result = result
        self.report_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        return result

    def status_line(self) -> str:
        result = self.last_result or self.load_last() or self.run()
        failed = [check.name for check in result.checks if not check.ok and not check.optional]
        optional_missing = [check.name for check in result.checks if not check.ok and check.optional]
        if failed:
            return "startup checks: " + ", ".join(failed[:3]) + " need help."
        if optional_missing:
            return f"startup ok. optional sleepy: {len(optional_missing)}."
        return "startup ok. tiny boots tied."

    def load_last(self) -> StartupDiagnostics | None:
        try:
            raw = json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        checks = [DiagnosticCheck(**item) for item in raw.get("checks", []) if isinstance(item, dict)]
        try:
            return StartupDiagnostics(str(raw.get("app_name", APP_NAME)), str(raw.get("app_version", APP_VERSION)), str(raw.get("build_channel", BUILD_CHANNEL)), str(raw.get("created_at", "")), checks)
        except TypeError:
            return None

    @staticmethod
    def _has_import(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    @staticmethod
    def _check_data_dir() -> DiagnosticCheck:
        try:
            path = data_dir()
            probe = path / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return DiagnosticCheck("data_dir_writable", True, str(path))
        except OSError as exc:
            return DiagnosticCheck("data_dir_writable", False, str(exc))

    @staticmethod
    def _check_sqlite(path: Path) -> DiagnosticCheck:
        if not path.exists():
            return DiagnosticCheck("memory_db_accessible", True, "not created yet", optional=True)
        connection: sqlite3.Connection | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(path)
            connection.execute("SELECT 1")
            return DiagnosticCheck("memory_db_accessible", True, str(path))
        except sqlite3.Error as exc:
            return DiagnosticCheck("memory_db_accessible", False, str(exc))
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _path_check(name: str, path: Path, optional: bool, make: bool) -> DiagnosticCheck:
        try:
            if make:
                path.mkdir(parents=True, exist_ok=True)
            return DiagnosticCheck(name, path.exists(), str(path), optional)
        except OSError as exc:
            return DiagnosticCheck(name, False, str(exc), optional)

    @staticmethod
    def _json_check(name: str, path: Path, optional: bool) -> DiagnosticCheck:
        if not path.exists():
            return DiagnosticCheck(name, True, "not created yet", optional)
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return DiagnosticCheck(name, True, "readable", optional)
        except (OSError, json.JSONDecodeError) as exc:
            return DiagnosticCheck(name, False, str(exc), optional)

    @staticmethod
    def _unclean_marker_check() -> DiagnosticCheck:
        try:
            raw = json.loads(data_path("fibi_state.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DiagnosticCheck("shutdown_marker", True, "no marker yet", optional=True)
        clean = raw.get("clean_shutdown")
        if clean is False:
            return DiagnosticCheck("shutdown_marker", True, "previous shutdown looked unclean", optional=True)
        return DiagnosticCheck("shutdown_marker", True, "clean or unknown", optional=True)
