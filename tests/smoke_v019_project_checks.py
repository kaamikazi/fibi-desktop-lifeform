"""Smoke tests for Fibi v0.19 safe project check runner."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.project_check_confirmation_engine import ProjectCheckConfirmationEngine
from fibi.engines.project_check_history_engine import ProjectCheckHistoryEngine
from fibi.engines.project_check_preset_engine import ProjectCheckPresetEngine
from fibi.engines.project_check_runner import ProjectCheckRunner
from fibi.engines.project_check_safety_engine import ProjectCheckSafetyEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import CheckCommandPreset, ProjectCheckRequest
from tests.smoke_v012_actions import make_core


def wire_check_test_paths(core, root: Path) -> None:
    core.project_workspace = ProjectWorkspaceEngine(
        root / "project_workspaces.json",
        context=core.context_engine,
        sanitizer=core.secret_sanitizer,
    )
    core.check_presets = ProjectCheckPresetEngine()
    core.check_safety = ProjectCheckSafetyEngine()
    core.check_runner = ProjectCheckRunner(root / "project_checks", sanitizer=core.secret_sanitizer)
    core.check_confirmations = ProjectCheckConfirmationEngine(root / "pending_project_check.json")
    core.check_history = ProjectCheckHistoryEngine(root / "project_check_history.jsonl")
    core._last_check_result = None


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "demo_project"
        project.mkdir()
        (project / "app.py").write_text("print('check me')\n", encoding="utf-8")
        (project / "package.json").write_text(
            '{"scripts":{"lint":"echo lint ok","deploy":"npm publish","bad":"rm -rf ."}}',
            encoding="utf-8",
        )

        core, model, _ = make_core(root / "core", [], [])
        wire_check_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok
        workspace = core.project_workspace.current()
        assert workspace is not None

        presets = core.check_presets.presets_for(workspace)
        keys = {preset.command_key for preset in presets}
        assert "python-compileall" in keys
        assert "npm-lint" in keys
        assert "npm-deploy" not in keys
        assert "npm-bad" not in keys

        safety = core.check_safety.assess(
            ProjectCheckRequest("bad", workspace.project_id, "evil", ["git", "status"], str(project)),
            workspace,
            CheckCommandPreset("evil", "git status", ["git", "status"], "blocked"),
        )
        assert not safety.allowed
        assert "manual" in safety.error or safety.risk_level == "blocked"

        listed = core.respond("/check presets")
        assert "python-compileall" in listed.display_text
        assert model.calls == 0

        pending = core.respond("/check run python-compileall")
        assert "check creature ready" in pending.display_text
        assert "run check confirm" in pending.display_text
        assert core.check_confirmations.pending() is not None
        assert not any((root / "project_checks").iterdir())

        canceled = core.respond("/check cancel")
        assert "canceled" in canceled.display_text
        assert core.check_confirmations.pending() is None

        natural = core.respond("compile project")
        assert "check creature ready" in natural.display_text
        assert core.check_confirmations.pending() is not None
        assert model.calls == 0

        confirmed = core.respond("run check confirm")
        assert "check survived" in confirmed.display_text
        assert core.check_confirmations.pending() is None
        result = core._last_check_result
        assert result is not None
        assert result.command_key == "python-compileall"
        assert result.cwd == str(project)
        assert Path(result.output_path).exists()
        assert (Path(result.output_path) / "stdout.txt").exists()
        assert core.memory_router.rag_memory.service.repository.get_by_source_id(f"check:{result.check_id}") is not None

        last = core.respond("/check last")
        assert "python-compileall" in last.display_text
        output = core.respond("/check output last")
        assert output.display_text
        history = core.respond("/check history")
        assert "check footprints" in history.display_text

        unknown = core.respond("/check run npm install left-pad")
        assert "unknown" in unknown.display_text.lower() or "sharp" in unknown.display_text.lower()
        assert core.check_confirmations.pending() is None

        complex_reply = core.respond("what is Python?")
        assert "check creature ready" not in complex_reply.display_text
        assert core.check_confirmations.pending() is None

        timeout_runner = ProjectCheckRunner(root / "timeout_checks", sanitizer=core.secret_sanitizer)
        timeout_result = timeout_runner.run(
            ProjectCheckRequest(
                "slow",
                workspace.project_id,
                "python-sleep",
                [sys.executable, "-c", "import time; time.sleep(2)"],
                str(project),
                timeout_seconds=1,
                allowed=True,
                requires_confirmation=False,
            )
        )
        assert timeout_result.timed_out
        assert "timed out" in timeout_result.summary

    print("Fibi v0.19 project check smoke tests passed.")


if __name__ == "__main__":
    run()


