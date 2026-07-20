"""Tests for Fibi v0.26 beta feedback and local issue tracking."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from fibi.engines.update_manifest_engine import UpdateManifestEngine
from fibi.engines.version_compare import compare_versions
from tests.smoke_v012_actions import make_core


def test_issue_lifecycle_and_export() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        created = core.respond("/issue new voice is broken | RVC still sounds like old voice")
        assert "issue saved" in created.display_text
        issue = core.issues.last()
        assert issue is not None
        assert issue.category in {"voice", "rvc"}
        assert (root / "data" / "issues" / "issues.jsonl").exists()

        assert issue.issue_id in core.respond("/issue list").display_text
        assert "closed" in core.respond(f"/issue close {issue.issue_id}").display_text
        assert "reopened" in core.respond(f"/issue reopen {issue.issue_id}").display_text
        exported = core.respond(f"/issue export {issue.issue_id}")
        assert "packed issue crumb" in exported.display_text
        assert (root / "data" / "reports" / f"{issue.issue_id}_issue_export.md").exists()


def test_feedback_export_and_clear() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        assert "feedback saved" in core.respond("/feedback new please add a smaller sleepy mode").display_text
        export = core.respond("/feedback export").display_text
        assert "packed feedback crumbs" in export
        exported = json.loads((root / "data" / "reports" / "fibi_feedback_export.json").read_text(encoding="utf-8"))
        assert exported and exported[0]["feedback_type"] in {"feature_request", "personality"}
        assert "cleared 1" in core.respond("/feedback clear exported confirm").display_text


def test_issue_linked_support_bundle_contains_safe_metadata() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        dummy_secret = "<dummy-secret-value>"
        core.respond(f"/issue new crash on startup | api_key={dummy_secret} should be masked")
        issue = core.issues.last()
        assert issue is not None
        response = core.respond(f"/support bundle for issue {issue.issue_id}")
        assert "packed the safe crumbs" in response.display_text
        linked = core.issues.get(issue.issue_id)
        assert linked is not None and linked.linked_support_bundle

        with zipfile.ZipFile(linked.linked_support_bundle) as bundle:
            names = set(bundle.namelist())
            assert "issue_metadata.json" in names
            assert "fibi_memory.db" not in names
            issue_metadata = bundle.read("issue_metadata.json").decode("utf-8")
            assert dummy_secret not in issue_metadata


def test_release_health_update_manifest_and_version_compare() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        manifest = root / "updates" / "update_manifest.json"
        manifest.parent.mkdir()
        manifest.write_text(
            json.dumps(
                {
                    "latest_version": "0.30.3",
                    "channel": "beta",
                    "release_date": "2026-07-08",
                    "release_notes": "tiny update prep.",
                    "download_url": "https://example.invalid/fibi.zip",
                    "sha256": "abc",
                    "required": False,
                    "min_supported_version": "0.26.0",
                }
            ),
            encoding="utf-8",
        )
        engine = UpdateManifestEngine(manifest)
        assert "0.30.3" in engine.status_line()
        assert "tiny update prep" in engine.notes_line()
        assert "no auto-download" in engine.safety_line()
        assert compare_versions("0.26.0", "0.30.3").relation == "older"

        core, _, _ = make_core(root / "core", [], [])
        core.updates = engine
        core.release_health.updates = engine
        assert "release health v0.30.3" in core.respond("/release health").display_text
        assert "no download" in core.respond("/update status").display_text


def test_debug_commands_mask_sensitive_values_and_local_intents() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        dummy_secret = "<dummy-secret-value>"
        core._last_error_summary = f"API_KEY={dummy_secret}"
        debug = core.respond("/debug recent errors").display_text
        assert dummy_secret not in debug
        assert "[secret]" in debug
        assert "issue saved" in core.respond("Fibi crashed").display_text
        assert "bug jar opened" in core.respond("report a bug").display_text
        assert "feedback jar opened" in core.respond("beta feedback").display_text


def test_beta_report_button_path_does_not_crash() -> None:
    try:
        from PyQt6.QtWidgets import QApplication
        from fibi.ui.fibi_window import FibiWindow
    except Exception as exc:  # pragma: no cover - depends on optional desktop deps
        pytest.skip(f"PyQt6 unavailable: {exc}")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        app = QApplication.instance() or QApplication([])
        window = FibiWindow()
        window._open_beta_report()
        assert window.chat_input.text() == "/issue new "
        window.close()
        app.processEvents()


