"""Tests for Fibi v0.24 beta release hardening."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_beta_first_run_limitations_and_self_test_commands() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        first_run = core.respond("/first run status").display_text
        assert "cloud off" in first_run
        assert "voice off" in first_run
        assert "crumbs local" in first_run

        assert "beta mode" in core.respond("/beta status").display_text
        assert "beta mode on" in core.respond("/beta on").display_text
        assert core.app_settings.settings.beta_mode is True
        assert "beta mode off" in core.respond("/beta off").display_text
        assert core.app_settings.settings.beta_mode is False

        limitations = core.respond("/limitations").display_text
        assert "RVC" in limitations
        assert "cloud off" in limitations

        assert "self test survived" in core.respond("/self test").display_text


def test_support_bundle_alias_and_report_exclusions() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data = root / "data"
        os.environ["FIBI_DATA_DIR"] = str(data)
        core, _, _ = make_core(root / "core", [], [])
        (data / "fibi_memory.db").write_text("private memory", encoding="utf-8")
        (data / "voice_models").mkdir(parents=True, exist_ok=True)
        (data / "voice_models" / "model.pth").write_text("private model", encoding="utf-8")
        (data / ".env").write_text("API_KEY=SECRET", encoding="utf-8")

        reply = core.respond("/support bundle").display_text
        assert "packed the safe crumbs" in reply
        reports = sorted((data / "reports").glob("fibi_error_report_*.zip"))
        assert reports
        with zipfile.ZipFile(reports[-1]) as bundle:
            names = set(bundle.namelist())
            joined = "\n".join(bundle.read(name).decode("utf-8", errors="replace") for name in names)
        assert "runtime_paths.json" in names
        assert "beta_mode.txt" in names
        assert "fibi_memory.db" not in joined
        assert "private memory" not in joined
        assert "private model" not in joined
        assert "SECRET" not in joined


def test_docs_and_zip_name_exist() -> None:
    for relative in [
        "docs/RELEASE_NOTES_V024.md",
        "docs/RESET_AND_UNINSTALL.md",
        "docs/QA_RESULTS_V024.md",
        "docs/RELEASE_QA_V023.md",
        "docs/GUI_MANUAL_QA_V022.md",
    ]:
        assert (PROJECT_ROOT / relative).exists()
    assert release_zip_path().name == "Fibi_Chubi_v0.30.2_windows_beta.zip"


