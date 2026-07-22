"""Structural contract tests for the application composition boundary."""

from __future__ import annotations

from fibi.app.contracts import (
    DesktopActionService,
    LanguageProvider,
    MemoryService,
    ProjectService,
    SpeechToTextService,
    TextToSpeechService,
)


class _Provider:
    def generate(self, prompt: str):
        return prompt


class _Memory:
    def remember_fact(self, content: str, **kwargs):
        return content

    def retrieve_relevant(self, query: str, filters=None, top_k: int = 5):
        return []

    def update_memory(self, memory_id: int, **kwargs):
        return None

    def delete_memory(self, memory_id: int) -> bool:
        return True


class _Actions:
    def execute(self, intent):
        return intent


class _Projects:
    def list_workspaces(self):
        return []

    def files(self):
        return []

    def search(self, query: str):
        return []

    def read_file(self, relative_path: str):
        return relative_path


class _Stt:
    def listen(self, settings, source="mic_button", max_duration_seconds=6, phrase_timeout_seconds=3):
        return None

    def devices(self):
        return []


class _Tts:
    def decide(self, model_used, text, allow_tts, requested_priority=""):
        return None

    def mark_started(self):
        return None

    def mark_finished(self, duration_ms):
        return None

    def stop(self):
        return "stopped"


def test_existing_style_doubles_satisfy_minimal_protocols() -> None:
    assert isinstance(_Provider(), LanguageProvider)
    assert isinstance(_Memory(), MemoryService)
    assert isinstance(_Actions(), DesktopActionService)
    assert isinstance(_Projects(), ProjectService)
    assert isinstance(_Stt(), SpeechToTextService)
    assert isinstance(_Tts(), TextToSpeechService)
