"""Focused, side-effect-free tests for the native assistant contract."""

from __future__ import annotations

from pathlib import Path

from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.permission_engine import PermissionEngine
from fibi.engines.project_scanner_engine import ProjectScannerEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import ActionIntent, ActionResultStatus, ActionSettings, PrivacySettings, ProjectWorkspaceSettings
from fibi.engines.types import DesktopActionResult
from fibi.engines.work_planner_engine import WorkPlannerEngine
from fibi.engines.work_session_engine import WorkSessionEngine


def _exe(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    return path


def test_native_intents_cover_bounded_productivity_actions() -> None:
    detector = ActionIntentDetector()
    assert detector.detect("Open file README.md").action_type == "open_file"
    assert detector.detect("Open the Downloads folder").action_type == "open_folder"
    assert detector.detect("Search files for TODO").action_type == "search_files"
    assert detector.detect("Take a note: release checklist").action_type == "save_note"
    assert detector.detect("Start a work session to review tests").action_type == "start_work_session"
    assert detector.detect("Copy this text").target == ""


def test_app_resolution_prefers_start_menu_over_known_location_and_path(tmp_path: Path) -> None:
    start_menu = _exe(tmp_path / "start" / "Google Chrome.lnk")
    known = _exe(tmp_path / "known" / "Google" / "Chrome" / "Application" / "chrome.exe")
    path_copy = _exe(tmp_path / "path" / "chrome.exe")
    index = AppIndexEngine(
        tmp_path / "apps.json",
        which_lookup=lambda _name: str(path_copy),
        environment={"ProgramFiles": str(tmp_path / "known")},
        start_menu_roots=[start_menu.parent],
    )

    resolved = index.resolve_app("Chrome")

    assert resolved is not None
    assert resolved.source == "start-menu"
    assert Path(resolved.path) == start_menu.resolve()
    assert known.exists()


def test_vscode_project_resolution_skips_unresolved_shortcut_for_executable(tmp_path: Path) -> None:
    shortcut = _exe(tmp_path / "start" / "Visual Studio Code.lnk")
    executable = _exe(tmp_path / "known" / "Microsoft VS Code" / "Code.exe")
    index = AppIndexEngine(
        tmp_path / "apps.json",
        environment={"ProgramFiles": str(tmp_path / "known")},
        start_menu_roots=[shortcut.parent],
    )

    resolved = index.resolve_executable_app("VS Code")

    assert resolved is not None
    assert resolved.source == "known-location"
    assert Path(resolved.path) == executable.resolve()


def test_native_executor_uses_injected_effects_and_returns_normalized_result(tmp_path: Path) -> None:
    launched: list[str] = []
    copied: list[str] = []
    notes: list[str] = []
    sessions: list[str] = []
    root = tmp_path / "project"
    root.mkdir()
    file_path = root / "README.md"
    file_path.write_text("TODO: test", encoding="utf-8")

    engine = DesktopActionEngine(
        app_index=AppIndexEngine(tmp_path / "apps.json"),
        app_launcher=launched.append,
        clipboard_writer=copied.append,
        file_searcher=lambda query: ["README.md"] if query == "TODO" else [],
        note_writer=lambda text: notes.append(text) or True,
        work_session_starter=lambda goal: sessions.append(goal) or "session started.",
    )
    assert engine.register_allowed_path(root)

    opened = engine.execute(ActionIntent("open_file", target=str(file_path)))
    searched = engine.execute(ActionIntent("search_files", query="TODO"))
    noted = engine.execute(ActionIntent("save_note", target="release checklist"))
    started = engine.execute(ActionIntent("start_work_session", target="review tests"))
    copied_result = engine.execute(ActionIntent("copy_text", target="hello"))

    assert opened.ok and opened.status == ActionResultStatus.COMPLETED.value
    assert searched.ok and "README.md" in searched.message
    assert noted.ok and notes == ["release checklist"]
    assert started.ok and sessions == ["review tests"]
    assert copied_result.ok and copied == ["hello"]
    assert launched == [str(file_path.resolve())]


def test_native_executor_rejects_outside_paths_and_secret_like_notes(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    engine = DesktopActionEngine(app_index=AppIndexEngine(tmp_path / "apps.json"))
    assert engine.register_allowed_path(root)

    outside_result = engine.execute(ActionIntent("open_file", target=str(outside)))
    secret_note = engine.execute(ActionIntent("save_note", target="API_KEY=do-not-save"))

    assert not outside_result.ok
    assert outside_result.error_code == "unsafe_path"
    assert outside_result.error_category == "not_allowed"
    assert outside_result.status == ActionResultStatus.FAILED.value
    assert not secret_note.ok
    assert secret_note.error_code == "unsafe_note"


def test_arbitrary_application_path_is_not_accepted_from_chat(tmp_path: Path) -> None:
    launches: list[str] = []
    index = AppIndexEngine(tmp_path / "apps.json", which_lookup=lambda _name: None, environment={}, start_menu_roots=[])
    result = DesktopActionEngine(index, app_launcher=launches.append).execute(
        ActionIntent("open_app", target=str(tmp_path / "unsafe.exe"))
    )

    assert not result.ok
    assert launches == []
    assert result.error_code == "app_not_found"
    assert str(tmp_path) not in result.message
    assert str(tmp_path) not in result.target


def test_open_file_cannot_bypass_the_application_allowlist(tmp_path: Path) -> None:
    launches: list[str] = []
    project = tmp_path / "project"
    project.mkdir()
    engine = DesktopActionEngine(
        AppIndexEngine(tmp_path / "apps.json"), app_launcher=launches.append,
    )
    assert engine.register_allowed_path(project)
    for suffix in (".exe", ".cmd", ".ps1", ".py", ".lnk", ".url"):
        file_path = project / ("launch" + suffix)
        file_path.write_text("synthetic test", encoding="utf-8")
        result = engine.execute(ActionIntent("open_file", target=str(file_path)))
        assert not result.ok
        assert result.error_code == "executable_file_blocked"
    assert launches == []


def test_manual_app_registration_precedes_alias_discovery(tmp_path: Path) -> None:
    manual = _exe(tmp_path / "manual" / "chrome.exe")
    guessed = _exe(tmp_path / "guessed" / "chrome.exe")
    index = AppIndexEngine(
        tmp_path / "apps.json",
        which_lookup=lambda _name: str(guessed),
        environment={},
        start_menu_roots=[],
    )
    assert index.register_manual("Chrome", manual)[0]

    resolved = index.resolve_app("Google Chrome")

    assert resolved is not None
    assert Path(resolved.path) == manual.resolve()
    assert resolved.source == "manual"


def test_short_alias_does_not_match_an_unrelated_start_menu_app(tmp_path: Path) -> None:
    _exe(tmp_path / "start" / "CodeBlocks.lnk")
    code = _exe(tmp_path / "path" / "Code.exe")
    index = AppIndexEngine(
        tmp_path / "apps.json",
        which_lookup=lambda name: str(code) if name.casefold() == "code" else None,
        environment={},
        start_menu_roots=[tmp_path / "start"],
    )
    resolved = index.resolve_app("VS Code")
    assert resolved is not None
    assert resolved.source == "path"
    assert Path(resolved.path) == code.resolve()


def test_native_executor_handles_projects_urls_and_recent_notes(tmp_path: Path) -> None:
    project = tmp_path / "Atlas"
    project.mkdir()
    (project / "README.md").write_text("TODO", encoding="utf-8")
    workspace = ProjectWorkspaceEngine(tmp_path / "workspaces.json")
    assert workspace.add_workspace(project, aliases=["frontend"]).ok
    assert workspace.note("review the navbar")

    code = _exe(tmp_path / "Code.exe")
    launched: list[str] = []
    urls: list[str] = []
    vscode: list[tuple[str, str]] = []
    engine = DesktopActionEngine(
        app_index=AppIndexEngine(tmp_path / "apps.json"),
        app_launcher=launched.append,
        browser_open=lambda url: urls.append(url) or True,
        project_launcher=lambda executable, target: vscode.append((executable, target)),
        note_lister=lambda: workspace.recent_notes(limit=5),
    )
    engine.app_index.add_entry("VS Code", str(code), "manual")
    assert engine.register_allowed_path(project)

    opened_project = engine.execute(ActionIntent("open_project", target=str(project), query="Atlas"))
    opened_vscode = engine.execute(ActionIntent("open_project_vscode", target=str(project), query="Atlas"))
    opened_url = engine.execute(ActionIntent("open_website", target="https://github.com"))
    listed = engine.execute(ActionIntent("list_notes"))
    redacted = DesktopActionEngine(
        app_index=AppIndexEngine(tmp_path / "redaction-apps.json"),
        note_lister=lambda: [r"Atlas: C:\Users\tester\private\release.txt"],
    ).execute(ActionIntent("list_notes"))

    assert opened_project.ok and "Atlas" in opened_project.message
    assert opened_vscode.ok and vscode == [(str(code), str(project.resolve()))]
    assert opened_url.ok and urls == ["https://github.com"]
    assert listed.ok and "navbar" in listed.message
    assert redacted.ok and "C:\\Users\\tester" not in redacted.message
    assert all(str(project) not in result.target for result in (opened_project, opened_vscode, listed))
    assert launched == [str(project.resolve())]


def test_url_validation_reports_browser_false_and_rejects_dangerous_schemes(tmp_path: Path) -> None:
    engine = DesktopActionEngine(
        app_index=AppIndexEngine(tmp_path / "apps.json"),
        browser_open=lambda _url: False,
    )

    browser_failed = engine.execute(ActionIntent("open_website", target="https://github.com"))
    dangerous = engine.execute(ActionIntent("open_website", target="javascript:alert(1)"))

    assert not browser_failed.ok and browser_failed.error_code == "browser_open_failed"
    assert not dangerous.ok and dangerous.error_code == "unsafe_url"


def test_project_scanning_is_bounded_and_cancellable(tmp_path: Path) -> None:
    root = tmp_path / "project"
    deep = root / "one" / "two" / "three" / "four"
    deep.mkdir(parents=True)
    (root / "README.md").write_text("root", encoding="utf-8")
    (deep / "deep.txt").write_text("too deep", encoding="utf-8")
    settings = ProjectWorkspaceSettings(max_scan_depth=2, max_scan_files=3)
    workspace = ProjectWorkspaceEngine(tmp_path / "workspaces.json", settings=settings)
    assert workspace.add_workspace(root).ok

    files = {entry.relative_path for entry in workspace.files()}
    assert "README.md" in files
    assert "one/two/three/four/deep.txt" not in files

    scanner = ProjectScannerEngine(max_depth=20, max_files=10)
    cancelled = scanner.scan(workspace.current(), cancel_check=lambda: True)
    assert not cancelled.ok and cancelled.error == "cancelled"
    timed_out = ProjectScannerEngine(max_seconds=0).scan(workspace.current())
    assert not timed_out.ok and timed_out.error == "timeout"


def test_reparse_project_and_app_paths_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    executable = _exe(root / "safe.exe")
    link = tmp_path / "project-link"
    try:
        link.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        return

    assert not DesktopActionEngine(app_index=AppIndexEngine(tmp_path / "apps.json")).register_allowed_path(link)
    assert not ProjectWorkspaceEngine(tmp_path / "workspaces.json").add_workspace(link).ok
    index = AppIndexEngine(tmp_path / "indexed.json", environment={}, start_menu_roots=[])
    assert not index.register_manual("Linked App", link / executable.name)[0]


def test_project_aliases_and_duplicate_sessions_are_deterministic(tmp_path: Path) -> None:
    project = tmp_path / "Atlas"
    project.mkdir()
    workspace = ProjectWorkspaceEngine(tmp_path / "workspaces.json")
    assert workspace.add_workspace(project, aliases=["web"]).ok
    assert workspace.find("WEB").name == "Atlas"

    planner = WorkPlannerEngine()
    plan = planner.plan("review this project", workspace.current())
    sessions = WorkSessionEngine(tmp_path / "sessions.json")
    first = sessions.create_session("atlas", "review this project", plan)
    second = sessions.create_session("atlas", "start another task", plan)

    assert first.session_id == second.session_id
    assert len(sessions.state.sessions) == 1
    assert sessions.cancel() is not None


def test_permission_and_result_contract_fail_closed_without_private_paths(tmp_path: Path) -> None:
    permission = PermissionEngine().check(
        ActionIntent("read_clipboard"),
        ActionSettings(),
        PrivacySettings(),
        True,
    )
    assert permission.blocked and not permission.allowed

    outside = tmp_path / "outside"
    outside.mkdir()
    engine = DesktopActionEngine(app_index=AppIndexEngine(tmp_path / "apps.json"))
    result = engine.execute(ActionIntent("open_folder", target=str(outside)))
    assert not result.ok
    assert result.status == ActionResultStatus.FAILED.value
    assert str(outside) not in result.message
    assert str(outside) not in result.target


def test_native_effect_modules_do_not_import_language_providers_or_shell_interpolation() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "fibi/engines/desktop_action_engine.py",
        "fibi/engines/app_index_engine.py",
        "fibi/engines/project_workspace_engine.py",
    ):
        source = (root / relative).read_text(encoding="utf-8").lower()
        assert "gemini" not in source and "ollama" not in source
        assert "shell=true" not in source


def test_compatibility_helpers_require_the_existing_permission_gateway() -> None:
    from fibi.control.apps import open_app
    from fibi.control.browser import search

    assert "permission-checked" in open_app("Chrome")
    assert "permission-checked" in search("Python")
    calls: list[ActionIntent] = []

    def denied_gateway(intent: ActionIntent) -> DesktopActionResult:
        calls.append(intent)
        return DesktopActionResult(False, "desktop actions disabled", intent.action_type).mark_permission("blocked")

    assert open_app("Chrome", execute_action=denied_gateway) == "desktop actions disabled"
    assert search("Python", execute_action=denied_gateway) == "desktop actions disabled"
    assert [intent.action_type for intent in calls] == ["open_app", "web_search"]
