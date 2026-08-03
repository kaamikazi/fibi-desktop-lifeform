"""Gemini adapter hiding Google SDK and legacy result details."""

from __future__ import annotations

from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.engines.types import Observation
from fibi.providers.gemini_provider import GeminiProvider
from fibi.services.providers.errors import normalize_error_category
from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderConfigurationStatus,
    ProviderErrorCategory,
    ProviderHealth,
    ProviderModelMetadata,
)


class GeminiLanguageProvider:
    provider_id = "gemini"
    display_name = "Gemini"

    def __init__(
        self,
        provider: GeminiProvider,
        sanitizer: CloudContextSanitizer | None = None,
    ) -> None:
        self.provider = provider
        self.sanitizer = sanitizer or CloudContextSanitizer()

    def configuration_status(self) -> ProviderConfigurationStatus:
        status = self.provider.status()
        configured = bool(status.configured and status.sdk_available)
        detail = "configured" if configured else (
            "API key missing" if not status.configured else "google-genai SDK unavailable"
        )
        return ProviderConfigurationStatus(
            self.provider_id,
            configured,
            status.sdk_available,
            status.model,
            detail,
        )

    def model_metadata(self) -> ProviderModelMetadata:
        configuration = self.configuration_status()
        capabilities = ("text_generation", "streaming", "search_grounding", "context_preview")
        enabled = ["text_generation"]
        if self.provider.config.streaming:
            enabled.append("streaming")
        if self.provider.config.google_search:
            enabled.append("search_grounding")
        if self.provider.config.context_preview:
            enabled.append("context_preview")
        return ProviderModelMetadata(
            provider_id=self.provider_id,
            model_id=configuration.model_id,
            display_name=self.display_name,
            configured=configuration.configured,
            available=configuration.configured and configuration.sdk_available,
            capabilities=capabilities,
            enabled_capabilities=tuple(enabled),
            configuration_source="FIBI_GEMINI_MODEL",
            safe_options=(
                ("thinking_level", self.provider.config.thinking_level),
                ("streaming", "on" if self.provider.config.streaming else "off"),
                ("search_grounding", "on" if self.provider.config.google_search else "off"),
                ("context_preview", "on" if self.provider.config.context_preview else "off"),
            ),
        )
    def health(self) -> ProviderHealth:
        status = self.provider.status()
        category = (
            normalize_error_category(status.last_error_category, status.last_error)
            if status.last_error_category or status.last_error
            else None
        )
        return ProviderHealth(
            self.provider_id,
            status.health_state,
            status.health_state in {"healthy", "unknown"} and status.configured and status.sdk_available,
            category,
            status.retry_after_seconds,
        )

    def cached_health(self) -> ProviderHealth:
        return self.health()

    def reset_health(self) -> bool:
        return self.provider.reset_transient_health()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.purpose == "provider_test":
            reply = self.provider.test_connection()
            search_used = False
        else:
            observation = Observation("", request.time_of_day)
            prompt = self.sanitizer.build_prompt(
                request.user_text,
                request.mood,
                request.context_level,
                list(request.approved_context_summaries),
                observation,
                request.response_instruction,
            )
            reply = self.provider.generate_reply(
                prompt,
                use_google_search=request.search_grounding_allowed,
            )
            search_used = bool(
                request.search_grounding_allowed
                and self.provider.config.google_search
                and reply.text.strip()
                and not reply.error
            )
        if reply.error:
            category = (
                ProviderErrorCategory.EMPTY_RESPONSE
                if "empty" in str(reply.error or "").lower()
                else normalize_error_category(reply.error_category, reply.error)
            )
            if not self.provider.is_configured():
                category = ProviderErrorCategory.NOT_CONFIGURED
            return GenerationResult(
                False,
                "",
                self.provider_id,
                self.provider_id,
                "",
                reply.model,
                reply.duration_ms,
                category,
                reply.error,
                reply.retry_count,
                search_grounding_used=False,
                safe_metadata=(("attempt_count", str(reply.attempt_count)),),
            )
        if not reply.text.strip():
            return GenerationResult(
                False,
                "",
                self.provider_id,
                self.provider_id,
                "",
                reply.model,
                reply.duration_ms,
                ProviderErrorCategory.EMPTY_RESPONSE,
                "Gemini returned an empty response",
                reply.retry_count,
            )
        return GenerationResult(
            True,
            reply.text,
            self.provider_id,
            self.provider_id,
            self.provider_id,
            reply.model,
            reply.duration_ms,
            retry_count=reply.retry_count,
            search_grounding_used=search_used,
            safe_metadata=(("attempt_count", str(reply.attempt_count)),),
        )
