"""Tests for Fibi v0.25 installer and beta distribution flow."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from tests.smoke_v012_actions import make_core
from tools import build_installer, build_windows, make_checksums

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_inno_script_exists_and_excludes_sensitive_paths() -> None:
    script = PROJECT_ROOT / "packaging" / "inno" / "FibiChubi.iss"
    assert script.exists()
    text = script.read_text(encoding="utf-8").lower()
    for forbidden in ["data\\*", "logs\\*", "voice_models\\*", "*.env", "*.pth", "*.index", "*.db"]:
        assert forbidden in text
    assert "fibi_chubi_setup_v0.30.0" in text


def test_install_status_data_folder_and_reset_commands() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        launched: list[str] = []
        core, _, _ = make_core(root / "core", opened, launched)

        assert "install status" in core.respond("/install status").display_text
        assert str(root / "data") in core.respond("/data folder").display_text
        assert "folder opened" in core.respond("/open data folder").display_text
        assert launched and launched[-1] == str(root / "data")
        assert "reset:" in core.respond("/reset instructions").display_text


def test_onboarding_state_persists_and_defaults_stay_safe() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])
        state = core.app_settings.complete_setup(skipped=True)
        assert state.completed
        assert core.app_settings.first_run_state().completed
        assert not core.privacy.settings.allow_cloud_model
        assert not core.privacy.settings.allow_nvidia_api
        assert not core.voice_settings.settings.allow_voice_input
        assert not core.voice_skin_settings.settings.rvc_enabled


def test_release_manifest_and_checksums_generated(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        dist = root / "dist"
        release = dist / "Fibi Chubi"
        release.mkdir(parents=True)
        exe = release / "Fibi Chubi.exe"
        exe.write_text("exe", encoding="utf-8")
        zip_path = dist / "Fibi_Chubi_v0.30.0_windows_beta.zip"
        zip_path.write_text("zip", encoding="utf-8")
        installer = dist / "installers" / "Fibi_Chubi_Setup_v0.30.0.exe"
        installer.parent.mkdir()
        installer.write_text("installer", encoding="utf-8")

        monkeypatch.setattr(build_windows, "DIST_DIR", dist)
        monkeypatch.setattr(build_windows, "RELEASE_DIR", release)
        manifest_path = build_windows.write_release_manifest(zip_path, installer)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["app_version"] == "0.30.0"
        assert manifest["checksums"]["zip_sha256"]

        monkeypatch.setattr(make_checksums, "DIST_DIR", dist)
        monkeypatch.setattr(make_checksums, "CHECKSUM_PATH", dist / "checksums_v0.30.0.txt")
        monkeypatch.setattr(make_checksums, "INSTALLER_PATH", installer)
        monkeypatch.setattr(make_checksums, "release_zip_path", lambda: zip_path)
        checksums = make_checksums.generate_checksums()
        assert "Fibi_Chubi_v0.30.0_windows_beta.zip" in checksums.read_text(encoding="utf-8")


def test_build_installer_handles_missing_inno_gracefully(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        release = root / "dist" / "Fibi Chubi"
        release.mkdir(parents=True)
        (release / "Fibi Chubi.exe").write_text("exe", encoding="utf-8")
        installer = root / "dist" / "installers" / "Fibi_Chubi_Setup_v0.30.0.exe"

        monkeypatch.setattr(build_installer, "RELEASE_DIR", release)
        monkeypatch.setattr(build_installer, "INSTALLER_PATH", installer)
        monkeypatch.setattr(build_installer, "find_iscc", lambda: None)
        monkeypatch.setattr(build_installer, "verify_release", lambda release_dir: [])
        monkeypatch.setattr(build_installer, "write_release_manifest", lambda *args, **kwargs: root / "manifest.json")
        monkeypatch.setattr(build_installer, "generate_checksums", lambda: root / "checksums.txt")

        assert build_installer.build_installer(skip_build=False) == 0
        reports = list((root / "data" / "reports").glob("installer_build_report_v0.30.0.json"))
        assert reports
        assert json.loads(reports[0].read_text(encoding="utf-8"))["status"] == "inno_missing"


