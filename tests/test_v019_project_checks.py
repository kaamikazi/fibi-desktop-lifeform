"""Unit coverage for Fibi v0.19 project check engines."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from fibi.engines.project_check_preset_engine import ProjectCheckPresetEngine
from fibi.engines.project_check_runner import ProjectCheckRunner
from fibi.engines.project_check_safety_engine import ProjectCheckSafetyEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import CheckCommandPreset, ProjectCheckRequest
from tests.smoke_v019_project_checks import wire_check_test_paths
from tests.smoke_v012_actions import make_core


def test_safe_presets_and_dangerous_scripts_are_filtered() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        (project / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (project / "package.json").write_text(
            '{"scripts":{"lint":"eslint .","test":"vitest","install":"npm install x","deploy":"npm publish","bad":"rm -rf ."}}',
            encoding="utf-8",
        )
        workspace_engine = ProjectWorkspaceEngine(root / "workspaces.json")
        assert workspace_engine.add_workspace(project).ok
        workspace = workspace_engine.current()
        assert workspace is not None

        presets = ProjectCheckPresetEngine().presets_for(workspace)
        keys = {preset.command_key for preset in presets}
        assert "python-compileall" in keys
        assert "npm-lint" in keys
        assert "npm-test" in keys
        assert "npm-deploy" not in keys
        assert "npm-install" not in keys
        assert "npm-bad" not in keys


def test_safety_blocks_unknown_outside_and_mutating_commands() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        outside = root / "outside"
        project.mkdir()
        outside.mkdir()
        workspace_engine = ProjectWorkspaceEngine(root / "workspaces.json")
        assert workspace_engine.add_workspace(project).ok
        workspace = workspace_engine.current()
        assert workspace is not None
        safety = ProjectCheckSafetyEngine()

        unknown = safety.assess(
            ProjectCheckRequest("x", workspace.project_id, "missing", ["python", "--version"], str(project)),
            workspace,
            None,
        )
        assert not unknown.allowed

        preset = CheckCommandPreset("python-version", "python --version", [sys.executable, "--version"])
        outside_result = safety.assess(
            ProjectCheckRequest("x", workspace.project_id, "python-version", [sys.executable, "--version"], str(outside)),
            workspace,
            preset,
        )
        assert not outside_result.allowed

        mutating = safety.assess(
            ProjectCheckRequest("x", workspace.project_id, "evil", ["git", "status"], str(project)),
            workspace,
            CheckCommandPreset("evil", "git status", ["git", "status"], "low"),
        )
        assert not mutating.allowed


def test_runner_saves_output_and_handles_timeout() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        runner = ProjectCheckRunner(root / "checks", sanitizer=SecretSanitizer())

        ok = runner.run(
            ProjectCheckRequest(
                "ok",
                "project",
                "python-print",
                [sys.executable, "-c", "print('hello check')"],
                str(project),
                timeout_seconds=5,
                allowed=True,
                requires_confirmation=False,
            )
        )
        assert ok.exit_code == 0
        assert "hello check" in ok.stdout_preview
        assert (Path(ok.output_path) / "stdout.txt").exists()

        slow = runner.run(
            ProjectCheckRequest(
                "slow",
                "project",
                "python-sleep",
                [sys.executable, "-c", "import time; time.sleep(2)"],
                str(project),
                timeout_seconds=1,
                allowed=True,
                requires_confirmation=False,
            )
        )
        assert slow.timed_out
        assert "timed out" in slow.summary


def test_core_confirmation_flow_and_model_boundary() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
        (project / "tests").mkdir()
        (project / "tests" / "test_dummy.py").write_text("def test_dummy():\n    assert True\n", encoding="utf-8")

        core, model, _ = make_core(root / "core", [], [])
        wire_check_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        reply = core.respond("run tests")
        assert "check creature ready" in reply.display_text
        assert core.check_confirmations.pending() is not None
        assert model.calls == 0
        core.respond("/check cancel")

        assert "check creature ready" in core.respond("compile project").display_text
        confirmed = core.respond("/check confirm")
        assert "check survived" in confirmed.display_text
        assert core._last_check_result is not None

        normal_question = core.respond("what is Python?")
        assert "check creature ready" not in normal_question.display_text


