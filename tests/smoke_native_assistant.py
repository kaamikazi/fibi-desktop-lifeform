"""No-side-effect native assistant smoke test.

Every OS effect is injected with an in-memory callback. This file is safe to
run on a developer machine or in CI without opening applications or URLs.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.permission_engine import PermissionEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import ActionIntent, ActionResultStatus, ActionSettings, PrivacySettings
from fibi.engines.work_planner_engine import WorkPlannerEngine
from fibi.engines.work_session_engine import WorkSessionEngine


def run() -> None:
    detector = ActionIntentDetector()
    assert detector.detect("what's the date").action_type == "tell_date"
    assert detector.detect("Open VS Code").action_type == "open_app"
    assert detector.detect("Search files for TODO").action_type == "search_files"
    assert detector.detect("Open the Atlas project folder").action_type == "open_project"
    assert detector.detect("Show my recent notes").action_type == "list_notes"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project = root / "project"
        project.mkdir()
        readme = project / "README.md"
        readme.write_text("TODO: verify native actions", encoding="utf-8")
        workspace = ProjectWorkspaceEngine(root / "workspaces.json")
        assert workspace.add_workspace(project, aliases=["Atlas"]).ok
        code = root / "Code.exe"
        code.write_bytes(b"MZ")
        launched: list[str] = []
        copied: list[str] = []
        opened_urls: list[str] = []
        project_launches: list[tuple[str, str]] = []
        session_engine = WorkSessionEngine(root / "sessions.json")
        plan = WorkPlannerEngine().plan("review this project", workspace.current())

        def start_session(goal: str) -> str:
            current = workspace.current()
            assert current is not None
            session_engine.create_session(current.project_id, goal, plan)
            return "session started."

        engine = DesktopActionEngine(
            app_index=AppIndexEngine(root / "apps.json"),
            app_launcher=launched.append,
            browser_open=lambda url: opened_urls.append(url) or True,
            clipboard_writer=copied.append,
            file_searcher=lambda query: ["README.md"] if query == "TODO" else [],
            note_writer=workspace.note,
            note_lister=lambda: workspace.recent_notes(limit=5),
            work_session_starter=start_session,
            project_launcher=lambda executable, target: project_launches.append((executable, target)),
        )
        assert engine.register_allowed_path(project)
        engine.app_index.add_entry("Visual Studio Code", str(code), "test")

        intents = (
            ActionIntent("open_file", target=str(readme)),
            ActionIntent("open_project", target=str(project), query="Atlas"),
            ActionIntent("open_project_vscode", target=str(project), query="Atlas"),
            ActionIntent("search_files", query="TODO"),
            ActionIntent("copy_text", target="approved text"),
            ActionIntent("open_website", target="https://github.com"),
            ActionIntent("save_note", target="check the release path"),
            ActionIntent("list_notes"),
            ActionIntent("start_work_session", target="review native actions"),
        )
        for intent in intents:
            permission = PermissionEngine().check(intent, ActionSettings(), PrivacySettings(), True)
            assert permission.allowed
            result = engine.execute(intent).mark_permission("allowed")
            assert result.ok, result.message
            assert result.status == ActionResultStatus.COMPLETED.value
            assert result.permission_state == "allowed"

        assert str(readme.resolve()) in launched
        assert str(project.resolve()) in launched
        assert copied == ["approved text"]
        assert opened_urls == ["https://github.com"]
        assert project_launches == [(str(code), str(project.resolve()))]
        assert session_engine.active() is not None
        session_engine.cancel()

        denied = PermissionEngine().check(ActionIntent("read_clipboard"), ActionSettings(), PrivacySettings(), True)
        assert denied.blocked and not denied.allowed

    print("Native assistant smoke passed without real desktop effects.")


if __name__ == "__main__":
    run()
