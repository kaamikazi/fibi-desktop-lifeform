"""Smoke tests for Fibi v0.20 check-output fix suggestions."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.check_failure_analyzer import CheckFailureAnalyzer
from fibi.engines.check_fix_planner import CheckFixPlanner
from fibi.engines.related_file_resolver import RelatedFileResolver
from tests.smoke_v012_actions import make_core
from tests.smoke_v018_patch_apply import wire_patch_test_paths
from tests.smoke_v019_project_checks import wire_check_test_paths


def wire_fix_test_paths(core, root: Path) -> None:
    wire_check_test_paths(core, root)
    wire_patch_test_paths(core, root)
    core.check_failure_analyzer = CheckFailureAnalyzer()
    core.related_file_resolver = RelatedFileResolver(core.project_workspace)
    core.check_fix_planner = CheckFixPlanner()
    core._last_check_failure_analysis = None
    core._last_check_fix_plan = None
    core._pending_fix_suggestion = None


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "demo_project"
        project.mkdir()
        target = project / "bad.py"
        target.write_text("print('oops'\n", encoding="utf-8")
        (project / ".env").write_text("TOKEN=secret", encoding="utf-8")
        (project / "auth.py").write_text("ALLOW = False\n", encoding="utf-8")

        core, model, _ = make_core(root / "core", [], [])
        wire_fix_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        assert "check creature ready" in core.respond("compile project").display_text
        failed = core.respond("run check confirm")
        assert "check found crumbs" in failed.display_text
        assert core._last_check_result is not None
        assert core._last_check_result.exit_code != 0

        analysis = core.respond("/check analyze last")
        assert "python_syntax_error" in analysis.display_text
        assert "bad.py" in analysis.display_text

        suggestion = core.respond("/check suggest fix")
        assert "tiny fix ready" in suggestion.display_text
        assert "apply patch confirm" in suggestion.display_text
        assert core.patch_confirmations.pending() is not None
        assert target.read_text(encoding="utf-8") == "print('oops'\n"
        assert model.calls == 0

        plan = core._last_check_fix_plan
        assert plan is not None
        assert plan.suggested_patch_id
        assert core.memory_router.rag_memory.service.repository.get_by_source_id(f"check-fix:{plan.check_id}:{plan.suggested_patch_id}") is not None

        explained = core.respond("/fix explain")
        assert "tiny fix plan" in explained.display_text or "python_syntax_error" in explained.display_text

        applied = core.respond("apply patch confirm")
        assert "patch applied" in applied.display_text
        assert target.read_text(encoding="utf-8") == "print('oops')\n"
        assert core.check_confirmations.pending() is None

        core._last_check_result = None
        no_fail = core.respond("/fix last check")
        assert "no failed check" in no_fail.display_text

        core._pending_fix_suggestion = object()
        cleared = core.respond("/fix clear")
        assert "cleared" in cleared.display_text
        assert core._pending_fix_suggestion is None

    print("Fibi v0.20 check fix suggestion smoke tests passed.")


if __name__ == "__main__":
    run()


