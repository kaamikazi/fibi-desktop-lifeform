"""Compact pet mode and safe manual desktop action regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.types import ActionIntent
from tests.smoke_v012_actions import make_core


class FixedDetector:
    def __init__(self, intent: ActionIntent) -> None:
        self.intent = intent

    def detect(self, _message: str, direct_user_initiated: bool = True) -> ActionIntent | None:
        return self.intent if direct_user_initiated else None


def _mocked_core(tmp_path: Path):
    opened: list[str] = []
    launched: list[str] = []
    copied: list[str] = []
    typed: list[str] = []
    screenshots: list[Path] = []
    commands: list[tuple[tuple[str, ...], Path]] = []
    projects: list[tuple[str, str]] = []
    core, model, app_index = make_core(tmp_path / "core", opened, launched)
    engine = DesktopActionEngine(
        app_index,
        browser_open=lambda url: opened.append(url) or True,
        app_launcher=lambda path: launched.append(path),
        clipboard_writer=copied.append,
        keyboard_writer=typed.append,
        screenshot_taker=screenshots.append,
        command_runner=lambda args, cwd: commands.append((args, cwd)) or (0, "clean", ""),
        project_launcher=lambda executable, project: projects.append((executable, project)),
    )
    core.desktop_actions = engine
    return core, model, app_index, engine, {
        "opened": opened,
        "launched": launched,
        "copied": copied,
        "typed": typed,
        "screenshots": screenshots,
        "commands": commands,
        "projects": projects,
    }


@pytest.mark.parametrize(
    ("message", "action_type"),
    [
        ("Open Chrome", "open_app"),
        ("Open my Fibi project in VS Code", "open_project_vscode"),
        ("Open Downloads", "open_folder"),
        ("Create a folder named demo on Desktop", "create_folder"),
        ("Copy this text", "copy_text"),
        ("Open YouTube", "open_website"),
        ("Lower the volume", "volume_down"),
        ("run git status", "run_safe_command"),
    ],
)
def test_requested_action_examples_are_detected(message: str, action_type: str) -> None:
    intent = ActionIntentDetector().detect(message)
    assert intent is not None
    assert intent.action_type == action_type


def test_safe_app_and_website_opening_use_injected_callbacks(tmp_path: Path) -> None:
    core, model, _, _, calls = _mocked_core(tmp_path)
    app = core.respond("Open Chrome")
    website = core.respond("Open YouTube")
    assert calls["launched"]
    assert calls["opened"] == ["https://www.youtube.com"]
    assert model.calls == 0
    for response in (app, website):
        assert "Action requested:" in response.display_text
        assert "Permission: allowed" in response.display_text
        assert "Result: completed" in response.display_text


def test_open_folder_requires_allowlisted_path(tmp_path: Path) -> None:
    core, _, _, engine, calls = _mocked_core(tmp_path)
    allowed = tmp_path / "Downloads"
    allowed.mkdir()
    engine.register_allowed_path(allowed)
    core.action_intents = FixedDetector(ActionIntent("open_folder", target=str(allowed), raw_text="open downloads"))
    response = core.respond("open downloads")
    assert calls["launched"] == [str(allowed.resolve())]
    assert "Result: completed" in response.display_text

    blocked = tmp_path.parent / "outside"
    blocked.mkdir(exist_ok=True)
    core.action_intents = FixedDetector(ActionIntent("open_folder", target=str(blocked), raw_text="open outside"))
    response = core.respond("open outside")
    assert "Result: failed" in response.display_text
    assert "allowlist" in response.display_text


def test_registered_project_opens_in_indexed_vscode(tmp_path: Path) -> None:
    core, _, app_index, _, calls = _mocked_core(tmp_path)
    project = tmp_path / "Fibi"
    project.mkdir()
    assert core.project_workspace.add_workspace(project).ok
    code = tmp_path / "Code.exe"
    code.write_text("", encoding="utf-8")
    app_index.add_entry("Visual Studio Code", str(code), "test")
    response = core.respond("Open my Fibi project in VS Code")
    assert calls["projects"] == [(str(code), str(project.resolve()))]
    assert "Result: completed" in response.display_text


def test_copy_and_confirmed_typing_are_mocked_and_secret_safe(tmp_path: Path) -> None:
    core, _, _, _, calls = _mocked_core(tmp_path)
    copied = core.respond("Copy this text: hello Fibi")
    assert calls["copied"] == ["hello Fibi"]
    assert "Result: completed" in copied.display_text

    core.action_intents = FixedDetector(ActionIntent("type_text", target="approved hello", raw_text="type approved hello"))
    pending = core.respond("type approved hello")
    assert "Permission: confirmation required" in pending.display_text
    assert "confirm type text" in pending.display_text
    assert not calls["typed"]
    confirmed = core.respond("confirm type text")
    assert calls["typed"] == ["approved hello"]
    assert "Permission: confirmed and allowed" in confirmed.display_text

    core.action_intents = ActionIntentDetector()
    secret = core.respond("type text API_KEY=do-not-expose")
    assert "sensitive" in secret.display_text.lower() or "secret" in secret.display_text.lower()
    assert "do-not-expose" not in secret.display_text
    assert calls["typed"] == ["approved hello"]


def test_folder_screenshot_and_safe_command_confirmation_use_mocks(tmp_path: Path) -> None:
    core, _, _, engine, calls = _mocked_core(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    engine.register_allowed_path(desktop)

    target = desktop / "demo"
    core.action_intents = FixedDetector(ActionIntent("create_folder", target=str(target), raw_text="create folder"))
    pending = core.respond("create folder")
    assert "confirm create folder" in pending.display_text
    completed = core.respond("confirm create folder")
    assert target.is_dir()
    assert "Result: completed" in completed.display_text

    core.action_settings.update(allow_screenshot=True)
    core.action_intents = FixedDetector(ActionIntent("screenshot", raw_text="take screenshot"))
    assert "confirm screenshot" in core.respond("take screenshot").display_text
    screenshot = core.respond("confirm screenshot")
    assert len(calls["screenshots"]) == 1
    assert "Result: completed" in screenshot.display_text

    core.action_intents = FixedDetector(ActionIntent("run_safe_command", target="git status", raw_text="run git status"))
    assert "confirm safe command" in core.respond("run git status").display_text
    command = core.respond("confirm safe command")
    assert calls["commands"] and calls["commands"][0][0] == ("git", "status", "--short")
    assert "Result: completed" in command.display_text


def test_destructive_and_unapproved_commands_stay_blocked(tmp_path: Path) -> None:
    core, model, _, _, calls = _mocked_core(tmp_path)
    delete = core.respond("delete this file")
    shell = core.respond("run rm -rf everything")
    install = core.respond("install this software package")
    for response in (delete, shell, install):
        assert "Permission: blocked" in response.display_text
        assert "Result: failed" in response.display_text
    assert not calls["commands"]
    assert not calls["typed"]
    assert not calls["screenshots"]
    assert model.calls == 0
