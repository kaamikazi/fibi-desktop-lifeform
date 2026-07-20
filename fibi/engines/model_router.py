"""Fast provider router for Fibi model calls."""

from __future__ import annotations

import random
import time

from fibi.brain.cleanup import clean_response
from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.engines.model_engine import ModelEngine
from fibi.engines.nvidia_model_engine import NvidiaModelEngine
from fibi.engines.openai_compatible_provider import OpenAICompatibleProvider
from fibi.engines.types import ModelRouterResult, Observation, PrivacySettings
from fibi.providers.gemini_provider import GeminiProvider
from fibi.providers.types import CloudContextPreview
from fibi.settings import CLOUD_PROVIDER

ROUTER_FALLBACKS = [
    "No language model is available right now.",
    "The model provider is unavailable. Try again in a moment.",
    "Local mode is active, so explainy brain is unavailable.",
]


class ModelRouter:
    """Choose local, optional NVIDIA, optional Ollama, then fallback."""

    def __init__(
        self,
        ollama: ModelEngine | None = None,
        nvidia: NvidiaModelEngine | None = None,
        generic_cloud: OpenAICompatibleProvider | None = None,
        gemini: GeminiProvider | None = None,
        sanitizer: CloudContextSanitizer | None = None,
    ) -> None:
        self.ollama = ollama or ModelEngine()
        self.nvidia = nvidia or NvidiaModelEngine()
        self.generic_cloud = generic_cloud or OpenAICompatibleProvider()
        self.gemini = gemini or GeminiProvider()
        self.sanitizer = sanitizer or CloudContextSanitizer()
        configured_mode = self.gemini.config.selected_provider
        self.mode = configured_mode if configured_mode == "gemini" else "auto"
        self.last_provider_used = ""
        self.last_attempted_provider = ""
        self.last_fallback_provider = ""
        self.last_fallback_status = "none"
        self.last_error_category = ""
        self.last_duration_ms = 0.0
        self.last_generation_latency_ms = 0.0
        self.last_fallback_latency_ms = 0.0
        self.last_retry_count = 0

    def set_mode(self, mode: str) -> str:
        previous = self.mode
        self.mode = mode if mode in {"auto", "local", "ollama", "nvidia", "gemini"} else "auto"
        if self.mode == "gemini" and previous != "gemini":
            self.gemini.reset_transient_health()
        return self.mode

    def selected_provider(self) -> str:
        if self.mode == "gemini":
            return "gemini"
        if self.mode == "nvidia":
            return "nvidia"
        if self.mode == "local":
            return "local"
        return "ollama"

    def context_preview(self, approved_memory_summaries: list[str] | None = None) -> CloudContextPreview:
        return self.sanitizer.preview(approved_memory_summaries=approved_memory_summaries)

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
    ) -> ModelRouterResult:
        start = time.perf_counter()
        print("ROUTER START")
        print("FAST_PATH_USED: false")
        print(f"FAST_CATEGORY: {fast_category}")
        print(f"LOCAL_BRAIN_CONFIDENCE: {local_brain_confidence}")
        print(
            "LOCAL_BRAIN_HANDLED: "
            + ("n/a" if local_brain_handled is None else str(local_brain_handled).lower())
        )
        print("MODEL_ROUTER_USED: true")
        self.last_attempted_provider = ""
        self.last_fallback_provider = ""
        self.last_fallback_status = "none"
        self.last_generation_latency_ms = 0.0
        self.last_fallback_latency_ms = 0.0
        self.last_retry_count = 0
        cloud_allowed = bool(privacy.allow_cloud_model and privacy.allow_nvidia_api)
        gemini_allowed = bool(
            privacy.allow_cloud_model
            and privacy.allow_gemini_api
            and self.mode == "gemini"
        )
        generic_enabled = cloud_allowed and CLOUD_PROVIDER == "openai_compatible" and self.generic_cloud.is_available() and self.mode in {"auto", "nvidia"}
        nvidia_enabled = cloud_allowed and CLOUD_PROVIDER in {"disabled", "nvidia"} and self.nvidia.api_key_available() and self.mode in {"auto", "nvidia"}
        print(f"CLOUD_ALLOWED: {str(cloud_allowed).lower()}")
        print(f"GEMINI_ENABLED: {str(gemini_allowed).lower()}")
        print(f"NVIDIA_ENABLED: {str(nvidia_enabled).lower()}")
        last_error = ""

        if self.mode == "local":
            return self._fallback(start, "local mode")

        safe_prompt = self.sanitizer.build_prompt(
            user_message,
            mood,
            privacy.cloud_context_level,
            memory_hints=memory_hints,
            observation=observation,
        )
        if self.mode == "gemini":
            if not gemini_allowed:
                return self._fallback(start, "Gemini is selected but cloud permission is off")
            self.last_attempted_provider = "gemini"
            reply = self.gemini.generate_reply(
                safe_prompt,
                use_google_search=requires_live_data,
            )
            self.last_generation_latency_ms = reply.duration_ms
            self.last_retry_count = reply.retry_count
            if reply.text.strip() and not reply.error:
                return self._done(
                    start,
                    "gemini",
                    reply.model,
                    reply.text,
                    True,
                    False,
                    None,
                    attempted_provider="gemini",
                    retry_count=reply.retry_count,
                    error_category=reply.error_category,
                    generation_latency_ms=reply.duration_ms,
                )
            last_error = reply.error or "Gemini returned no text"
            if not self.gemini.config.fallback_to_ollama:
                return self._done(
                    start,
                    "fallback",
                    "local-fallback",
                    self._gemini_unavailable_message(ollama_available=False),
                    False,
                    True,
                    last_error,
                    attempted_provider="gemini",
                    retry_count=reply.retry_count,
                    error_category=reply.error_category,
                    generation_latency_ms=reply.duration_ms,
                )
            if privacy.allow_ollama:
                fallback_started = time.perf_counter()
                if self._ollama_available():
                    self.last_fallback_provider = "ollama"
                    self.last_fallback_status = "attempted"
                    result = self.ollama.generate(prompt)
                    fallback_latency_ms = (time.perf_counter() - fallback_started) * 1000
                    self.last_fallback_latency_ms = fallback_latency_ms
                    print(f"OLLAMA_DURATION_MS: {fallback_latency_ms:.1f}")
                    if result.raw_text.strip() and not result.error:
                        self.last_fallback_status = "used"
                        visible = "Gemini stumbled, so I used Ollama. " + result.raw_text
                        return self._done(
                            start,
                            "ollama",
                            result.model,
                            visible,
                            False,
                            True,
                            last_error,
                            attempted_provider="gemini",
                            retry_count=reply.retry_count,
                            error_category=reply.error_category,
                            generation_latency_ms=reply.duration_ms,
                            fallback_latency_ms=fallback_latency_ms,
                        )
                    self.last_fallback_status = "failed"
                    last_error = f"{last_error}; Ollama fallback unavailable"
                else:
                    self.last_fallback_status = "unavailable"
                    self.last_fallback_latency_ms = (time.perf_counter() - fallback_started) * 1000
            return self._done(
                start,
                "fallback",
                "local-fallback",
                self._gemini_unavailable_message(ollama_available=False),
                False,
                True,
                last_error,
                attempted_provider="gemini",
                retry_count=reply.retry_count,
                error_category=reply.error_category,
                generation_latency_ms=reply.duration_ms,
                fallback_latency_ms=self.last_fallback_latency_ms,
            )

        if generic_enabled:
            reply = self.generic_cloud.generate_reply(safe_prompt)
            if reply.text.strip() and not reply.error:
                return self._done(start, "cloud", reply.model, reply.text, True, False, None)
            last_error = reply.error or "cloud empty"
            if self.mode == "nvidia":
                return self._fallback(start, reply.error or "cloud empty")

        if nvidia_enabled:
            result = self.nvidia.generate(safe_prompt)
            if result.raw_text.strip() and not result.error:
                return self._done(start, "nvidia", result.model, result.raw_text, True, False, None)
            last_error = result.error or "nvidia empty"
            if result.error and ("401" in result.error or "403" in result.error):
                print("ERROR: NVIDIA auth failed; provider disabled for session")
            if self.mode == "nvidia":
                return self._fallback(start, result.error or "nvidia empty")

        if privacy.allow_ollama and self.mode in {"auto", "ollama"}:
            ollama_start = time.perf_counter()
            result = self.ollama.generate(prompt)
            print(f"OLLAMA_DURATION_MS: {(time.perf_counter() - ollama_start) * 1000:.1f}")
            if result.raw_text.strip() and not result.error:
                return self._done(start, "ollama", result.model, result.raw_text, False, False, None)
            last_error = result.error or "ollama empty"
            if self.mode == "ollama":
                return self._fallback(start, result.error or "ollama empty")

        return self._fallback(start, last_error or "no provider produced text")

    def _fallback(self, start: float, error: str | None = None) -> ModelRouterResult:
        return self._done(start, "fallback", "local-fallback", random.choice(ROUTER_FALLBACKS), False, True, error)

    def _done(
        self,
        start: float,
        provider: str,
        model: str,
        text: str,
        was_cloud: bool,
        fallback: bool,
        error: str | None,
        *,
        attempted_provider: str = "",
        retry_count: int = 0,
        error_category: str = "",
        generation_latency_ms: float = 0.0,
        fallback_latency_ms: float = 0.0,
    ) -> ModelRouterResult:
        duration_ms = (time.perf_counter() - start) * 1000
        reply = clean_response(text)
        self.last_provider_used = "" if provider in {"fallback", "none"} else provider
        self.last_attempted_provider = attempted_provider or self.last_attempted_provider or provider
        if fallback and provider not in {"fallback", "local", "none"}:
            self.last_fallback_provider = provider
            self.last_fallback_status = "used"
        self.last_duration_ms = duration_ms
        self.last_error_category = error_category or self._error_category(error)
        self.last_retry_count = retry_count
        self.last_generation_latency_ms = generation_latency_ms or self.last_generation_latency_ms
        self.last_fallback_latency_ms = fallback_latency_ms or self.last_fallback_latency_ms
        print("ROUTER END")
        print(f"ROUTER DURATION MS: {duration_ms:.1f}")
        print(f"PROVIDER_USED: {provider}")
        print(f"MODEL_USED: {model}")
        print(f"FALLBACK_USED: {str(fallback).lower()}")
        print(f"ROUTE_SELECTED: {'local-direct-fallback' if fallback else 'model-router'}")
        model_response = provider not in {"fallback", "local"} or bool(attempted_provider)
        print(f"FINAL_REPLY: {'[model response omitted]' if model_response else reply}")
        print(f"ATTEMPTED_PROVIDER: {self.last_attempted_provider or 'none'}")
        print(f"FALLBACK_PROVIDER: {self.last_fallback_provider or 'none'}")
        print(f"RETRY_COUNT: {retry_count}")
        print(f"PROVIDER_HEALTH_STATE: {self.gemini.status().health_state if self.mode == 'gemini' else 'n/a'}")
        print(f"GENERATION_LATENCY_MS: {self.last_generation_latency_ms:.1f}")
        print(f"FALLBACK_LATENCY_MS: {self.last_fallback_latency_ms:.1f}")
        return ModelRouterResult(
            provider,
            model,
            duration_ms,
            was_cloud,
            fallback,
            error,
            reply,
            self.last_attempted_provider,
            retry_count,
            self.last_error_category,
            self.last_generation_latency_ms,
            self.last_fallback_latency_ms,
            True,
        )

    def _ollama_available(self) -> bool:
        probe = getattr(self.ollama, "health_check", None)
        if probe is None:
            return True
        try:
            return bool(probe())
        except Exception:
            return False

    def _gemini_unavailable_message(self, *, ollama_available: bool) -> str:
        category = self.gemini.last_error_category
        if category in {"temporary_unavailable", "network_error", "timeout"}:
            local = "The local model is also unavailable." if not ollama_available else ""
            return f"Gemini is temporarily unavailable. {local} Try again in a moment.".replace("  ", " ").strip()
        if category in {"rate_limit_error", "quota_error"}:
            return "Gemini is rate limited, and no local fallback is available. Try again shortly."
        if category == "authentication_error":
            return "Gemini configuration needs attention, and no local fallback is available."
        if category == "model_unavailable":
            return "The selected Gemini model is unavailable, and no local fallback is running."
        return "Gemini could not answer, and no local fallback is available. Try again in a moment."

    def _error_category(self, error: str | None) -> str:
        if not error:
            return ""
        if self.mode == "gemini" and self.gemini.last_error_category:
            return self.gemini.last_error_category
        lowered = error.lower()
        for category in (
            "authentication_error",
            "quota_error",
            "rate_limit_error",
            "temporary_unavailable",
            "timeout",
            "network_error",
            "model_unavailable",
            "malformed_response",
        ):
            if category.replace("_", " ") in lowered or category in lowered:
                return category
        return "provider_error"
