"""Build the provider subsystem around existing provider implementations."""

from __future__ import annotations

from dataclasses import dataclass

from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.model_router import ModelRouter
from fibi.services.providers.adapters.gemini import GeminiLanguageProvider
from fibi.services.providers.adapters.ollama import OllamaLanguageProvider
from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.generation import CompanionGenerationService
from fibi.services.providers.models import GenerationResult
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService


@dataclass(slots=True)
class ProviderSubsystem:
    registry: ProviderRegistry
    selection: ProviderSelectionService
    generation: CompanionGenerationService
    diagnostics: ProviderDiagnostics
    legacy_router: ModelRouter


def build_provider_subsystem(
    router: ModelRouter,
    settings: AppSettingsEngine,
    *,
    initial_provider_id: str | None = None,
    initial_fallback_enabled: bool | None = None,
) -> ProviderSubsystem:
    registry = ProviderRegistry(
        (
            OllamaLanguageProvider(router.ollama),
            GeminiLanguageProvider(router.gemini, router.sanitizer),
        )
    )
    selection = ProviderSelectionService(
        registry,
        settings,
        initial_provider_id=initial_provider_id,
        on_change=router.set_mode,
    )
    selected = selection.get_selected_provider()
    diagnostics = ProviderDiagnostics(
        selected.provider_id,
        selected.configuration_status().configured,
    )

    def sync_selection_diagnostics(provider_id: str) -> None:
        configuration = registry.get(provider_id).configuration_status()
        diagnostics.selection_changed(provider_id, configuration.configured)

    selection.add_listener(sync_selection_diagnostics)

    def mirror(result: GenerationResult) -> None:
        router.last_attempted_provider = result.attempted_provider_id
        router.last_provider_used = result.provider_id if result.success else ""
        router.last_fallback_provider = result.fallback_provider_id
        router.last_fallback_status = "used" if result.fallback_used else "none"
        router.last_error_category = result.error_category.value if result.error_category else ""
        router.last_duration_ms = result.latency_ms
        router.last_generation_latency_ms = result.latency_ms - result.fallback_latency_ms
        router.last_fallback_latency_ms = result.fallback_latency_ms
        router.last_retry_count = result.retry_count

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
        result_observer=mirror,
    )
    router.set_automatic_fallback(generation.fallback_enabled)
    return ProviderSubsystem(registry, selection, generation, diagnostics, router)
