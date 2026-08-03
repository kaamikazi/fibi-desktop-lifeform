"""Build the provider subsystem around existing provider implementations."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_router import ModelRouter
from fibi.providers.gemini_provider import GeminiProvider
from fibi.services.providers.adapters.gemini import GeminiLanguageProvider
from fibi.services.providers.adapters.ollama import OllamaLanguageProvider
from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.generation import CompanionGenerationService
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService


@dataclass(slots=True)
class ProviderSubsystem:
    registry: ProviderRegistry
    selection: ProviderSelectionService
    generation: CompanionGenerationService
    diagnostics: ProviderDiagnostics
    legacy_router: ModelRouter


class _CompatibilitySettingsStore:
    """Non-persisting settings used only by deprecated direct router callers."""

    def __init__(self, provider_id: str, fallback_enabled: bool) -> None:
        self.settings = SimpleNamespace(
            language_provider=provider_id,
            automatic_provider_fallback=fallback_enabled,
        )

    def update(self, **values: Any):
        for name, value in values.items():
            setattr(self.settings, name, value)
        return self.settings


def build_provider_subsystem(
    router: ModelRouter,
    settings: AppSettingsEngine | _CompatibilitySettingsStore,
    *,
    initial_provider_id: str | None = None,
    initial_fallback_enabled: bool | None = None,
) -> ProviderSubsystem:
    ollama = router.ollama or ModelEngine()
    gemini = router.gemini or GeminiProvider()
    sanitizer = router.sanitizer or CloudContextSanitizer()
    router.bind_legacy_dependencies(ollama=ollama, gemini=gemini, sanitizer=sanitizer)
    registry = ProviderRegistry(
        (
            OllamaLanguageProvider(ollama),
            GeminiLanguageProvider(gemini, sanitizer),
        )
    )
    selection = ProviderSelectionService(
        registry,
        settings,
        initial_provider_id=initial_provider_id,
    )
    selected = selection.get_selected_provider()
    if selected.provider_id == "gemini":
        registry.reset_health(selected.provider_id)
    diagnostics = ProviderDiagnostics(
        selected.provider_id,
        selected.configuration_status().configured,
    )

    def sync_selection_diagnostics(provider_id: str) -> None:
        if provider_id == "gemini":
            registry.reset_health(provider_id)
        configuration = registry.get(provider_id).configuration_status()
        health = registry.health_snapshot(provider_id)
        diagnostics.selection_changed(provider_id, configuration.configured, health.state)

    selection.add_listener(sync_selection_diagnostics)

    generation = CompanionGenerationService(
        registry,
        selection,
        diagnostics,
        fallback_enabled=(
            settings.settings.automatic_provider_fallback
            if initial_fallback_enabled is None
            else initial_fallback_enabled
        ),
        fallback_provider_id="ollama",
    )
    diagnostics.fallback_changed(generation.fallback_enabled, generation.fallback_provider_id)
    router.attach(registry, selection, generation, diagnostics)
    return ProviderSubsystem(registry, selection, generation, diagnostics, router)


def build_compatibility_provider_subsystem(router: ModelRouter) -> ProviderSubsystem:
    """Attach old direct callers without touching persisted application settings."""

    settings = _CompatibilitySettingsStore(
        router.selected_provider(),
        router.automatic_fallback_enabled,
    )
    return build_provider_subsystem(
        router,
        settings,
        initial_provider_id=router.selected_provider(),
        initial_fallback_enabled=router.automatic_fallback_enabled,
    )
