"""Optional, resilient Google Gemini language provider.

The SDK is imported lazily and every request receives sanitized text from the
router. Provider health is session-only: no prompt, response, or credential is
stored in health diagnostics.
"""

from __future__ import annotations

import importlib.util
import logging
import random
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
Clock = Callable[[], float]
Sleeper = Callable[[float], None]
Jitter = Callable[[float, float], float]

RETRYABLE_CATEGORIES = {"temporary_unavailable", "network_error"}
TRANSIENT_STATES = {"degraded", "rate_limited"}
PREFERRED_MODEL = "gemini-3.1-flash-lite"


class ProviderError(RuntimeError):
    """Normalized provider failure safe to expose in diagnostics."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        retry_after_seconds: int = 0,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.safe_message = message
        self.retry_after_seconds = max(0, retry_after_seconds)


class GeminiProvider(CloudProviderBase):
    """Bounded Gemini text provider with temporary health recovery."""

    name = "gemini"
    max_tokens = 80
    supports_streaming = True
    privacy_level = "minimal"
    max_attempts = 2

    def __init__(
        self,
        config: GeminiProviderConfig | None = None,
        *,
        client_factory: ClientFactory | None = None,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = time.sleep,
        jitter: Jitter = random.uniform,
        cooldown_seconds: float = 25.0,
    ) -> None:
        self.config = config or GeminiProviderConfig.from_env()
        self.timeout_seconds = self.config.timeout_seconds
        self._client_factory = client_factory
        self._client: Any | None = None
        self._model_cache: tuple[str, ...] | None = None
        self._candidate_cache: tuple[str, ...] | None = None
        self._selected_model = ""
        self._clock = clock
        self._sleeper = sleeper
        self._jitter = jitter
        self._cooldown_seconds = max(1.0, cooldown_seconds)
        self._cooldown_until = 0.0
        self._authentication_blocked = False
        self._health_state = "unknown"
        self.last_error: str | None = None
        self.last_error_category = ""
        self.last_usage = ProviderUsage()
        self.last_retry_count = 0
        self.last_attempt_count = 0

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def sdk_available(self) -> bool:
        return self._client_factory is not None or importlib.util.find_spec("google.genai") is not None

    def is_available(self) -> bool:
        return self.is_configured() and self.sdk_available() and not self._authentication_blocked

    def status(self, *, selected: bool = False) -> ProviderStatus:
        state = self._current_health_state()
        retry_after = self.retry_after_seconds()
        return ProviderStatus(
            provider=self.name,
            selected=selected,
            configured=self.is_configured(),
            sdk_available=self.sdk_available(),
            model=self._selected_model or self.config.model or "auto-discover",
            availability=state,
            fallback_enabled=self.config.fallback_to_ollama,
            streaming_enabled=self.config.streaming,
            context_preview_enabled=self.config.context_preview,
            last_error=self.last_error or "",
            health_state=state,
            last_error_category=self.last_error_category,
            retry_after_seconds=retry_after,
            last_retry_count=self.last_retry_count,
            candidate_models=self._candidate_cache or (),
            google_search_enabled=self.config.google_search,
            thinking_level=self.config.thinking_level,
        )

    def retry_after_seconds(self) -> int:
        return max(0, int(round(self._cooldown_until - self._clock())))

    def reset_transient_health(self) -> bool:
        """Clear cooldown state without hiding authentication failures."""

        if self._authentication_blocked:
            return False
        self._cooldown_until = 0.0
        if self._health_state in TRANSIENT_STATES:
            self._health_state = "unknown"
            self.last_error = None
            self.last_error_category = ""
        return True

    def list_models(self, *, refresh: bool = False) -> list[str]:
        """Return cached compatible text-generation model IDs."""

        if self._model_cache is not None and not refresh:
            return list(self._model_cache)
        if not self.is_configured():
            raise ProviderError("authentication_error", "GEMINI_API_KEY is not configured")
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
        self._candidate_cache = None
        return names

    def model_candidates(self, *, refresh: bool = False) -> list[str]:
        """Rank a small, stable session cache of text-generation candidates."""

        if self._candidate_cache is not None and not refresh:
            return list(self._candidate_cache)
        models = self.list_models(refresh=refresh)
        configured = self._clean_model_name(self.config.model)
        if configured and configured not in models:
            raise ProviderError(
                "model_unavailable",
                f"configured Gemini model is unavailable: {configured}",
            )
        stable = [model for model in models if not self._is_preview_model(model)]
        flash = sorted(
            (model for model in stable if "flash" in model.lower()),
            key=self._model_sort_key,
            reverse=True,
        )
        other = sorted(
            (model for model in stable if model not in flash),
            key=self._model_sort_key,
            reverse=True,
        )
        ranked = ([configured] if configured else []) + flash + other
        if not configured and PREFERRED_MODEL in ranked:
            ranked.remove(PREFERRED_MODEL)
            ranked.insert(0, PREFERRED_MODEL)
        candidates = tuple(dict.fromkeys(model for model in ranked if model))[:3]
        if not candidates:
            raise ProviderError(
                "model_unavailable",
                "no stable Gemini text-generation model is available",
            )
        self._candidate_cache = candidates
        return list(candidates)

    def select_model(self, *, refresh: bool = False) -> str:
        self._selected_model = self.model_candidates(refresh=refresh)[0]
        return self._selected_model

    def generate_reply(
        self,
        context: str,
        *,
        bypass_health: bool = False,
        max_attempts: int | None = None,
        use_google_search: bool = False,
    ) -> CloudProviderReply:
        """Generate with at most two attempts and no prompt logging.

        The one retry uses the next stable Flash candidate when available;
        otherwise it retries the selected model. Total attempts remain two.
        """

        started = time.perf_counter()
        self.last_retry_count = 0
        self.last_attempt_count = 0
        blocked = self._preflight_error(bypass_health=bypass_health)
        if blocked is not None:
            return self._failure(started, blocked, update_health=False)
        try:
            candidates = self.model_candidates()
        except ProviderError as error:
            self._record_failure(error)
            return self._failure(started, error, update_health=False)

        terminal_error: ProviderError | None = None
        attempt_limit = min(self.max_attempts, max(1, max_attempts or self.max_attempts))
        for attempt in range(1, attempt_limit + 1):
            model = candidates[min(attempt - 1, len(candidates) - 1)]
            self._selected_model = model
            self.last_attempt_count = attempt
            attempt_started = time.perf_counter()
            LOGGER.info("gemini_attempt attempt=%d model=%s", attempt, model)
            try:
                text, response = self._generate_once(
                    model,
                    context,
                    use_google_search=use_google_search,
                )
                if not text.strip():
                    raise ProviderError("malformed_response", "Gemini returned an empty response")
                self.last_usage = self._usage_from_response(response)
                self._record_success()
                duration_ms = (time.perf_counter() - started) * 1000
                LOGGER.info(
                    "gemini_generation_complete attempt=%d model=%s duration_ms=%.1f",
                    attempt,
                    model,
                    duration_ms,
                )
                return CloudProviderReply(
                    text,
                    model,
                    duration_ms,
                    retry_count=self.last_retry_count,
                    attempt_count=self.last_attempt_count,
                )
            except ProviderError as error:
                terminal_error = error
            except Exception as error:
                terminal_error = self._normalize_error(error)

            attempt_duration_ms = (time.perf_counter() - attempt_started) * 1000
            LOGGER.warning(
                "gemini_attempt_failed attempt=%d model=%s category=%s duration_ms=%.1f",
                attempt,
                model,
                terminal_error.category,
                attempt_duration_ms,
            )
            if attempt >= attempt_limit or terminal_error.category not in RETRYABLE_CATEGORIES:
                break
            self.last_retry_count += 1
            self._sleeper(self._jitter(0.5, 1.5))

        terminal_error = terminal_error or ProviderError(
            "unknown_provider_error",
            "Gemini request failed",
        )
        self._record_failure(terminal_error)
        return self._failure(started, terminal_error, update_health=False)

    def test_connection(self) -> CloudProviderReply:
        """Run one explicit context-free probe that bypasses transient cooldown."""

        return self.generate_reply(
            "Reply with GEMINI_PROVIDER_OK.",
            bypass_health=True,
            max_attempts=1,
        )

    def benchmark(self) -> ProviderBenchmarkResult:
        result = self.test_connection()
        return ProviderBenchmarkResult(
            provider=self.name,
            model=result.model,
            latency_ms=result.duration_ms,
            ok=bool(result.text and not result.error),
            error_category=result.error_category,
        )

    def _preflight_error(self, *, bypass_health: bool) -> ProviderError | None:
        if not self.is_configured():
            self._health_state = "configuration_error"
            return ProviderError("authentication_error", "GEMINI_API_KEY is not configured")
        if not self.sdk_available():
            self._health_state = "configuration_error"
            return ProviderError("model_unavailable", "google-genai SDK is not installed")
        if self._authentication_blocked and not bypass_health:
            return ProviderError(
                "authentication_error",
                "Gemini authentication must be tested after configuration changes",
            )
        if not bypass_health and self.retry_after_seconds() > 0:
            category = self.last_error_category or "temporary_unavailable"
            message = (
                "Gemini is rate limited; try again shortly"
                if self._health_state == "rate_limited"
                else "Gemini is temporarily unavailable; retry cooldown is active"
            )
            return ProviderError(
                category,
                message,
                retry_after_seconds=self.retry_after_seconds(),
            )
        return None

    def _generate_once(
        self,
        model: str,
        context: str,
        *,
        use_google_search: bool,
    ) -> tuple[str, Any | None]:
        models_api = self._get_client().models
        config_values: dict[str, Any] = {
            "temperature": 0.8,
            "top_p": 0.9,
            "max_output_tokens": self.max_tokens,
            "thinking_config": {"thinking_level": self.config.thinking_level},
        }
        if use_google_search and self.config.google_search:
            config_values["tools"] = [{"google_search": {}}]
        config = self._typed_generation_config(config_values)
        if self.config.streaming:
            chunks = models_api.generate_content_stream(model=model, contents=context, config=config)
            return "".join(str(getattr(chunk, "text", "") or "") for chunk in chunks), None
        response = models_api.generate_content(model=model, contents=context, config=config)
        return str(getattr(response, "text", "") or ""), response

    def _typed_generation_config(self, values: dict[str, Any]) -> Any:
        """Use SDK types in production while keeping injected test clients simple."""

        if self._client_factory is not None:
            return values
        try:
            from google.genai import types
        except ImportError as error:
            raise ProviderError("model_unavailable", "google-genai SDK is not installed") from error
        tools = (
            [types.Tool(google_search=types.GoogleSearch())]
            if "tools" in values
            else None
        )
        return types.GenerateContentConfig(
            temperature=values["temperature"],
            top_p=values["top_p"],
            max_output_tokens=values["max_output_tokens"],
            thinking_config=types.ThinkingConfig(
                thinking_level=self.config.thinking_level,
            ),
            tools=tools,
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
            raise ProviderError("model_unavailable", "google-genai SDK is not installed") from error
        self._client = genai.Client(
            api_key=self.config.api_key,
            http_options=types.HttpOptions(
                timeout=self.config.timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return self._client

    def _record_success(self) -> None:
        self.last_error = None
        self.last_error_category = ""
        self._health_state = "healthy"
        self._cooldown_until = 0.0
        self._authentication_blocked = False

    def _record_failure(self, error: ProviderError) -> None:
        self.last_error = error.safe_message
        self.last_error_category = error.category
        if error.category in {"temporary_unavailable", "network_error", "timeout"}:
            self._health_state = "degraded"
            self._cooldown_until = self._clock() + self._cooldown_seconds
        elif error.category in {"rate_limit_error", "quota_error"}:
            self._health_state = "rate_limited"
            wait = error.retry_after_seconds or 30
            self._cooldown_until = self._clock() + min(300, max(5, wait))
        elif error.category == "authentication_error":
            self._health_state = "configuration_error"
            self._authentication_blocked = True
            self._cooldown_until = 0.0
        elif error.category in {"model_unavailable", "malformed_response"}:
            self._health_state = "unavailable"
            self._cooldown_until = 0.0
        else:
            self._health_state = "unknown"
            self._cooldown_until = 0.0

    def _failure(
        self,
        started: float,
        error: ProviderError,
        *,
        update_health: bool,
    ) -> CloudProviderReply:
        if update_health:
            self._record_failure(error)
        duration_ms = (time.perf_counter() - started) * 1000
        self.last_error = error.safe_message
        self.last_error_category = error.category
        LOGGER.warning(
            "gemini_generation_failed category=%s duration_ms=%.1f model=%s attempts=%d",
            error.category,
            duration_ms,
            self._selected_model or self.config.model or "gemini-auto",
            self.last_attempt_count,
        )
        return CloudProviderReply(
            "",
            self._selected_model or self.config.model or "gemini-auto",
            duration_ms,
            error.safe_message,
            error.category,
            self.last_retry_count,
            self.last_attempt_count,
        )

    def _current_health_state(self) -> str:
        if not self.is_configured() or not self.sdk_available() or self._authentication_blocked:
            return "configuration_error"
        if self.retry_after_seconds() <= 0 and self._health_state in TRANSIENT_STATES:
            self._health_state = "unknown"
            self._cooldown_until = 0.0
        return self._health_state

    @staticmethod
    def _normalize_error(error: Exception) -> ProviderError:
        if isinstance(error, ProviderError):
            return error
        response = getattr(error, "response", None)
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code is None and response is not None:
            code = getattr(response, "status_code", None)
        try:
            code = int(code) if code is not None else None
        except (TypeError, ValueError):
            code = None
        name = type(error).__name__.lower()
        message = str(getattr(error, "message", "") or error).lower()
        retry_after = GeminiProvider._retry_after_seconds(response)
        if code in {401, 403} or any(token in message for token in ("invalid api key", "permission denied")):
            return ProviderError("authentication_error", "Gemini authentication or access failed")
        if code == 429:
            category = "quota_error" if "quota" in message else "rate_limit_error"
            return ProviderError(
                category,
                "Gemini quota or rate limit was reached",
                retry_after_seconds=retry_after,
            )
        if code in {500, 502, 503, 504}:
            return ProviderError("temporary_unavailable", "Gemini is temporarily unavailable")
        if code == 404 or any(token in message for token in ("model not found", "unsupported model")):
            return ProviderError("model_unavailable", "Gemini model is unavailable")
        if "timeout" in name or "timed out" in message or isinstance(error, TimeoutError):
            return ProviderError("timeout", "Gemini request timed out")
        if any(token in name or token in message for token in ("connect", "network", "dns", "disconnect")):
            return ProviderError("network_error", "Gemini network request failed")
        if code == 400 or any(token in message for token in ("malformed", "invalid argument")):
            return ProviderError("malformed_response", "Gemini request or response was malformed")
        return ProviderError("unknown_provider_error", "Gemini request failed")

    @staticmethod
    def _retry_after_seconds(response: Any | None) -> int:
        headers = getattr(response, "headers", {}) if response is not None else {}
        value = headers.get("Retry-After", headers.get("retry-after", "")) if hasattr(headers, "get") else ""
        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            return 0

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
        return str(name or "").strip().removeprefix("models/")

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
