"""Minimal structural contracts used by Fibi's composition boundary.

The protocols describe behavior already provided by existing engines. They do
not require implementations to inherit from a framework-specific base class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from fibi.memory.query_models import (
    MemoryListFilter,
    MemoryQueryHealth,
    MemoryQueryRequest,
    MemoryQueryResult,
    MemoryRecordView,
    MemorySourceHealth,
    MemorySourceReference,
)


@runtime_checkable
class LanguageProvider(Protocol):
    """Generate one model result from a prepared prompt."""

    def generate(self, prompt: str) -> Any: ...


@runtime_checkable
class MemoryService(Protocol):
    """Store and retrieve Fibi's local long-term memories."""

    def remember_fact(self, content: str, **kwargs: Any) -> Any: ...

    def retrieve_relevant(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[Any]: ...

    def update_memory(self, memory_id: int, **kwargs: Any) -> Any: ...

    def delete_memory(self, memory_id: int) -> bool: ...


@runtime_checkable
class MemoryQueryService(Protocol):
    """Stage 1 storage-neutral reads with no mutation capability."""

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None: ...

    def query(self, request: MemoryQueryRequest) -> MemoryQueryResult: ...

    def list(self, filters: MemoryListFilter) -> MemoryQueryResult: ...

    def health(self) -> MemoryQueryHealth: ...

    def available_sources(self) -> tuple[MemorySourceHealth, ...]: ...

    def build_candidates(self, request: MemoryQueryRequest) -> MemoryQueryResult: ...


@runtime_checkable
class DesktopActionService(Protocol):
    """Execute a previously classified and permission-checked action."""

    def execute(self, intent: Any) -> Any: ...


@runtime_checkable
class ProjectService(Protocol):
    """Expose registered project workspaces without granting shell access."""

    def list_workspaces(self) -> list[Any]: ...

    def files(self) -> list[Any]: ...

    def search(self, query: str) -> list[Any]: ...

    def read_file(self, relative_path: str) -> Any: ...


@runtime_checkable
class SpeechToTextService(Protocol):
    """Transcribe a bounded in-memory microphone capture."""

    def listen(
        self,
        settings: Any,
        source: str = "mic_button",
        max_duration_seconds: int = 6,
        phrase_timeout_seconds: int = 3,
    ) -> Any: ...

    def devices(self) -> list[Any]: ...


@runtime_checkable
class TextToSpeechService(Protocol):
    """Coordinate speech policy and playback state."""

    def decide(
        self,
        model_used: str,
        text: str,
        allow_tts: bool,
        requested_priority: str = "",
    ) -> Any: ...

    def mark_started(self) -> None: ...

    def mark_finished(self, duration_ms: float) -> None: ...

    def stop(self) -> str: ...


@runtime_checkable
class CoreRuntime(Protocol):
    """The lifecycle surface needed by :class:`ApplicationRuntime`."""

    life: Any

    def shutdown(self) -> Any: ...
