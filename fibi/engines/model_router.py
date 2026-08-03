"""Deprecated compatibility facade for Fibi's provider subsystem.

New code uses ``ProviderRegistry``, ``ProviderSelectionService``,
``CompanionGenerationService``, and ``ProviderDiagnostics`` directly. This
facade remains for legacy constructors and integrations while those callers
migrate; it owns no providers, fallback policy, persistence, or diagnostics.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from fibi.engines.types import ModelRouterResult, Observation, PrivacySettings
from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.generation import CompanionGenerationService
from fibi.services.providers.models import GenerationRequest
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService

if TYPE_CHECKING:
    from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
    from fibi.engines.model_engine import ModelEngine
    from fibi.engines.nvidia_model_engine import NvidiaModelEngine
    from fibi.engines.openai_compatible_provider import OpenAICompatibleProvider
    from fibi.providers.gemini_provider import GeminiProvider


class ModelRouter:
    """Read-only compatibility projection over authoritative provider services.

    Removal criteria: no production or supported external caller constructs or
    calls this class, and one full release has exposed the replacement APIs.
    Earliest intended removal is Fibi 0.5.
    """

    def __init__(
        self,
        ollama: ModelEngine | None = None,
        nvidia: NvidiaModelEngine | None = None,
        generic_cloud: OpenAICompatibleProvider | None = None,
        gemini: GeminiProvider | None = None,
        sanitizer: CloudContextSanitizer | None = None,
    ) -> None:
        # These injected implementations are retained only so the centralized
        # provider factory can adapt old direct constructors.
        self._ollama = ollama
        self._nvidia = nvidia
        self._generic_cloud = generic_cloud
        self._gemini = gemini
        self._sanitizer = sanitizer
        configured = str(getattr(getattr(gemini, "config", None), "selected_provider", "ollama"))
        self._bootstrap_provider_id = configured if configured in {"gemini", "ollama"} else "ollama"
        self._bootstrap_fallback_enabled = False
        self._registry: ProviderRegistry | None = None
        self._selection: ProviderSelectionService | None = None
        self._generation: CompanionGenerationService | None = None
        self._diagnostics: ProviderDiagnostics | None = None

    @property
    def ollama(self) -> Any:
        return self._ollama

    @property
    def nvidia(self) -> Any:
        return self._nvidia

    @property
    def generic_cloud(self) -> Any:
        return self._generic_cloud

    @property
    def gemini(self) -> Any:
        return self._gemini

    @property
    def sanitizer(self) -> Any:
        return self._sanitizer

    def attach(
        self,
        registry: ProviderRegistry,
        selection: ProviderSelectionService,
        generation: CompanionGenerationService,
        diagnostics: ProviderDiagnostics,
    ) -> None:
        """Attach the one authoritative runtime subsystem."""

        self._registry = registry
        self._selection = selection
        self._generation = generation
        self._diagnostics = diagnostics
        self._bootstrap_provider_id = selection.get_selected_provider_id()
        self._bootstrap_fallback_enabled = generation.fallback_enabled

    def bind_legacy_dependencies(self, *, ollama: Any, gemini: Any, sanitizer: Any) -> None:
        """Expose factory-owned implementations to verified legacy callers."""

        self._ollama = ollama
        self._gemini = gemini
        self._sanitizer = sanitizer

    def set_mode(self, mode: str) -> str:
        """Compatibility forwarder; new code calls selection.select_provider."""

        provider_id = mode if mode in {"ollama", "gemini"} else "ollama"
        if self._selection is None:
            self._bootstrap_provider_id = provider_id
            self._require_generation()
        if self._selection is None:  # pragma: no cover - factory contract guard
            return provider_id
        self._selection.select_provider(provider_id, persist=False)
        return self._selection.get_selected_provider_id()

    def set_automatic_fallback(self, enabled: bool) -> bool:
        """Compatibility forwarder; new code calls generation.set_fallback."""

        if self._generation is None:
            self._bootstrap_fallback_enabled = bool(enabled)
            self._require_generation()
        if self._generation is None:  # pragma: no cover - factory contract guard
            return self._bootstrap_fallback_enabled
        self._generation.set_fallback(bool(enabled), "ollama")
        return self._generation.fallback_enabled

    def selected_provider(self) -> str:
        return (
            self._selection.get_selected_provider_id()
            if self._selection is not None
            else self._bootstrap_provider_id
        )

    @property
    def mode(self) -> str:
        return self.selected_provider()

    @property
    def automatic_fallback_enabled(self) -> bool:
        return (
            self._generation.fallback_enabled
            if self._generation is not None
            else self._bootstrap_fallback_enabled
        )

    def context_preview(self, approved_memory_summaries: list[str] | None = None):
        self._warn("context_preview", "CompanionGenerationService.context_preview")
        return self._require_generation().context_preview(approved_memory_summaries)

    def route(
        self,
        prompt: str,
        user_message: str,
        mood: str,
        privacy: PrivacySettings,
        observation: Observation | None = None,
        memory_hints: list[str] | None = None,
        fast_category: str = "unknown",
        local_brain_confidence: str = "n/a",
        local_brain_handled: bool | None = None,
        requires_live_data: bool = False,
        response_instruction: str = "",
    ) -> ModelRouterResult:
        """Forward a legacy request through the authoritative generation use case."""

        del fast_category, local_brain_confidence, local_brain_handled
        self._warn("route", "CompanionGenerationService.generate")
        generation = self._require_generation()
        allowed: set[str] = set()
        if privacy.allow_ollama:
            allowed.add("ollama")
        if privacy.allow_cloud_model and privacy.allow_gemini_api:
            allowed.add("gemini")
        result = generation.generate(
            GenerationRequest(
                user_text=user_message,
                prepared_prompt=prompt,
                mood=mood,
                time_of_day=observation.time_of_day if observation else "unknown",
                context_level=privacy.cloud_context_level,
                approved_context_summaries=tuple(memory_hints or ()),
                response_instruction=response_instruction,
                search_grounding_allowed=requires_live_data,
                allowed_provider_ids=frozenset(allowed),
            )
        )
        text = result.text if result.success else generation.present_error(result)
        return ModelRouterResult(
            result.provider_id or "fallback",
            result.model_id,
            result.latency_ms,
            result.provider_id == "gemini",
            result.fallback_used or not result.success,
            result.error_message or None,
            text,
            result.attempted_provider_id,
            result.retry_count,
            result.error_category.value if result.error_category else "",
            max(0.0, result.latency_ms - result.fallback_latency_ms),
            result.fallback_latency_ms,
            True,
        )

    @property
    def last_provider_used(self) -> str:
        return self._snapshot_value("last_active_provider_id", "")

    @property
    def last_attempted_provider(self) -> str:
        return self._snapshot_value("last_attempted_provider_id", "")

    @property
    def last_fallback_provider(self) -> str:
        snapshot = self._snapshot()
        return snapshot.fallback_provider_id if snapshot and snapshot.fallback_used else ""

    @property
    def last_fallback_status(self) -> str:
        snapshot = self._snapshot()
        return "used" if snapshot and snapshot.fallback_used else "none"

    @property
    def last_error_category(self) -> str:
        return self._snapshot_value("last_error_category", "")

    @property
    def last_duration_ms(self) -> float:
        return self._snapshot_value("last_latency_ms", 0.0)

    @property
    def last_generation_latency_ms(self) -> float:
        return self._snapshot_value("last_generation_latency_ms", 0.0)

    @property
    def last_fallback_latency_ms(self) -> float:
        return self._snapshot_value("last_fallback_latency_ms", 0.0)

    @property
    def last_retry_count(self) -> int:
        return self._snapshot_value("retry_count", 0)

    def _snapshot(self):
        return self._diagnostics.snapshot() if self._diagnostics is not None else None

    def _snapshot_value(self, name: str, default):
        snapshot = self._snapshot()
        return getattr(snapshot, name, default) if snapshot is not None else default

    def _require_generation(self) -> CompanionGenerationService:
        if self._generation is None:
            from fibi.services.providers.factory import build_compatibility_provider_subsystem

            build_compatibility_provider_subsystem(self)
        if self._generation is None:  # pragma: no cover - factory contract guard
            raise RuntimeError("provider compatibility subsystem could not be attached")
        return self._generation

    @staticmethod
    def _warn(member: str, replacement: str) -> None:
        warnings.warn(
            f"ModelRouter.{member} is deprecated; use {replacement}",
            DeprecationWarning,
            stacklevel=3,
        )
