"""Hard concise, local wake-word, and structured-memory regressions."""

from __future__ import annotations

from pathlib import Path

import pytest

from fibi.engines.reply_style_engine import ReplyStyleEngine
from fibi.engines.structured_memory_engine import StructuredMemoryEngine
from fibi.engines.types import VoiceInputSettings, VoiceTranscriptionResult
from fibi.engines.wake_word_engine import WakeWordEngine
from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService
from tests.smoke_v012_actions import make_core


class QueuedSpeech:
    def __init__(self, transcripts: list[str]) -> None:
        self.transcripts = list(transcripts)
        self.calls: list[tuple[str, int, int]] = []

    def listen(
        self,
        _settings: VoiceInputSettings,
        source: str = "mic_button",
        max_duration_seconds: int = 6,
        phrase_timeout_seconds: int = 3,
    ) -> VoiceTranscriptionResult:
        self.calls.append((source, max_duration_seconds, phrase_timeout_seconds))
        transcript = self.transcripts.pop(0) if self.transcripts else ""
        return VoiceTranscriptionResult(
            transcript=transcript,
            raw_text=transcript,
            confidence=0.95 if transcript else 0.0,
            source=source,
            should_route_to_core=bool(transcript),
            error=None if transcript else "silence",
        )

    def devices(self):
        return []


def _rag(tmp_path: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=tmp_path / "memory.db",
            vector_dir=tmp_path / "vectors",
            similarity_threshold=0.0,
            duplicate_threshold=0.88,
        )
    )


@pytest.mark.parametrize("phrase", ["oi fibi", "Oi, Fibi!", "oy phoebe"])
def test_local_wake_phrase_detection(phrase: str) -> None:
    assert WakeWordEngine.detected(phrase)
    assert not WakeWordEngine.detected("hello assistant")


def test_wake_mode_off_by_default_and_manual_commands_preserve_provider_voice(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path, [], [])
    provider = core.model_router.selected_provider()
    rvc = core.voice_skin_settings.settings.rvc_enabled
    assert not core.voice_settings.settings.wake_word_enabled
    assert "off" in core.respond("/wake status").display_text.lower()
    core.respond("/wake on")
    assert core.voice_settings.settings.wake_word_enabled
    assert core.voice_settings.settings.allow_voice_input
    assert not core.voice_settings.settings.save_voice_audio
    core.respond("/voice input on confirm")
    assert core.voice_settings.settings.wake_word_enabled
    core.respond("/wake off")
    assert not core.voice_settings.settings.wake_word_enabled
    assert core.model_router.selected_provider() == provider
    assert core.voice_skin_settings.settings.rvc_enabled == rvc


def test_wake_engine_uses_local_probe_then_one_command_without_audio_files(tmp_path: Path) -> None:
    speech = QueuedSpeech(["oi fibi", "hello"])
    engine = WakeWordEngine(speech)  # type: ignore[arg-type]
    settings = VoiceInputSettings(allow_voice_input=True, wake_word_enabled=True)
    before = set(tmp_path.rglob("*"))
    detected, probe = engine.listen_once(settings)
    command = engine.capture_command(settings)
    assert detected
    assert probe.source == "wake_word_probe"
    assert command.transcript == "hello"
    assert speech.calls == [("wake_word_probe", 3, 2), ("wake_word_command", 8, 4)]
    assert set(tmp_path.rglob("*")) == before
    assert not settings.save_voice_audio


def test_core_wake_capture_routes_follow_up_through_normal_handling(tmp_path: Path) -> None:
    core, model, _ = make_core(tmp_path, [], [])
    speech = QueuedSpeech(["oi fibi", "hello"])
    core.speech_recognition = speech  # type: ignore[assignment]
    core.wake_word = WakeWordEngine(speech)  # type: ignore[arg-type]
    core.respond("/wake on")
    detected, _probe = core.listen_for_wake_once()
    response = core.capture_wake_command()
    assert detected
    assert response.model_used == "local-greeting"
    assert model.calls == 0


def test_structured_memory_extraction_ignores_questions_and_general_chat() -> None:
    extractor = StructuredMemoryEngine()
    relation = extractor.extract("My sister studies mathematical finance.")
    assert len(relation) == 1
    assert relation[0].category == "relationship"
    assert relation[0].memory_key == "relationship:sister:study"
    assert "mathematical finance" in relation[0].content
    assert extractor.extract("What does my sister study?") == []
    assert extractor.extract("That is interesting.") == []


def test_relevant_memory_recall_has_real_similarity(tmp_path: Path) -> None:
    service = _rag(tmp_path)
    saved = service.add_memory(
        "The user's sister studies mathematical finance.",
        category="relationship",
        importance=0.85,
        confidence=0.95,
        memory_key="relationship:sister:study",
    )
    service.add_memory("The user is working on Project Fibi.", category="project")
    results = service.search_memories("What does my sister study?", top_k=5, similarity_threshold=0.0)
    assert results
    assert results[0].memory.id == saved.id
    assert results[0].similarity > 0.0


def test_duplicate_and_contradiction_update_existing_memory(tmp_path: Path) -> None:
    service = _rag(tmp_path)
    first = service.add_memory(
        "The user's sister studies mathematics.",
        category="relationship",
        memory_key="relationship:sister:study",
    )
    duplicate = service.add_memory(
        "The user's sister studies mathematics.",
        category="relationship",
        memory_key="relationship:sister:study",
    )
    updated = service.add_memory(
        "The user's sister studies mathematical finance.",
        category="relationship",
        memory_key="relationship:sister:study",
        confidence=0.95,
    )
    assert duplicate.id == first.id == updated.id
    assert service.repository.count_active() == 1
    assert "mathematical finance" in updated.content
    check = service.detect_duplicate(updated.content)
    assert check.is_duplicate
    assert check.similarity == pytest.approx(1.0)


def test_sensitive_contradiction_is_not_silently_overwritten(tmp_path: Path) -> None:
    service = _rag(tmp_path)
    original = service.add_memory(
        "The user has a private relationship note.",
        category="relationship",
        memory_key="relationship:private",
        metadata={"sensitive_flag": "relationship"},
    )
    with pytest.raises(PermissionError):
        service.add_memory(
            "The private relationship note changed.",
            category="relationship",
            memory_key="relationship:private",
        )
    assert service.repository.get(int(original.id)).content == original.content  # type: ignore[arg-type]


def test_core_memory_commands_and_temporary_context(tmp_path: Path) -> None:
    core, model, _ = make_core(tmp_path / "core", [], [])
    remembered = core.respond("/memory remember My sister studies mathematical finance.")
    assert "saved" in remembered.display_text.lower()
    recalled = core.respond("/memory recall sister study")
    assert "mathematical finance" in recalled.display_text.lower()
    conversational = core.respond("What does my sister study?")
    assert "mathematical finance" in conversational.display_text.lower()
    assert conversational.model_used == "local-memory-recall"
    assert model.calls == 0
    assert "relationship" in core.respond("/memory stats").display_text.lower()

    core._remember_conversation_rag("user", "temporary context sentence")
    temporary = [
        memory
        for memory in core.memory_router.rag_memory.service.repository.list_active()
        if memory.category == "temporary_context"
    ]
    assert temporary
    assert temporary[-1].expires_at
    assert temporary[-1].metadata["temporary"] is True
