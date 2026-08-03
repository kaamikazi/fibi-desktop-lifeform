"""Ollama adapter hiding HTTP and legacy result details."""

from __future__ import annotations

from fibi.engines.model_engine import ModelEngine
from fibi.services.providers.errors import normalize_error_category
from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderConfigurationStatus,
    ProviderErrorCategory,
    ProviderHealth,
    ProviderModelMetadata,
)
from fibi.settings import OLLAMA_MODEL


class OllamaLanguageProvider:
    provider_id = "ollama"
    display_name = "Ollama"

    def __init__(self, engine: ModelEngine) -> None:
        self.engine = engine
        self._last_health = ProviderHealth(self.provider_id, "unknown", False)

    def configuration_status(self) -> ProviderConfigurationStatus:
        configured = bool(OLLAMA_MODEL.strip())
        return ProviderConfigurationStatus(
            self.provider_id,
            configured,
            True,
            OLLAMA_MODEL,
            "configured locally" if configured else "model name missing",
        )

    def model_metadata(self) -> ProviderModelMetadata:
        configuration = self.configuration_status()
        return ProviderModelMetadata(
            provider_id=self.provider_id,
            model_id=configuration.model_id,
            display_name=self.display_name,
            configured=configuration.configured,
            available=configuration.configured,
            capabilities=("text_generation",),
            enabled_capabilities=("text_generation",),
            configuration_source="OLLAMA_MODEL",
        )

    def cached_health(self) -> ProviderHealth:
        return self._last_health

    def health(self) -> ProviderHealth:
        try:
            available = bool(self.engine.health_check())
            self._last_health = ProviderHealth(
                self.provider_id,
                "healthy" if available else "unavailable",
                available,
                None if available else ProviderErrorCategory.NETWORK_ERROR,
            )
        except Exception:
            self._last_health = ProviderHealth(
                self.provider_id,
                "unavailable",
                False,
                ProviderErrorCategory.NETWORK_ERROR,
            )
        return self._last_health

    def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt = "Reply with OLLAMA_PROVIDER_OK." if request.purpose == "provider_test" else request.prepared_prompt
        result = self.engine.generate(prompt)
        latency_ms = result.duration_seconds * 1000
        if result.error:
            category = normalize_error_category("", result.error)
            return GenerationResult(
                False,
                "",
                self.provider_id,
                self.provider_id,
                "",
                result.model,
                latency_ms,
                category,
                result.error,
            )
        if not result.raw_text.strip():
            return GenerationResult(
                False,
                "",
                self.provider_id,
                self.provider_id,
                "",
                result.model,
                latency_ms,
                ProviderErrorCategory.EMPTY_RESPONSE,
                "Ollama returned an empty response",
            )
        return GenerationResult(
            True,
            result.raw_text,
            self.provider_id,
            self.provider_id,
            self.provider_id,
            result.model,
            latency_ms,
        )
