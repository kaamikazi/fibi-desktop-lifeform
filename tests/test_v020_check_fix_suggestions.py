"""Unit coverage for Fibi v0.20 check failure fix suggestions."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fibi.engines.check_failure_analyzer import CheckFailureAnalyzer
from fibi.engines.check_fix_planner import CheckFixPlanner
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.related_file_resolver import RelatedFileResolver
from fibi.engines.types import CheckFailureAnalysis, ErrorLocation, ProjectCheckResult
from tests.smoke_v012_actions import make_core
from tests.smoke_v020_check_fix_suggestions import wire_fix_test_paths


def _result(output: str, check_id: str = "check") -> ProjectCheckResult:
    return ProjectCheckResult(
        check_id,
        "project",
        "python-compileall",
        [],
        "",
        60,
        exit_code=1,
        stdout_preview=output,
        stderr_preview="",
        summary="failed",
    )


def test_python_syntax_error_analysis_extracts_file_and_line() -> None:
    output = """Compiling '.\\bad.py'...
***   File ".\\bad.py", line 1
    print('oops'
          ^
SyntaxError: '(' was never closed
"""
    analysis = CheckFailureAnalyzer().analyze(_result(output))
    assert analysis.error_type == "python_syntax_error"
    assert analysis.suspected_file.endswith("bad.py")
    assert analysis.suspected_line == 1
    assert analysis.confidence >= 0.8


def test_typescript_and_eslint_analysis() -> None:
    ts = CheckFailureAnalyzer().analyze(_result("src/app.tsx(12,5): error TS2322: Type 'number' is not assignable"))
    assert ts.error_type == "typescript_error"
    assert ts.suspected_file == "src/app.tsx"
    assert ts.suspected_line == 12

    eslint = CheckFailureAnalyzer().analyze(_result("src/app.tsx\n  7:3  error  no-unused-vars"))
    assert eslint.error_type == "eslint_error"
    assert eslint.suspected_file == "src/app.tsx"
    assert eslint.suspected_line == 7


def test_related_file_resolver_refuses_outside_and_secret_paths() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        (project / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (project / ".env").write_text("TOKEN=<dummy-secret-value>", encoding="utf-8")
        workspace = ProjectWorkspaceEngine(root / "workspaces.json")
        assert workspace.add_workspace(project).ok
        resolver = RelatedFileResolver(workspace)

        outside = CheckFailureAnalysis("x", workspace.current().project_id, "python_syntax_error", "bad", [ErrorLocation("../outside.py", 1)])
        outside_candidates = resolver.resolve(outside)
        assert outside_candidates and not outside_candidates[0].safe_to_read
        assert outside_candidates[0].refused_reason == "outside project"

        secret = CheckFailureAnalysis("x", workspace.current().project_id, "unknown_failure", "secret", [ErrorLocation(".env", 1)])
        secret_candidates = resolver.resolve(secret)
        assert secret_candidates and not secret_candidates[0].safe_to_read
        assert "secret" in secret_candidates[0].refused_reason

        safe = CheckFailureAnalysis("x", workspace.current().project_id, "python_syntax_error", "bad", [ErrorLocation("main.py", 1)])
        safe_candidates = resolver.resolve(safe)
        assert safe_candidates[0].safe_to_read
        assert "1: print" in safe_candidates[0].snippet


def test_fix_planner_creates_low_risk_syntax_patch_and_refuses_auth() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        bad = project / "bad.py"
        bad.write_text("print('oops'\n", encoding="utf-8")
        workspace = ProjectWorkspaceEngine(root / "workspaces.json")
        assert workspace.add_workspace(project).ok
        resolver = RelatedFileResolver(workspace)
        analysis = CheckFailureAnalysis(
            "x",
            workspace.current().project_id,
            "python_syntax_error",
            "SyntaxError: '(' was never closed",
            [ErrorLocation("bad.py", 1)],
            "bad.py",
            1,
            0.9,
        )
        plan = CheckFixPlanner().plan(analysis, resolver.resolve(analysis))
        assert plan.edit_suggestion is not None
        assert plan.risk_level == "low"
        assert "bad.py" in plan.related_files

        auth = project / "auth.py"
        auth.write_text("ALLOW = False\n", encoding="utf-8")
        workspace.scan_current()
        auth_analysis = CheckFailureAnalysis(
            "y",
            workspace.current().project_id,
            "python_syntax_error",
            "SyntaxError: '(' was never closed",
            [ErrorLocation("auth.py", 1)],
            "auth.py",
            1,
            0.9,
        )
        auth_plan = CheckFixPlanner().plan(auth_analysis, resolver.resolve(auth_analysis))
        assert auth_plan.edit_suggestion is None
        assert auth_plan.risk_level == "high"
        assert "manual" in auth_plan.refused_reason


def test_core_fix_suggestion_never_auto_applies_or_runs_model_command() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        bad = project / "bad.py"
        bad.write_text("print('oops'\n", encoding="utf-8")
        core, model, _ = make_core(root / "core", [], [])
        wire_fix_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        core.respond("compile project")
        core.respond("run check confirm")
        reply = core.respond("suggest a fix")
        assert "apply patch confirm" in reply.display_text
        assert bad.read_text(encoding="utf-8") == "print('oops'\n"
        assert core.check_confirmations.pending() is None
        assert core.patch_confirmations.pending() is not None
        assert model.calls == 0


