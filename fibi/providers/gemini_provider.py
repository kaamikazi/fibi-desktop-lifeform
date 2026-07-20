"""Optional Google Gemini language provider.

The official SDK is imported only when Gemini is explicitly used. The provider
accepts sanitized text, performs at most one generation call, and returns safe
diagnostics without logging prompts, responses, or credentials.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import time
from collections.abc import Callable, Iterable
from typing import Any

from fibi.engines.cloud_provider_base import CloudProviderBase, CloudProviderReply
from fibi.providers.types import (
    GeminiProviderConfig,
    ProviderBenchmarkResult,
    ProviderStatus,
    ProviderUsage,
)

LOGGER = logging.getLogger(__name__)
ClientFactory = Callable[[str, int], Any]


class ProviderError(RuntimeError):
    """Normalized provider failure safe to show without credential leakage."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.safe_message = message


class GeminiProvider(CloudProviderBase):
    """One-request Gemini text provider with session-only model discovery."""

    name = "gemini"
    max_tokens = 80
    supports_streaming = True
    privacy_level = "minimal"

    def __init__(
        self,
        config: GeminiProviderConfig | None = None,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.config = config or GeminiProviderConfig.from_env()
        self.timeout_seconds = self.config.timeout_seconds
        self._client_factory = client_factory
        self._client: Any | None = None
        self._model_cache: tuple[str, ...] | None = None
        self._selected_model = ""
        self.last_error: str | None = None
        self.last_error_category = ""
        self.last_usage = ProviderUsage()
        self._last_success: bool | None = None

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def sdk_available(self) -> bool:
        return self._client_factory is not None or importlib.util.find_spec("google.genai") is not None

    def is_available(self) -> bool:
        return self.is_configured() and self.sdk_available()

    def status(self, *, selected: bool = False) -> ProviderStatus:
        if not self.is_configured():
            availability = "not configured"
        elif not self.sdk_available():
            availability = "SDK unavailable"
        elif self._last_success is True:
            availability = "online"
        elif self._last_success is False:
            availability = "offline"
        else:
            availability = "unknown"
        return ProviderStatus(
            provider=self.name,
            selected=selected,
            configured=self.is_configured(),
            sdk_available=self.sdk_available(),
            model=self._selected_model or self.config.model or "auto-discover",
            availability=availability,
            fallback_enabled=self.config.fallback_to_ollama,
            streaming_enabled=self.config.streaming,
            context_preview_enabled=self.config.context_preview,
            last_error=self.last_error or "",
        )

    def list_models(self, *, refresh: bool = False) -> list[str]:
        """Return safe text-generation model IDs available to this API key."""

        if self._model_cache is not None and not refresh:
            return list(self._model_cache)
        if not self.is_configured():
            raise ProviderError("missing_key", "GEMINI_API_KEY is not configured")
        try:
            models = list(self._get_client().models.list())
        except Exception as error:
            raise self._normalize_error(error) from None
        names = sorted(
            {
                self._clean_model_name(getattr(model, "name", ""))
                for model in models
                if self._supports_text_generation(model)
            }
            - {""}
        )
        self._model_cache = tuple(names)
        return names

    def select_model(self, *, refresh: bool = False) -> str:
        models = self.list_models(refresh=refresh)
        configured = self._clean_model_name(self.config.model)
        if configured:
            if configured not in models:
                raise ProviderError("unavailable_model", f"configured Gemini model is unavailable: {configured}")
            self._selected_model = configured
            return configured
        stable_flash = [
            model for model in models
            if "flash" in model.lower() and not self._is_preview_model(model)
        ]
        stable_generation = [model for model in models if not self._is_preview_model(model)]
        candidates = stable_flash or stable_generation
        if not candidates:
            raise ProviderError("unavailable_model", "no stable Gemini text-generation model is available")
        self._selected_model = max(candidates, key=self._model_sort_key)
        return self._selected_model

    def generate_reply(self, context: str) -> CloudProviderReply:
        """Generate once from an already-sanitized context."""

        started = time.perf_counter()
        if not self.is_configured():
            return self._failure(started, ProviderError("missing_key", "GEMINI_API_KEY is not configured"))
        if not self.sdk_available():
            return self._failure(started, ProviderError("sdk_unavailable", "google-genai SDK is not installed"))
        try:
            model = self.select_model()
            models_api = self._get_client().models
            config = {
                "temperature": 0.8,
                "top_p": 0.9,
                "max_output_tokens": self.max_tokens,
            }
            if self.config.streaming:
                chunks = models_api.generate_content_stream(model=model, contents=context, config=config)
                text = "".join(str(getattr(chunk, "text", "") or "") for chunk in chunks)
                response = None
            else:
                response = models_api.generate_content(model=model, contents=context, config=config)
                text = str(getattr(response, "text", "") or "")
            if not text.strip():
                raise ProviderError("malformed_response", "Gemini returned an empty response")
            self.last_usage = self._usage_from_response(response)
            self.last_error = None
            self.last_error_category = ""
            self._last_success = True
            duration_ms = (time.perf_counter() - started) * 1000
            LOGGER.info("gemini_generation_complete model=%s duration_ms=%.1f", model, duration_ms)
            return CloudProviderReply(text, model, duration_ms)
        except ProviderError as error:
            return self._failure(started, error)
        except Exception as error:
            return self._failure(started, self._normalize_error(error))

    def test_connection(self) -> CloudProviderReply:
        """Run the explicit, context-free provider test command."""

        return self.generate_reply("Reply with GEMINI_PROVIDER_OK.")

    def benchmark(self) -> ProviderBenchmarkResult:
        result = self.test_connection()
        return ProviderBenchmarkResult(
            provider=self.name,
            model=result.model,
            latency_ms=result.duration_ms,
            ok=bool(result.text and not result.error),
            error_category=self.last_error_category,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory(self.config.api_key, self.config.timeout_seconds)
            return self._client
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise ProviderError("sdk_unavailable", "google-genai SDK is not installed") from error
        self._client = genai.Client(
            api_key=self.config.api_key,
            http_options=types.HttpOptions(
                timeout=self.config.timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return self._client

    def _failure(self, started: float, error: ProviderError) -> CloudProviderReply:
        duration_ms = (time.perf_counter() - started) * 1000
        self.last_error = error.safe_message
        self.last_error_category = error.category
        self._last_success = False
        LOGGER.warning(
            "gemini_generation_failed category=%s duration_ms=%.1f",
            error.category,
            duration_ms,
        )
        return CloudProviderReply(
            "",
            self._selected_model or self.config.model or "gemini-auto",
            duration_ms,
            error.safe_message,
        )

    @staticmethod
    def _normalize_error(error: Exception) -> ProviderError:
        if isinstance(error, ProviderError):
            return error
        code = getattr(error, "code", None)
        name = type(error).__name__.lower()
        message = str(getattr(error, "message", "") or error).lower()
        if code in {401, 403}:
            return ProviderError("authentication", "Gemini authentication failed")
        if code == 429:
            return ProviderError("quota", "Gemini quota or rate limit was reached")
        if code == 404:
            return ProviderError("unavailable_model", "Gemini model is unavailable")
        if "timeout" in name or "timed out" in message or isinstance(error, TimeoutError):
            return ProviderError("timeout", "Gemini request timed out")
        if any(token in name or token in message for token in ("connect", "network", "dns")):
            return ProviderError("network", "Gemini network request failed")
        return ProviderError("provider_error", "Gemini request failed")

    @staticmethod
    def _supports_text_generation(model: Any) -> bool:
        actions: Iterable[Any] = (
            getattr(model, "supported_actions", None)
            or getattr(model, "supported_generation_methods", None)
            or ()
        )
        normalized = {str(action).lower() for action in actions}
        if normalized and not any("generate" in action for action in normalized):
            return False
        name = GeminiProvider._clean_model_name(getattr(model, "name", ""))
        lowered = name.lower()
        return bool(name) and not any(
            token in lowered
            for token in ("embedding", "imagen", "veo", "tts", "audio", "image-generation")
        )

    @staticmethod
    def _clean_model_name(name: str) -> str:
        cleaned = str(name or "").strip()
        return cleaned.removeprefix("models/")

    @staticmethod
    def _is_preview_model(name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ("preview", "experimental", "-exp", "latest"))

    @staticmethod
    def _model_sort_key(name: str) -> tuple[tuple[int, ...], int, str]:
        numbers = tuple(int(value) for value in re.findall(r"\d+", name))
        lite_penalty = 0 if "lite" in name.lower() else 1
        return numbers, lite_penalty, name

    @staticmethod
    def _usage_from_response(response: Any | None) -> ProviderUsage:
        metadata = getattr(response, "usage_metadata", None) if response is not None else None
        if metadata is None:
            return ProviderUsage()
        return ProviderUsage(
            prompt_tokens=int(getattr(metadata, "prompt_token_count", 0) or 0),
            response_tokens=int(getattr(metadata, "candidates_token_count", 0) or 0),
            total_tokens=int(getattr(metadata, "total_token_count", 0) or 0),
        )
