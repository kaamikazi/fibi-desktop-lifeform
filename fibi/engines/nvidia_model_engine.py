"""Optional NVIDIA OpenAI-compatible model provider."""

from __future__ import annotations

import os
import time

try:
    import requests
except ImportError:
    requests = None

from fibi.engines.types import ModelResult
from fibi.settings import (
    NVIDIA_BASE_URL,
    NVIDIA_MAX_TOKENS,
    NVIDIA_MODEL,
    NVIDIA_TEMPERATURE,
    NVIDIA_TIMEOUT_SECONDS,
)


class NvidiaModelEngine:
    """Call NVIDIA only when explicitly enabled by privacy settings."""

    def __init__(self) -> None:
        self.disabled_for_session = False

    @staticmethod
    def api_key_available() -> bool:
        return bool(os.getenv("NVIDIA_API_KEY", "").strip())

    @staticmethod
    def mask_api_key(value: str | None) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"

    def generate(self, prompt: str) -> ModelResult:
        if self.disabled_for_session:
            return ModelResult("", NVIDIA_MODEL, 0.0, "NVIDIA disabled for session")
        api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        if not api_key:
            return ModelResult("", NVIDIA_MODEL, 0.0, "NVIDIA_API_KEY missing")

        start = time.perf_counter()
        print(f"NVIDIA_ENABLED: true")
        try:
            result = self._generate_openai(prompt, api_key)
            if result is not None:
                return result
            return self._generate_requests(prompt, api_key, start)
        except Exception as error:
            duration = (time.perf_counter() - start) * 1000
            print(f"NVIDIA_DURATION_MS: {duration:.1f}")
            return ModelResult("", NVIDIA_MODEL, duration / 1000, str(error))

    def _generate_openai(self, prompt: str, api_key: str) -> ModelResult | None:
        try:
            from openai import OpenAI
        except ImportError:
            return None
        start = time.perf_counter()
        try:
            client = OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL)
            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=NVIDIA_MAX_TOKENS,
                temperature=NVIDIA_TEMPERATURE,
                timeout=NVIDIA_TIMEOUT_SECONDS,
            )
            text = response.choices[0].message.content or ""
        except Exception as error:
            message = str(error)
            if "401" in message or "403" in message:
                self.disabled_for_session = True
            duration = (time.perf_counter() - start) * 1000
            print(f"NVIDIA_DURATION_MS: {duration:.1f}")
            return ModelResult("", NVIDIA_MODEL, duration / 1000, message)
        duration = (time.perf_counter() - start) * 1000
        print(f"NVIDIA_DURATION_MS: {duration:.1f}")
        return ModelResult(text, NVIDIA_MODEL, duration / 1000, None if text.strip() else "empty NVIDIA reply")

    def _generate_requests(self, prompt: str, api_key: str, start: float) -> ModelResult:
        if requests is None:
            return ModelResult("", NVIDIA_MODEL, 0.0, "requests package is not installed")
        try:
            response = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": NVIDIA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": NVIDIA_MAX_TOKENS,
                    "temperature": NVIDIA_TEMPERATURE,
                },
                timeout=NVIDIA_TIMEOUT_SECONDS,
            )
            if response.status_code in {401, 403}:
                self.disabled_for_session = True
                duration = (time.perf_counter() - start) * 1000
                print(f"NVIDIA_DURATION_MS: {duration:.1f}")
                return ModelResult("", NVIDIA_MODEL, duration / 1000, f"NVIDIA auth failed: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            text = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
        except Exception as error:
            duration = (time.perf_counter() - start) * 1000
            print(f"NVIDIA_DURATION_MS: {duration:.1f}")
            return ModelResult("", NVIDIA_MODEL, duration / 1000, str(error))
        duration = (time.perf_counter() - start) * 1000
        print(f"NVIDIA_DURATION_MS: {duration:.1f}")
        return ModelResult(text, NVIDIA_MODEL, duration / 1000, None if text.strip() else "empty NVIDIA reply")
