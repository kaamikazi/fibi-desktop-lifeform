"""Ollama is a replaceable language tool, not Fibi's identity."""

from __future__ import annotations

import time

try:
    import requests
except ImportError:  # Model access is optional; local personality still works.
    requests = None

from fibi.engines.types import ModelResult
from fibi.settings import OLLAMA_MODEL, OLLAMA_MODEL_FALLBACKS, OLLAMA_TIMEOUT_SECONDS, OLLAMA_URL


class ModelEngine:
    def __init__(self) -> None:
        self._health_checked_at = 0.0
        self._health_available = False

    def health_check(self, *, timeout_seconds: float = 0.6, max_age_seconds: float = 3.0) -> bool:
        """Probe Ollama cheaply before committing to a generation timeout."""

        if requests is None:
            return False
        now = time.monotonic()
        if now - self._health_checked_at <= max_age_seconds:
            return self._health_available
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout_seconds)
            available = response.ok
        except requests.RequestException:
            available = False
        self._health_checked_at = now
        self._health_available = available
        return available

    def generate(self, prompt: str) -> ModelResult:
        if requests is None:
            return ModelResult("", "unavailable", 0.0, "requests package is not installed")
        for model in self._models():
            result, model_missing = self._generate_once(model, prompt)
            if not model_missing:
                return result
        return ModelResult("", OLLAMA_MODEL, 0.0, "No configured Ollama model is installed")

    def _generate_once(self, model: str, prompt: str) -> tuple[ModelResult, bool]:
        start = time.perf_counter()
        print(f"AI START TIME: {start:.3f}")
        print(f"MODEL USED: {model}")
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 320, "temperature": 0.8, "top_p": 0.9},
                },
                timeout=OLLAMA_TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                duration = self._log_end(start, response.text.strip() or "model not found")
                return ModelResult("", model, duration, "model not found"), True
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            duration = self._log_end(start, str(error))
            return ModelResult("", model, duration, str(error)), False

        duration = self._log_end(start)
        raw = str(data.get("response", ""))
        if not raw.strip():
            print(f"RAW OLLAMA RESPONSE OBJECT: {data}")
        return ModelResult(raw, model, duration), False

    @staticmethod
    def _log_end(start: float, error: str | None = None) -> float:
        end = time.perf_counter()
        duration = end - start
        print(f"AI END TIME: {end:.3f}")
        print(f"AI DURATION SECONDS: {duration:.2f}")
        if error:
            print(f"ERROR: {error}")
        return duration

    @staticmethod
    def _models() -> list[str]:
        models: list[str] = []
        for model in [OLLAMA_MODEL, *OLLAMA_MODEL_FALLBACKS]:
            if model and model not in models:
                models.append(model)
        return models
