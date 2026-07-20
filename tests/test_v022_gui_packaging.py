"""Unit coverage for Fibi v0.22 diagnostics, reporting, and packaging prep."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from fibi.engines.error_report_engine import ErrorReportEngine
from fibi.engines.shutdown_manager import ShutdownManager
from fibi.engines.startup_diagnostics_engine import StartupDiagnosticsEngine
from tests.smoke_v012_actions import make_core

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_startup_diagnostics_optional_missing_is_not_failure() -> None:
    with tempfile.TemporaryDirectory() as temp:
        os.environ["FIBI_DATA_DIR"] = str(Path(temp) / "data")
        result = StartupDiagnosticsEngine(Path(temp) / "diag.json").run()
        assert result.checks
        assert any(check.name.startswith("optional_") for check in result.checks)
        assert all(check.ok or check.optional for check in result.checks if check.name.startswith("optional_"))


def test_shutdown_manager_persists_marker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        manager = ShutdownManager(Path(temp) / "shutdown.json")
        result = manager.shutdown()
        assert result.ok
        marker = manager.last_marker()
        assert marker["ok"] is True
        assert marker["message"]


def test_error_report_masks_secrets_and_excludes_private_payloads() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        data = root / "data"
        data.mkdir(parents=True)
        dummy_secret = "<dummy-secret-value>"
        (data / "fibi.log").write_text(f"password={dummy_secret}\n", encoding="utf-8")
        (data / "fibi_memory.db").write_text("do not include", encoding="utf-8")
        path = ErrorReportEngine(root / "reports").export(f"api_key={dummy_secret}", "route", [f"token={dummy_secret}"])
        with zipfile.ZipFile(path) as bundle:
            names = set(bundle.namelist())
            text = "\n".join(bundle.read(name).decode("utf-8", errors="replace") for name in names)
        assert "fibi_memory.db" not in names
        assert dummy_secret not in text
        assert "health_snapshot.txt" in names


def test_core_version_health_and_error_recording() -> None:
    with tempfile.TemporaryDirectory() as temp:
        os.environ["FIBI_DATA_DIR"] = str(Path(temp) / "data")
        core, _, _ = make_core(Path(temp) / "core", [], [])
        assert "Fibi Chubi v0.30.0" in core.respond("/version").display_text
        health = core.respond("/health gui").display_text
        assert "uptime" in health
        core.record_ui_error("test", RuntimeError("squeak"))
        assert "test" in core.get_gui_health_snapshot()


def test_packaging_files_exist() -> None:
    expected = [
        "packaging/README.md",
        "packaging/pyinstaller_fibi.spec",
        "packaging/icon_notes.md",
        "packaging/release_checklist.md",
        "docs/GUI_MANUAL_QA_V022.md",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).exists()


