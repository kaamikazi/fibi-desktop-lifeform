"""Regression tests for Fibi v0.30.3 routing, provider config, and Settings UI."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QLabel

from fibi.environment import load_environment
from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.model_router import ModelRouter
from fibi.ui.fibi_window import FibiSettingsDialog
from tests.smoke_v012_actions import make_core
from tests.test_v0301_gemini_provider import CountingOllama, FakeModelsAPI, provider_with


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_runtime_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep provider and voice persistence tests out of the user's runtime data."""

    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "runtime-data"))


@pytest.mark.parametrize("message", ["hi", "hello", "heyyyyyyy"])
def test_exact_greetings_remain_local(message: str, tmp_path: Path) -> None:
    core, model, _ = make_core(tmp_path / message, [], [])
    response = core.respond(message)
    assert response.model_used == "local-greeting"
    assert model.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "what do you think about memory?",
        "explain model-independent identity",
        "why should memory remain outside the LLM?",
        "compare local and cloud language providers",
        "help me plan a software project",
        "summarize how Fibi protects memory",
        "tell me something interesting",
        "how does your memory work?",
        "what have you learned recently?",
    ],
)
def test_meaningful_conversation_reaches_model_router(message: str, tmp_path: Path) -> None:
    core, model, _ = make_core(tmp_path / str(abs(hash(message))), [], [])
    response = core.respond(message)
    assert core.route_decisions.last_decision.model_router_allowed
    assert model.calls == 1
    assert response.model_used != "local-micro-brain"


def test_short_social_question_uses_selected_model(tmp_path: Path) -> None:
    core, model, _ = make_core(tmp_path / "social", [], [])
    first = core.respond("what are you doing?")
    second = core.respond("what are you doing?")
    assert model.calls == 2
    assert first.model_used == "local-fallback"
    assert second.model_used == "local-fallback"


def test_classifier_prefers_model_when_local_intent_is_uncertain() -> None:
    classifier = FastResponseClassifier()
    assert classifier.classify("what are you doing?").category == "complex_chat"
    assert classifier.classify("what do you think about memory?").category == "complex_chat"
    assert classifier.classify("how are you feeling today?").category == "complex_chat"
    assert classifier.classify("tell me something interesting").should_use_model


def test_gemini_selected_routes_reasoning_with_mock_only(tmp_path: Path) -> None:
    core, ollama, _ = make_core(tmp_path / "gemini", [], [])
    api = FakeModelsAPI(response_text="tiny routed answer")
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True)
    response = core.respond("explain why memory stays outside the model")
    assert api.generate_calls == 1
    assert ollama.calls == 0
    assert response.display_text == "tiny routed answer"
    assert core.model_router.last_provider_used == "gemini"


def test_greeting_stays_local_while_gemini_selected(tmp_path: Path) -> None:
    core, ollama, _ = make_core(tmp_path / "gemini-greeting", [], [])
    api = FakeModelsAPI()
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True)
    assert core.respond("hello").model_used == "local-greeting"
    assert api.generate_calls == 0
    assert ollama.calls == 0


def test_live_data_uses_opted_in_gemini_search_grounding(tmp_path: Path) -> None:
    core, ollama, _ = make_core(tmp_path / "gemini-search", [], [])
    api = FakeModelsAPI(response_text="grounded tiny weather")
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True)
    response = core.respond("weather today")
    assert response.display_text == "grounded tiny weather"
    assert api.generate_calls == 1
    assert api.configs[0]["tools"] == [{"google_search": {}}]
    assert ollama.calls == 0


def test_provider_selection_persists_without_storing_secret(tmp_path: Path) -> None:
    core, ollama, _ = make_core(tmp_path / "persist-provider", [], [])
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(FakeModelsAPI()))
    selected = core.respond("/provider use gemini")
    assert "CLOUD - Gemini selected" in selected.display_text
    assert core.app_settings.settings.language_provider == "gemini"
    assert "api_key" not in core.app_settings.settings_path.read_text(encoding="utf-8").lower()


def test_settings_selection_is_reflected_in_command_status(
    tmp_path: Path,
    qt_app: QApplication,
) -> None:
    core, _, _ = make_core(tmp_path / "settings-provider-sync", [], [])
    dialog = FibiSettingsDialog(core)
    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("gemini"))
    dialog._save()

    assert "Selected: gemini" in core.respond("/provider status").display_text


def test_visible_gemini_fallback_updates_active_provider_status(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "fallback-status", [], [])
    api = FakeModelsAPI(error=TimeoutError("timed out"))
    ollama = CountingOllama("local rescue")
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.model_router.set_automatic_fallback(True)
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True, allow_ollama=True)
    core.respond("explain provider fallback behavior")
    status = core.get_provider_status()
    assert "Selected: gemini" in status
    assert "Active: ollama" in status
    assert "Last fallback provider: ollama" in status
    assert "Last provider error category: timeout" in status


def test_project_root_env_is_independent_of_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    root = tmp_path / "project"
    root.mkdir()
    (root / ".env").write_text("GEMINI_API_KEY=fake-test-only-key\n", encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    status = load_environment(root, packaged=False)
    assert status.loaded
    assert status.source == "project_root_env"
    assert status.gemini_key_configured


def test_process_environment_has_priority(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "process-test-only-key")
    (tmp_path / ".env").write_text("GEMINI_API_KEY=file-test-only-key\n", encoding="utf-8")
    status = load_environment(tmp_path, packaged=False)
    assert status.gemini_key_configured
    assert os.environ["GEMINI_API_KEY"] == "process-test-only-key"


def test_packaged_mode_does_not_implicitly_load_source_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=fake-test-only-key\n", encoding="utf-8")
    status = load_environment(tmp_path, packaged=True)
    assert not status.checked_project_env
    assert not status.gemini_key_configured


def test_provider_status_is_boolean_only_and_never_prints_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_key = "unit-test-secret-value"
    monkeypatch.setenv("GEMINI_API_KEY", fake_key)
    core, _, _ = make_core(tmp_path / "status", [], [])
    status = core.get_provider_status()
    captured = capsys.readouterr()
    assert "Gemini key configured:" in status
    assert fake_key not in status
    assert fake_key not in captured.out
    assert fake_key not in captured.err


def test_settings_tabs_and_provider_controls_are_readable(
    qt_app: QApplication,
    tmp_path: Path,
) -> None:
    core, _, _ = make_core(tmp_path / "settings", [], [])
    dialog = FibiSettingsDialog(core)
    dialog.show()
    qt_app.processEvents()
    assert [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())] == [
        "General", "Behavior", "Privacy", "Models", "Voice", "Actions", "Performance"
    ]
    stylesheet = dialog.styleSheet()
    assert "QTabBar::tab" in stylesheet
    assert "color: #4b3055" in stylesheet
    assert "QPushButton:disabled" in stylesheet
    dialog.tabs.setCurrentIndex(3)
    qt_app.processEvents()
    assert dialog.provider_combo.isVisible()
    assert dialog.provider_status_badge.isVisible()
    assert dialog.provider_test_button.isVisible()
    assert not dialog.rvc_checkbox.isChecked()
    assert dialog.provider_fallback_status.text() == "Automatic fallback: Off"
    assert dialog.rvc_status_label.text() == "RVC: Off"
    visible_text = "\n".join(label.text() for label in dialog.findChildren(QLabel))
    assert "GEMINI_API_KEY=" not in visible_text
    dialog.close()


@pytest.mark.parametrize("size", [QSize(600, 500), QSize(720, 620), QSize(900, 720)])
def test_settings_layout_remains_valid_at_multiple_sizes(
    qt_app: QApplication,
    tmp_path: Path,
    size: QSize,
) -> None:
    core, _, _ = make_core(tmp_path / f"settings-{size.width()}", [], [])
    dialog = FibiSettingsDialog(core)
    dialog.resize(size)
    dialog.show()
    dialog.tabs.setCurrentIndex(3)
    qt_app.processEvents()
    dialog.layout().activate()
    assert dialog.tabs.width() > 0
    assert dialog.provider_combo.width() > 100
    assert dialog.provider_status_badge.geometry().bottom() < dialog.cloud_label.geometry().top()
    dialog.close()


def test_rvc_can_be_disabled_without_disabling_tts(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "rvc", [], [])
    core.privacy.update(allow_tts=True)
    core.voice_skin_settings.update(allow_rvc_voice_skin=True, rvc_enabled=True)
    response = core.respond("/voice rvc off")
    assert "Edge TTS only" in response.display_text
    assert not core.voice_skin_settings.settings.rvc_enabled
    assert not core.voice_skin_settings.settings.allow_rvc_voice_skin
    assert core.privacy.settings.allow_tts


def test_rvc_can_be_enabled_with_direct_command(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "rvc-on", [], [])
    response = core.respond("/voice rvc on")
    assert core.voice_skin_settings.settings.rvc_enabled
    assert core.voice_skin_settings.settings.allow_rvc_voice_skin
    assert core.voice_skin_settings.settings.rvc_backend == "rvc_python"
    assert response.tts_priority == "silent"


def test_provider_error_fallback_is_silent_and_neutral(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "provider-error", [], [])
    core._model_router_invoked = True
    response = core._finish(
        "explain this",
        "Gemini is temporarily unavailable.",
        "angry",
        "local-fallback",
        True,
        core.observation.observe(),
        None,
    )
    assert response.tts_text == ""
    assert response.tts_priority == "silent"
    assert response.mood == "idle"


def test_safe_health_snapshot_exposes_route_and_latency_categories(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "health", [], [])
    core.respond("hello")
    snapshot = core.get_gui_health_snapshot()
    assert "conversation routing:" in snapshot
    assert "provider runtime:" in snapshot
    assert "latency:" in snapshot
