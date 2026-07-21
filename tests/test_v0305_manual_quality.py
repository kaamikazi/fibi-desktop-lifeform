"""Regression tests for useful answers and explicit provider/voice controls."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from fibi.engines.model_router import ModelRouter
from fibi.engines.types import ModelResult
from fibi.ui.fibi_window import FibiSettingsDialog
from tests.smoke_v012_actions import make_core
from tests.test_v0301_gemini_provider import CountingOllama, FakeModelsAPI, provider_with


class ScriptedOllama:
    def __init__(self, replies: list[str], error: str | None = None) -> None:
        self.replies = replies
        self.error = error
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        index = min(self.calls, len(self.replies) - 1)
        self.calls += 1
        return ModelResult(self.replies[index], "mock-ollama", 0.01, self.error)

    def health_check(self) -> bool:
        return self.error is None


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "runtime"))


def _core_with_ollama(tmp_path: Path, replies: list[str], error: str | None = None):
    core, _, _ = make_core(tmp_path / "core", [], [])
    ollama = ScriptedOllama(replies, error)
    core.model_router = ModelRouter(ollama=ollama)
    core.model_router.set_mode("ollama")
    core.model_router.set_automatic_fallback(False)
    core.privacy.update(allow_ollama=True)
    return core, ollama


@pytest.mark.parametrize(
    "message",
    [
        "what are you doing?",
        "what do you think?",
        "tell me about Python",
        "how does recursion work?",
        "why does this fail?",
        "make a plan for my project",
        "write code to sort this list",
        "what do you remember about me?",
    ],
)
def test_meaningful_prompts_use_selected_model(message: str, tmp_path: Path) -> None:
    core, ollama = _core_with_ollama(tmp_path / str(abs(hash(message))), ["A direct useful answer."])
    response = core.respond(message)
    assert ollama.calls == 1
    assert response.model_used == "mock-ollama"
    assert response.display_text == "A direct useful answer."


def test_greeting_only_may_stay_local(tmp_path: Path) -> None:
    core, ollama = _core_with_ollama(tmp_path, ["unused"])
    response = core.respond("hello")
    assert response.model_used == "local-greeting"
    assert ollama.calls == 0


def test_cute_only_model_reply_is_retried_on_same_provider(tmp_path: Path) -> None:
    core, ollama = _core_with_ollama(
        tmp_path,
        ["being tiny", "Python is a programming language used for automation and applications."],
    )
    response = core.respond("what is Python?")
    assert ollama.calls == 2
    assert response.display_text.startswith("Python is a programming language")
    assert core.model_router.selected_provider() == "ollama"


def test_provider_failure_never_switches_automatically(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "gemini", [], [])
    api = FakeModelsAPI(error=TimeoutError("timed out"))
    ollama = CountingOllama("must not be used")
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.model_router.set_automatic_fallback(False)
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True, allow_ollama=True)
    response = core.respond("explain dependency injection")
    assert core.model_router.selected_provider() == "gemini"
    assert ollama.calls == 0
    assert response.used_fallback
    assert "selected provider" in response.display_text.lower() or "gemini" in response.display_text.lower()


def test_manual_provider_commands_persist_selection(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path, [], [])
    api = FakeModelsAPI()
    core.model_router = ModelRouter(ollama=CountingOllama(), gemini=provider_with(api))
    selected = core.respond("/provider use gemini")
    assert "Gemini selected" in selected.display_text
    assert core.model_router.selected_provider() == "gemini"
    assert core.app_settings.settings.language_provider == "gemini"
    core.respond("/provider use ollama")
    assert core.model_router.selected_provider() == "ollama"
    assert core.app_settings.settings.language_provider == "ollama"


def test_manual_rvc_commands_persist_and_chat_does_not_change_them(tmp_path: Path) -> None:
    core, ollama = _core_with_ollama(tmp_path, ["A useful answer."])
    core.respond("/voice rvc on")
    assert core.voice_skin_settings.settings.rvc_enabled
    core.respond("explain this idea")
    assert ollama.calls == 1
    assert core.voice_skin_settings.settings.rvc_enabled
    core.respond("/voice rvc off")
    assert not core.voice_skin_settings.settings.rvc_enabled


def test_settings_choices_apply_only_when_saved(qt_app: QApplication, tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path, [], [])
    core.model_router = ModelRouter(ollama=CountingOllama(), gemini=provider_with(FakeModelsAPI()))
    core.model_router.set_mode("ollama")
    core.voice_skin_settings.update(allow_rvc_voice_skin=False, rvc_enabled=False)
    dialog = FibiSettingsDialog(core)
    dialog.provider_combo.setCurrentIndex(1)
    dialog.provider_fallback_checkbox.setChecked(True)
    dialog.rvc_checkbox.setChecked(True)
    assert core.model_router.selected_provider() == "ollama"
    assert not core.model_router.automatic_fallback_enabled
    assert not core.voice_skin_settings.settings.rvc_enabled
    dialog._save()
    assert core.model_router.selected_provider() == "gemini"
    assert core.model_router.automatic_fallback_enabled
    assert core.voice_skin_settings.settings.rvc_enabled


def test_demo_rvc_seed_happens_only_once(tmp_path: Path) -> None:
    from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine
    from tools.reset_demo_profile import configure_demo_voice

    profile = tmp_path / "demo"
    profile.mkdir()
    configure_demo_voice(profile)
    engine = VoiceSkinSettingsEngine(profile / "voice_skin_settings.json")
    assert not engine.settings.rvc_enabled
    engine.update(allow_rvc_voice_skin=True, rvc_enabled=True, rvc_backend="rvc_python")
    configure_demo_voice(profile)
    reloaded = VoiceSkinSettingsEngine(profile / "voice_skin_settings.json")
    assert reloaded.settings.rvc_enabled
    assert reloaded.settings.allow_rvc_voice_skin
