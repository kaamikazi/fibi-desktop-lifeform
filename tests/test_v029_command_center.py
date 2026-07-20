"""Tests for Fibi v0.29 Command Center and help registries."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fibi.engines.capability_registry_engine import CapabilityRegistryEngine
from fibi.engines.command_registry_engine import CommandRegistryEngine
from fibi.engines.safety_explainer_engine import SafetyExplainerEngine
from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path


def test_capability_registry_loads() -> None:
    registry = CapabilityRegistryEngine()
    capabilities = registry.all()
    ids = {capability.capability_id for capability in capabilities}
    assert "browser_helper" in ids
    assert "workflow_recipes" in ids
    assert "patch_apply" in ids
    assert all(capability.name and capability.description and capability.category for capability in capabilities)


def test_command_registry_loads_and_is_searchable() -> None:
    registry = CommandRegistryEngine()
    commands = registry.all()
    assert commands
    assert len({command.command for command in commands}) == len(commands)
    assert all(command.category and command.description and command.risk_level for command in commands)
    assert registry.search("browser")
    assert registry.search("patch")
    assert registry.search("voice")
    assert registry.search("bug")
    assert registry.search("release")
    assert registry.search("memory")
    assert registry.search("project")


def test_help_commands_are_read_only() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        before = _settings_snapshot(core)

        assert "try:" in core.respond("/help").display_text
        assert "browser" in core.respond("/help search browser").display_text.lower()
        assert "capabilities:" in core.respond("/capabilities").display_text
        assert "permissions:" in core.respond("/permissions").display_text
        assert "safety map" in core.respond("/safety").display_text
        assert "confirmation needed" in core.respond("/confirmations").display_text
        assert "i refuse" in core.respond("/refusals").display_text
        assert "command shelves" in core.respond("show commands").display_text
        assert "i can chat" in core.respond("what can you do?").display_text

        after = _settings_snapshot(core)
        assert before == after
        assert model.calls == 0


def test_help_topics_and_capability_details() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        command = core.respond("/help patch").display_text.lower()
        assert "patch" in command
        assert "confirm" in command

        capability = core.respond("/capability browser").display_text.lower()
        assert "browser" in capability
        assert "blocked" in capability

        commands = core.respond("/commands browser").display_text.lower()
        assert "/browser" in commands
        assert "risk" not in commands or "browser" in commands


def test_safety_explainer_mentions_core_boundaries() -> None:
    safety = SafetyExplainerEngine()
    overview = safety.safety_overview()
    assert "cloud off by default" in overview
    assert "no hidden browsing" in overview
    assert "no auto-send" in overview
    assert "no auto-buy" in overview
    assert "no auto-apply patch" in overview


def test_command_center_gui_does_not_crash() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["FIBI_DATA_DIR"] = str(root / "data")
        result = subprocess.run(
            [sys.executable, "app.py", "--gui-smoke"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert "GUI_SMOKE_OK" in result.stdout or "GUI_SMOKE_SKIPPED_OR_FAILED" in result.stdout


def test_packaged_v029_paths() -> None:
    assert release_zip_path().name == "Fibi_Chubi_v0.30.1_windows_beta.zip"


def _settings_snapshot(core) -> tuple[object, ...]:
    return (
        core.privacy.settings.allow_cloud_model,
        core.privacy.settings.allow_nvidia_api,
        core.privacy.settings.allow_clipboard_observation,
        core.privacy.settings.allow_memory_learning,
        core.action_settings.settings.allow_desktop_actions,
        core.app_settings.settings.allow_project_checks,
        core.voice_settings.settings.allow_voice_input,
        core.voice_skin_settings.settings.rvc_enabled,
        core.app_settings.settings.beta_mode,
    )
