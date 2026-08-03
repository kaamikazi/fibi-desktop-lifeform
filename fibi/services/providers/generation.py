"""Provider-neutral text generation use case."""

from __future__ import annotations

import logging
from dataclasses import replace

from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.errors import ProviderErrorPresenter
from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderContextPreview,
    ProviderErrorCategory,
)
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService

LOGGER = logging.getLogger(__name__)
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
    ) -> None:
        self.registry = registry
        self.selection = selection
        self.diagnostics = diagnostics
        self.fallback_enabled = bool(fallback_enabled)
        self.fallback_provider_id = fallback_provider_id
        self.error_presenter = error_presenter or ProviderErrorPresenter()

    def set_fallback(self, enabled: bool, provider_id: str = "ollama") -> None:
        if provider_id:
            self.registry.get(provider_id)
            self.fallback_provider_id = provider_id
        self.fallback_enabled = bool(enabled)
        self.diagnostics.fallback_changed(self.fallback_enabled, self.fallback_provider_id)

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

    def generate_with_provider(
        self,
        provider_id: str,
        request: GenerationRequest,
        *,
        record_diagnostics: bool = False,
    ) -> GenerationResult:
        """Run one explicit provider without fallback or persisted selection changes."""

        provider = self.registry.get(provider_id)
        configuration = provider.configuration_status()
        if not configuration.configured:
            result = GenerationResult(
                False,
                "",
                provider.provider_id,
                provider.provider_id,
                "",
                configuration.model_id,
                0.0,
                ProviderErrorCategory.NOT_CONFIGURED,
                configuration.detail or "provider is not configured",
            )
        elif provider.provider_id not in request.allowed_provider_ids:
            result = GenerationResult(
                False,
                "",
                provider.provider_id,
                provider.provider_id,
                "",
                configuration.model_id,
                0.0,
                ProviderErrorCategory.INVALID_REQUEST,
                "provider is disabled for this request",
            )
        else:
            result = replace(
                provider.generate(request),
                selected_provider_id=provider.provider_id,
                attempted_provider_id=provider.provider_id,
                fallback_used=False,
                fallback_provider_id="",
                fallback_latency_ms=0.0,
            )
        if record_diagnostics:
            return self._record(result)
        self._log_result(result, event="provider_explicit_generation")
        return result

    def benchmark(self, provider_ids: tuple[str, ...]) -> tuple[GenerationResult, ...]:
        """Run isolated neutral probes without fallback or selection side effects."""

        results: list[GenerationResult] = []
        for provider_id in provider_ids:
            results.append(
                self.generate_with_provider(
                    provider_id,
                    GenerationRequest(
                        user_text="provider benchmark",
                        prepared_prompt="",
                        allowed_provider_ids=frozenset({provider_id}),
                        purpose="provider_test",
                    ),
                )
            )
        return tuple(results)

    @staticmethod
    def context_preview(
        approved_memory_summaries: list[str] | tuple[str, ...] | None = None,
        *,
        recent_turn_count: int = 0,
    ) -> ProviderContextPreview:
        """Describe approved context categories without retaining their content."""

        return ProviderContextPreview(
            recent_turn_count=max(0, min(4, int(recent_turn_count))),
            approved_memory_summary_count=min(2, len(approved_memory_summaries or ())),
        )

    def present_error(self, result: GenerationResult) -> str:
        selected = self.registry.get(result.selected_provider_id)
        return self.error_presenter.present(result, selected.display_name)

    def _record(self, result: GenerationResult) -> GenerationResult:
        configured = self.selection.get_selected_provider().configuration_status().configured
        health = self.registry.health_snapshot(result.attempted_provider_id or result.selected_provider_id)
        health_state = "healthy" if result.success else health.state
        if not result.success and health_state == "unknown":
            health_state = "configuration_error" if result.error_category == ProviderErrorCategory.NOT_CONFIGURED else "degraded"
        self.diagnostics.record(
            result,
            selected_configured=configured,
            fallback_enabled=self.fallback_enabled,
            fallback_provider_id=self.fallback_provider_id,
            health_state=health_state,
            retry_after_seconds=health.retry_after_seconds,
        )
        self._log_result(result, event="provider_generation")
        return result

    @staticmethod
    def _log_result(result: GenerationResult, *, event: str) -> None:
        LOGGER.info(
            "%s selected=%s attempted=%s active=%s success=%s category=%s fallback=%s latency_ms=%.1f",
            event,
            result.selected_provider_id,
            result.attempted_provider_id,
            result.provider_id or "none",
            result.success,
            result.error_category.value if result.error_category else "none",
            result.fallback_used,
            result.latency_ms,
        )
