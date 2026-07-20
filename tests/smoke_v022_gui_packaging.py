"""Smoke tests for Fibi v0.22 GUI reliability and packaging prep."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.error_report_engine import ErrorReportEngine
from fibi.engines.shutdown_manager import ShutdownManager
from fibi.engines.startup_diagnostics_engine import StartupDiagnosticsEngine
from tests.smoke_v012_actions import make_core


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")

        diagnostics = StartupDiagnosticsEngine(root / "startup_diagnostics.json").run()
        assert diagnostics.checks
        assert any(check.name == "python_version" and check.ok for check in diagnostics.checks)

        shutdown = ShutdownManager(root / "shutdown_marker.json")
        report = shutdown.shutdown([("marker", lambda: None)])
        assert report.ok
        assert shutdown.last_marker().get("ok") is True

        core, _, _ = make_core(root / "core", [], [])
        assert "Fibi Chubi v0.30.2" in core.respond("/version").display_text
        assert "uptime" in core.respond("/health gui").display_text
        assert core.respond("/startup diagnostics").display_text

        secret_log = root / "data" / "fibi.log"
        secret_log.parent.mkdir(parents=True, exist_ok=True)
        dummy_secret = "<dummy-secret-value>"
        secret_log.write_text(f"api_key={dummy_secret}\n", encoding="utf-8")
        report_path = ErrorReportEngine(root / "reports").export(f"health ok api_key={dummy_secret}", "route", [f"token={dummy_secret}"])
        assert report_path.exists()
        import zipfile

        with zipfile.ZipFile(report_path) as bundle:
            joined = "\n".join(bundle.read(name).decode("utf-8", errors="replace") for name in bundle.namelist())
        assert dummy_secret not in joined

        for path in [
            PROJECT_ROOT / "packaging" / "README.md",
            PROJECT_ROOT / "packaging" / "pyinstaller_fibi.spec",
            PROJECT_ROOT / "packaging" / "icon_notes.md",
            PROJECT_ROOT / "packaging" / "release_checklist.md",
            PROJECT_ROOT / "docs" / "GUI_MANUAL_QA_V022.md",
        ]:
            assert path.exists()

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        gui = subprocess.run([sys.executable, "app.py", "--gui-smoke"], cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, timeout=30)
        assert gui.returncode == 0
        assert "GUI_SMOKE_OK" in gui.stdout or "GUI_SMOKE_SKIPPED_OR_FAILED" in gui.stdout

    print("Fibi v0.22 GUI reliability and packaging smoke tests passed.")


if __name__ == "__main__":
    run()


