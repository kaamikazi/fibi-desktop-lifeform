"""Provider-neutral text generation use case."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.errors import ProviderErrorPresenter
from fibi.services.providers.models import GenerationRequest, GenerationResult, ProviderErrorCategory
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService

LOGGER = logging.getLogger(__name__)
ResultObserver = Callable[[GenerationResult], None]

FALLBACK_ELIGIBLE_ERRORS = frozenset(
    {
        ProviderErrorCategory.TIMEOUT,
        ProviderErrorCategory.NETWORK_ERROR,
        ProviderErrorCategory.TEMPORARY_UNAVAILABLE,
        ProviderErrorCategory.PROVIDER_INTERNAL_ERROR,
    }
)


class CompanionGenerationService:
    """Generate with the manually selected provider and optional explicit fallback."""

    def __init__(
        self,
        registry: ProviderRegistry,
        selection: ProviderSelectionService,
        diagnostics: ProviderDiagnostics,
        *,
        fallback_enabled: bool = False,
        fallback_provider_id: str = "ollama",
        error_presenter: ProviderErrorPresenter | None = None,
        result_observer: ResultObserver | None = None,
    ) -> None:
        self.registry = registry
        self.selection = selection
        self.diagnostics = diagnostics
        self.fallback_enabled = bool(fallback_enabled)
        self.fallback_provider_id = fallback_provider_id
        self.error_presenter = error_presenter or ProviderErrorPresenter()
        self._result_observer = result_observer

    def set_fallback(self, enabled: bool, provider_id: str = "ollama") -> None:
        if provider_id:
            self.registry.get(provider_id)
            self.fallback_provider_id = provider_id
        self.fallback_enabled = bool(enabled)

    def generate(self, request: GenerationRequest, *, allow_fallback: bool | None = None) -> GenerationResult:
        selected = self.selection.get_selected_provider()
        selected_id = selected.provider_id
        configuration = selected.configuration_status()
        if not configuration.configured:
            result = GenerationResult(
                False,
                "",
                selected_id,
                selected_id,
                "",
                configuration.model_id,
                0.0,
                ProviderErrorCategory.NOT_CONFIGURED,
                configuration.detail or "selected provider is not configured",
            )
            return self._record(result)
        if selected_id not in request.allowed_provider_ids:
            result = GenerationResult(
                False,
                "",
                selected_id,
                selected_id,
                "",
                selected.configuration_status().model_id,
                0.0,
                ProviderErrorCategory.INVALID_REQUEST,
                "selected provider is disabled by current privacy settings",
            )
            return self._record(result)

        primary = replace(
            selected.generate(request),
            selected_provider_id=selected_id,
            attempted_provider_id=selected_id,
        )
        fallback_allowed = self.fallback_enabled if allow_fallback is None else bool(allow_fallback)
        if primary.success or not fallback_allowed or primary.error_category not in FALLBACK_ELIGIBLE_ERRORS:
            return self._record(primary)
        if self.fallback_provider_id == selected_id or self.fallback_provider_id not in request.allowed_provider_ids:
            return self._record(primary)

        fallback = self.registry.get(self.fallback_provider_id)
        fallback_result = fallback.generate(request)
        if not fallback_result.success:
            return self._record(primary)
        notice = self.error_presenter.fallback_notice(selected.display_name, fallback.display_name)
        combined = replace(
            fallback_result,
            text=f"{notice} {fallback_result.text}".strip(),
            selected_provider_id=selected_id,
            attempted_provider_id=selected_id,
            latency_ms=primary.latency_ms + fallback_result.latency_ms,
            error_category=primary.error_category,
            fallback_used=True,
            fallback_provider_id=fallback.provider_id,
            fallback_latency_ms=fallback_result.latency_ms,
        )
        return self._record(combined)

    def present_error(self, result: GenerationResult) -> str:
        selected = self.registry.get(result.selected_provider_id)
        return self.error_presenter.present(result, selected.display_name)

    def _record(self, result: GenerationResult) -> GenerationResult:
        configured = self.selection.get_selected_provider().configuration_status().configured
        self.diagnostics.record(
            result,
            selected_configured=configured,
            fallback_enabled=self.fallback_enabled,
            fallback_provider_id=self.fallback_provider_id,
        )
        if self._result_observer is not None:
            self._result_observer(result)
        LOGGER.info(
            "provider_generation selected=%s attempted=%s active=%s success=%s category=%s fallback=%s latency_ms=%.1f",
            result.selected_provider_id,
            result.attempted_provider_id,
            result.provider_id or "none",
            result.success,
            result.error_category.value if result.error_category else "none",
            result.fallback_used,
            result.latency_ms,
        )
        return result
