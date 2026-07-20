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
from fibi.settings import CLOUD_PROVIDER

ROUTER_FALLBACKS = [
    "model brain is asleep.",
    "Ollama is unavailable.",
    "model creature is asleep.",
    "i can do small thoughts right now.",
    "local mode. explainy brain unavailable.",
]


class ModelRouter:
    """Choose local, optional NVIDIA, optional Ollama, then fallback."""

    def __init__(
        self,
        ollama: ModelEngine | None = None,
        nvidia: NvidiaModelEngine | None = None,
        generic_cloud: OpenAICompatibleProvider | None = None,
        sanitizer: CloudContextSanitizer | None = None,
    ) -> None:
        self.ollama = ollama or ModelEngine()
        self.nvidia = nvidia or NvidiaModelEngine()
        self.generic_cloud = generic_cloud or OpenAICompatibleProvider()
        self.sanitizer = sanitizer or CloudContextSanitizer()
        self.mode = "auto"

    def set_mode(self, mode: str) -> str:
        self.mode = mode if mode in {"auto", "local", "ollama", "nvidia"} else "auto"
        return self.mode

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
        cloud_allowed = bool(privacy.allow_cloud_model and privacy.allow_nvidia_api)
        generic_enabled = cloud_allowed and CLOUD_PROVIDER == "openai_compatible" and self.generic_cloud.is_available() and self.mode in {"auto", "nvidia"}
        nvidia_enabled = cloud_allowed and CLOUD_PROVIDER in {"disabled", "nvidia"} and self.nvidia.api_key_available() and self.mode in {"auto", "nvidia"}
        print(f"CLOUD_ALLOWED: {str(cloud_allowed).lower()}")
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

    @staticmethod
    def _done(
        start: float,
        provider: str,
        model: str,
        text: str,
        was_cloud: bool,
        fallback: bool,
        error: str | None,
    ) -> ModelRouterResult:
        duration_ms = (time.perf_counter() - start) * 1000
        reply = clean_response(text)
        print("ROUTER END")
        print(f"ROUTER DURATION MS: {duration_ms:.1f}")
        print(f"PROVIDER_USED: {provider}")
        print(f"MODEL_USED: {model}")
        print(f"FALLBACK_USED: {str(fallback).lower()}")
        print(f"ROUTE_SELECTED: {'local-direct-fallback' if fallback else 'model-router'}")
        print(f"FINAL_REPLY: {reply}")
        return ModelRouterResult(provider, model, duration_ms, was_cloud, fallback, error, reply)
