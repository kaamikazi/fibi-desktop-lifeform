"""Direct smoke tests for Fibi v0.13 Voice Command Mode."""

from __future__ import annotations

import builtins
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.action_journal_engine import ActionJournalEngine
from fibi.engines.action_settings_engine import ActionSettingsEngine
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.core import FibiCore
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.types import ModelResult, Observation, VoiceInputSettings, VoiceTranscriptionResult
from fibi.engines.voice_settings_engine import VoiceSettingsEngine


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "Fibi", None)


class NoModel(ModelEngine):
    def __init__(self, text: str = "") -> None:
        self.calls = 0
        self.text = text

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult(self.text, "fake-model", 0.0, None)


class FakeSpeech(SpeechRecognitionEngine):
    def __init__(self, result: VoiceTranscriptionResult) -> None:
        self.result = result

    def listen(self, settings: VoiceInputSettings, source: str = "mic_button", max_duration_seconds: int = 6, phrase_timeout_seconds: int = 3) -> VoiceTranscriptionResult:
        self.result.source = source
        return self.result

    def devices(self):
        from fibi.engines.types import VoiceDeviceInfo

        return [VoiceDeviceInfo("0", "fake mic", True)]


def make_core(root: Path, speech: SpeechRecognitionEngine, opened: list[str], launched: list[str], model: NoModel | None = None) -> FibiCore:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"legacy_v012": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    app_index = AppIndexEngine(root / "app_index.json")
    fake_exe = root / "chrome.exe"
    fake_exe.write_text("", encoding="utf-8")
    app_index.add_entry("Chrome", str(fake_exe), "test")
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=model or NoModel(),
        privacy=PrivacySettingsEngine(state),
        action_settings=ActionSettingsEngine(state),
        app_index=app_index,
        desktop_actions=DesktopActionEngine(app_index, browser_open=lambda url: opened.append(url) or True, app_launcher=lambda path: launched.append(path)),
        action_journal=ActionJournalEngine(root / "action_journal.jsonl"),
        voice_settings=VoiceSettingsEngine(state),
        speech_recognition=speech,
    )


def missing_dependency_result() -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "speech_recognition":
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    builtins.__import__ = fake_import
    try:
        result = SpeechRecognitionEngine().listen(VoiceInputSettings(allow_voice_input=True))
        assert result.error == "voice brain not installed."
    finally:
        builtins.__import__ = original_import


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        speech = FakeSpeech(VoiceTranscriptionResult("open chrome", "open chrome", 0.9, source="mic_button"))
        core = make_core(root, speech, opened, launched)

        assert core.voice_settings.settings.allow_voice_input is False
        assert core.voice_settings.settings.wake_word_enabled is False
        assert core.voice_settings.settings.save_voice_audio is False
        assert core.voice_settings.settings.save_transcripts_to_journal is False

        disabled_listen = core.respond("/listen")
        assert "ears tucked away" in disabled_listen.display_text
        assert core.model.calls == 0

        enabled = core.respond("/voice input on confirm")
        assert "ears enabled" in enabled.display_text
        assert core.voice_settings.settings.allow_voice_input is True

        status = core.respond("/voice status")
        assert status.model_used == "local-command"
        assert "ears on" in status.display_text

        devices = core.respond("/mic devices")
        assert "fake mic" in devices.display_text
        assert core.respond("/wake word status").display_text == "Wake word mode is off."

        listened = core.respond("/listen")
        assert "Result: completed" in listened.display_text
        assert "Chrome opened" in listened.display_text
        assert launched
        assert core.model.calls == 0

        low_root = root / "low"
        low_core = make_core(
            low_root,
            FakeSpeech(VoiceTranscriptionResult("open chrome", "open chrome", 0.4, source="mic_button")),
            [],
            [],
        )
        low_core.respond("/voice input on confirm")
        low = low_core.start_voice_listen(source="mic_button")
        assert "not sure" in low.display_text

        safe_root = root / "safe"
        safe_opened: list[str] = []
        safe_core = make_core(
            safe_root,
            FakeSpeech(VoiceTranscriptionResult("search Google for Python recursion", "search Google for Python recursion", 0.95, source="mic_button")),
            safe_opened,
            [],
        )
        safe_core.respond("/voice input on confirm")
        safe = safe_core.start_voice_listen(source="mic_button")
        assert "opened" in safe.display_text
        assert safe_opened and "Python+recursion" in safe_opened[-1]

        risky_core = make_core(
            root / "risky",
            FakeSpeech(VoiceTranscriptionResult("shutdown pc", "shutdown pc", 0.95, source="mic_button")),
            [],
            [],
        )
        risky_core.respond("/voice input on confirm")
        risky_core.respond("/shutdown actions on confirm")
        risky = risky_core.start_voice_listen(source="mic_button")
        assert "confirm shutdown" in risky.display_text
        assert risky_core.action_confirmations.pending() is not None

        blocked_core = make_core(
            root / "blocked",
            FakeSpeech(VoiceTranscriptionResult("delete this file", "delete this file", 0.95, source="mic_button")),
            [],
            [],
        )
        blocked_core.respond("/voice input on confirm")
        blocked = blocked_core.start_voice_listen(source="mic_button")
        assert blocked.used_fallback is True
        assert (
            "dangerous" in blocked.display_text
            or "refuses" in blocked.display_text
            or "touching" in blocked.display_text
                or "human hands" in blocked.display_text
                or "blocked" in blocked.display_text
                or "not allowed" in blocked.display_text
            )

        model_core = make_core(
            root / "model",
            FakeSpeech(VoiceTranscriptionResult("what is Python", "what is Python", 0.95, source="mic_button")),
            [],
            [],
            model=NoModel("open chrome"),
        )
        model_core.respond("/voice input on confirm")
        response = model_core.start_voice_listen(source="mic_button")
        assert response.display_text == "open chrome"
        assert model_core.app_index.count() == 1

        missing_dependency_result()

    print("Fibi v0.13 voice smoke tests passed.")


if __name__ == "__main__":
    run()


