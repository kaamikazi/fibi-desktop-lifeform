"""Model health and lightweight performance metrics."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import ModelHealthState, PerformanceMetric


class ModelHealthEngine:
    KEY = "model_health"
    PERF_KEY = "performance_metric"

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_health()
        self.performance = self._load_perf()
        self.save()

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_health(self) -> ModelHealthState:
        raw = self._read_state().get(self.KEY, {})
        defaults = asdict(ModelHealthState())
        if isinstance(raw, dict):
            defaults.update({key: raw[key] for key in defaults if key in raw})
        return ModelHealthState(**defaults)

    def _load_perf(self) -> PerformanceMetric:
        raw = self._read_state().get(self.PERF_KEY, {})
        defaults = asdict(PerformanceMetric())
        if isinstance(raw, dict):
            defaults.update({key: raw[key] for key in defaults if key in raw})
        return PerformanceMetric(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.state)
        state[self.PERF_KEY] = asdict(self.performance)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def provider_allowed(self, provider: str) -> bool:
        disabled = self.state.provider_disabled_until
        if not disabled:
            return True
        try:
            until = datetime.fromisoformat(disabled)
        except ValueError:
            return True
        return datetime.now().astimezone() >= until or self.state.last_successful_provider == provider

    def record_provider_result(self, provider: str, latency_ms: float, ok: bool, error: str | None = None) -> None:
        if provider == "ollama":
            self.state.ollama_available = ok
            self.state.last_ollama_latency_ms = latency_ms
        elif provider in {"nvidia", "cloud"}:
            self.state.cloud_available = ok
            self.state.last_cloud_latency_ms = latency_ms
        if ok:
            self.state.consecutive_model_failures = 0
            self.state.last_successful_provider = provider
            self.state.provider_disabled_until = None
        else:
            self.state.consecutive_model_failures += 1
            if error and "timed out" in error.lower() or error and "timeout" in error.lower():
                self.state.provider_disabled_until = (datetime.now().astimezone() + timedelta(seconds=60)).isoformat(timespec="seconds")
            elif self.state.consecutive_model_failures >= 3:
                self.state.provider_disabled_until = (datetime.now().astimezone() + timedelta(minutes=5)).isoformat(timespec="seconds")
        self.save()

    def record_reply(
        self,
        latency_ms: float,
        provider: str,
        fast_path: bool = False,
        model_latency_ms: float = 0.0,
        slowest_step: str = "",
    ) -> None:
        previous = self.performance.average_reply_time_ms
        average = latency_ms if previous <= 0 else previous * 0.8 + latency_ms * 0.2
        self.performance = PerformanceMetric(
            latency_ms,
            provider,
            fast_path,
            model_latency_ms,
            self.performance.tts_latency_ms,
            self.performance.db_latency_ms,
            average,
            slowest_step,
        )
        self.state.average_reply_latency_ms = average
        self.save()

    def record_tts(self, latency_ms: float) -> None:
        self.performance.tts_latency_ms = latency_ms
        self.save()

    def reset_perf(self) -> None:
        self.performance = PerformanceMetric()
        self.save()

    def status_line(self) -> str:
        ollama = "ready" if self.state.ollama_available else "sleepy"
        cloud = "ready" if self.state.cloud_available else "off"
        disabled = self._cooldown_seconds()
        if disabled > 0:
            return f"local brain ready. ollama sleepy for {disabled}s. cloud {cloud}."
        return f"local brain ready. ollama {ollama}. cloud {cloud}."

    def _cooldown_seconds(self) -> int:
        disabled = self.state.provider_disabled_until
        if not disabled:
            return 0
        try:
            until = datetime.fromisoformat(disabled)
        except ValueError:
            return 0
        return max(0, int((until - datetime.now().astimezone()).total_seconds()))

    def perf_line(self) -> str:
        return f"last reply: {self.performance.last_reply_time_ms:.0f}ms. provider {self.performance.provider_used}. avg {self.performance.average_reply_time_ms:.0f}ms."
