"""Tests for Fibi v0.23 packaged runtime paths and release checks."""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

from fibi.engines.error_report_engine import ErrorReportEngine
from fibi.runtime_paths import (
    bundled_assets_dir,
    runtime_info,
    user_data_dir,
    voice_models_dir,
)
from tools.verify_release import forbidden_release_files
from tests.smoke_v012_actions import make_core


def _simulate_packaged(monkeypatch: pytest.MonkeyPatch, root: Path) -> tuple[Path, Path]:
    exe_dir = root / "release" / "Fibi Chubi"
    bundle = exe_dir / "_internal"
    exe_dir.mkdir(parents=True)
    (exe_dir / "Fibi Chubi.exe").write_text("stub", encoding="utf-8")
    (bundle / "config").mkdir(parents=True)
    (bundle / "config" / "default_settings.json").write_text(
        '{"app_settings": {"minimize_to_tray": true, "allow_project_checks": true}}',
        encoding="utf-8",
    )
    (bundle / "fibi" / "ui" / "assets").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "Fibi Chubi.exe"))
    monkeypatch.delenv("FIBI_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(root / "AppData" / "Roaming"))
    return exe_dir, bundle


def test_runtime_paths_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIBI_DATA_DIR", raising=False)
    info = runtime_info()
    assert not info.packaged
    assert info.user_data_dir.name == "data"
    assert voice_models_dir().name == "voice_models"


def test_runtime_paths_simulated_packaged_appdata(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        _simulate_packaged(monkeypatch, root)
        data = user_data_dir()
        assert data == root / "AppData" / "Roaming" / "Fibi Chubi"
        assert (data / "default_settings.json").exists()
        assert (data / "fibi_settings.json").exists()
        assert bundled_assets_dir().exists()


def test_runtime_paths_simulated_portable(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        exe_dir, _ = _simulate_packaged(monkeypatch, root)
        (exe_dir / "portable_mode.txt").write_text("portable", encoding="utf-8")
        info = runtime_info()
        assert info.packaged
        assert info.portable
        assert info.user_data_dir == exe_dir / "data"


def test_forbidden_release_files_detect_user_data_and_models() -> None:
    with tempfile.TemporaryDirectory() as temp:
        release = Path(temp) / "Fibi Chubi"
        (release / "_internal" / "fibi" / "ui" / "assets").mkdir(parents=True)
        (release / "Fibi Chubi.exe").write_text("stub", encoding="utf-8")
        (release / "data").mkdir()
        (release / "data" / "fibi_memory.db").write_text("private", encoding="utf-8")
        (release / "voice_models").mkdir()
        (release / "voice_models" / "model.pth").write_text("private", encoding="utf-8")
        (release / ".env").write_text("SECRET=1", encoding="utf-8")
        forbidden = {str(path).replace("\\", "/") for path in forbidden_release_files(release)}
        assert "data/fibi_memory.db" in forbidden
        assert "voice_models/model.pth" in forbidden
        assert ".env" in forbidden


def test_build_metadata_command_and_error_report_path(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        monkeypatch.setenv("FIBI_DATA_DIR", str(root / "data"))
        core, _, _ = make_core(root / "core", [], [])
        detailed = core.respond("/version detailed").display_text
        assert "Fibi Chubi v0.30.2" in detailed
        report = ErrorReportEngine().export("health api_key=SECRET", "route", ["token=SECRET"])
        assert report.parent == root / "data" / "reports"
        with zipfile.ZipFile(report) as bundle:
            joined = "\n".join(bundle.read(name).decode("utf-8", errors="replace") for name in bundle.namelist())
        assert "SECRET" not in joined


