"""Concise response policy and safe Windows app discovery regressions."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.reply_style_engine import ReplyStyleEngine
from fibi.engines.types import ActionIntent
from fibi.ui.fibi_window import FibiSettingsDialog
from tests.smoke_v012_actions import make_core
from tests.test_v0305_manual_quality import _core_with_ollama


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "runtime"))


def _exe(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    return path


def test_concise_policy_limits_sentences_and_words() -> None:
    policy = ReplyStyleEngine()
    source = " ".join(f"Sentence {index} has several useful words." for index in range(1, 12))
    concise = policy.apply(source, "concise", "what is this?")
    assert len(concise.split()) <= 20
    assert concise.count(".") <= 2
    assert "2 short sentences" in policy.instruction("concise", "what is this?")


@pytest.mark.parametrize("detail_prompt", ["Explain this in detail", "Explain deeply", "Give details", "Full explanation"])
def test_detailed_request_and_setting_are_not_concise_truncated(detail_prompt: str) -> None:
    policy = ReplyStyleEngine()
    source = " ".join(f"Useful sentence {index}." for index in range(12))
    assert policy.apply(source, "concise", detail_prompt) == source
    assert policy.apply(source, "detailed", "Explain this") == source


def test_reply_style_defaults_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = AppSettingsEngine(path)
    assert settings.settings.reply_style == "concise"
    settings.update(reply_style="normal")
    assert AppSettingsEngine(path).settings.reply_style == "normal"
    settings.update(reply_style="invalid")
    assert settings.settings.reply_style == "concise"


def test_model_reply_is_bounded_by_selected_concise_policy(tmp_path: Path) -> None:
    long_reply = " ".join(f"This is useful sentence {index}." for index in range(1, 10))
    core, _ollama = _core_with_ollama(tmp_path, [long_reply])
    core.app_settings.update(reply_style="concise")
    response = core.respond("what is dependency injection?")
    assert len(response.display_text.split()) <= 20
    assert response.display_text.count(".") <= 2


def test_cloud_prompt_receives_concise_instruction() -> None:
    instruction = ReplyStyleEngine().instruction("concise", "what is Python?")
    prompt = CloudContextSanitizer().build_prompt(
        "what is Python?",
        "idle",
        response_instruction=instruction,
    )
    assert "Response length:" in prompt
    assert "45 words" in prompt


def test_saved_registry_precedes_path_lookup(tmp_path: Path) -> None:
    saved = _exe(tmp_path / "saved" / "Code.exe")
    path_copy = _exe(tmp_path / "path" / "Code.exe")
    index = AppIndexEngine(tmp_path / "apps.json", which_lookup=lambda _name: str(path_copy))
    index.add_entry("Visual Studio Code", str(saved), "manual")
    resolved = index.resolve_app("VS Code")
    assert resolved is not None
    assert Path(resolved.path) == saved.resolve()


@pytest.mark.parametrize("alias", ["VS Code", "vscode", "code", "Code.exe"])
def test_vscode_alias_resolution_uses_path(alias: str, tmp_path: Path) -> None:
    code = _exe(tmp_path / "Code.exe")
    index = AppIndexEngine(tmp_path / f"{alias.replace(' ', '_')}.json", which_lookup=lambda name: str(code) if name.lower() in {"code", "code.exe"} else None, environment={}, start_menu_roots=[])
    resolved = index.resolve_app(alias)
    assert resolved is not None
    assert resolved.display_name == "VS Code"
    assert Path(resolved.path) == code.resolve()


@pytest.mark.parametrize("alias", ["Teams", "ms-teams", "msteams"])
def test_teams_alias_resolution_uses_known_location(alias: str, tmp_path: Path) -> None:
    local = tmp_path / "LocalAppData"
    teams = _exe(local / "Microsoft" / "WindowsApps" / "msteams.exe")
    index = AppIndexEngine(
        tmp_path / f"teams-{alias}.json",
        which_lookup=lambda _name: None,
        environment={"LOCALAPPDATA": str(local)},
        start_menu_roots=[],
    )
    resolved = index.resolve_app(alias)
    assert resolved is not None
    assert Path(resolved.path) == teams.resolve()


def test_path_and_known_location_resolution(tmp_path: Path) -> None:
    chrome = _exe(tmp_path / "path" / "chrome.exe")
    path_index = AppIndexEngine(tmp_path / "path.json", which_lookup=lambda name: str(chrome) if name == "chrome" else None, environment={}, start_menu_roots=[])
    assert Path(path_index.resolve_app("Chrome").path) == chrome.resolve()  # type: ignore[union-attr]

    local = tmp_path / "LocalAppData"
    code = _exe(local / "Programs" / "Microsoft VS Code" / "Code.exe")
    location_index = AppIndexEngine(
        tmp_path / "known.json",
        which_lookup=lambda _name: None,
        environment={"LOCALAPPDATA": str(local)},
        start_menu_roots=[],
    )
    assert Path(location_index.resolve_app("VS Code").path) == code.resolve()  # type: ignore[union-attr]


def test_start_menu_resolution(tmp_path: Path) -> None:
    start_menu = tmp_path / "Start Menu"
    shortcut = start_menu / "Microsoft Edge.lnk"
    shortcut.parent.mkdir(parents=True)
    shortcut.write_bytes(b"shortcut")
    index = AppIndexEngine(
        tmp_path / "start-menu.json",
        which_lookup=lambda _name: None,
        environment={},
        start_menu_roots=[start_menu],
    )
    resolved = index.resolve_app("Edge")
    assert resolved is not None
    assert resolved.source == "start-menu"
    assert Path(resolved.path) == shortcut.resolve()


def test_manual_registry_rejects_scripts_and_arguments(tmp_path: Path) -> None:
    index = AppIndexEngine(tmp_path / "manual.json", which_lookup=lambda _name: None)
    script = tmp_path / "launch.cmd"
    script.write_text("echo no", encoding="utf-8")
    assert not index.register_manual("Script", script)[0]
    executable = _exe(tmp_path / "Safe.exe")
    assert not index.register_manual("Safe --dangerous", executable)[0]
    assert index.manual_entries() == []


def test_missing_and_arbitrary_executable_are_blocked_without_launch(tmp_path: Path) -> None:
    launches: list[str] = []
    index = AppIndexEngine(tmp_path / "apps.json", which_lookup=lambda _name: None, environment={}, start_menu_roots=[])
    actions = DesktopActionEngine(index, app_launcher=launches.append)
    missing = actions.execute(ActionIntent("open_app", target="Figma"))
    arbitrary = actions.execute(ActionIntent("open_app", target=r"C:\Temp\unsafe.exe"))
    assert not missing.ok
    assert "Register its path in Settings > Actions" in missing.message
    assert not arbitrary.ok
    assert launches == []


def test_discovered_app_is_saved_only_after_mocked_launch(tmp_path: Path) -> None:
    launches: list[str] = []
    chrome = _exe(tmp_path / "chrome.exe")
    index = AppIndexEngine(tmp_path / "apps.json", which_lookup=lambda name: str(chrome) if name == "chrome" else None, environment={}, start_menu_roots=[])
    actions = DesktopActionEngine(index, app_launcher=launches.append)
    result = actions.execute(ActionIntent("open_app", target="Chrome"))
    assert result.ok
    assert launches == [str(chrome.resolve())]
    assert index.search("Chrome").matches


def test_manual_application_settings_validate_save_remove(
    qt_app: QApplication,
    tmp_path: Path,
) -> None:
    core, _, _ = make_core(tmp_path / "core", [], [])
    executable = _exe(tmp_path / "Apps" / "Example.exe")
    dialog = FibiSettingsDialog(core)
    dialog.application_name_input.setText("Example")
    dialog.application_path_input.setText(str(executable))
    dialog._test_application_path()
    assert "valid" in dialog.application_status.text().lower()
    dialog._save_application()
    assert core.app_index.manual_entries()[0].display_name == "Example"
    dialog._remove_application()
    assert core.app_index.manual_entries() == []

    dialog.reply_style_combo.setCurrentIndex(dialog.reply_style_combo.findData("normal"))
    dialog._save()
    assert core.app_settings.settings.reply_style == "normal"
