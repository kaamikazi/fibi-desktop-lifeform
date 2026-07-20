"""Mock-only regression tests for Fibi v0.30.4 provider resilience."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from fibi.engines.model_router import ModelRouter
from fibi.engines.types import ModelResult, PrivacySettings
from fibi.providers.gemini_provider import GeminiProvider
from fibi.providers.types import GeminiProviderConfig


@dataclass
class FakeModel:
    name: str
    supported_actions: tuple[str, ...] = ("generateContent",)


class FakeHTTPError(Exception):
    def __init__(self, code: int, message: str, retry_after: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.response = SimpleNamespace(
            status_code=code,
            headers={"Retry-After": retry_after} if retry_after else {},
        )


class SequenceModelsAPI:
    def __init__(self, outcomes: list[str | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.list_calls = 0
        self.generate_calls = 0
        self.prompts: list[str] = []
        self.generated_models: list[str] = []
        self.models = [
            FakeModel("models/gemini-3.5-flash"),
            FakeModel("models/gemini-3.0-flash"),
            FakeModel("models/gemini-3.0-pro"),
            FakeModel("models/gemini-3.5-flash-preview"),
            FakeModel("models/gemini-embedding-001", ("embedContent",)),
        ]

    def list(self) -> list[FakeModel]:
        self.list_calls += 1
        return list(self.models)

    def generate_content(self, *, model: str, contents: str, config: dict) -> SimpleNamespace:
        self.generate_calls += 1
        self.prompts.append(contents)
        self.generated_models.append(model)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        usage = SimpleNamespace(prompt_token_count=3, candidates_token_count=2, total_token_count=5)
        return SimpleNamespace(text=outcome, usage_metadata=usage)


class FakeClient:
    def __init__(self, models: SequenceModelsAPI) -> None:
        self.models = models


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


class HealthAwareOllama:
    def __init__(self, *, healthy: bool, text: str = "local rescue", error: str | None = None) -> None:
        self.healthy = healthy
        self.text = text
        self.error = error
        self.health_calls = 0
        self.generate_calls = 0

    def health_check(self) -> bool:
        self.health_calls += 1
        return self.healthy

    def generate(self, prompt: str) -> ModelResult:
        self.generate_calls += 1
        return ModelResult(self.text, "fake-ollama", 0.01, self.error)


def provider_with(
    api: SequenceModelsAPI,
    clock: FakeClock | None = None,
    **overrides: object,
) -> GeminiProvider:
    fake_clock = clock or FakeClock()
    values: dict[str, object] = {
        "selected_provider": "gemini",
        "api_key": "fake-unit-test-key",
        "model": "",
        "timeout_seconds": 8,
        "fallback_to_ollama": True,
        "streaming": False,
        "context_preview": True,
    }
    values.update(overrides)
    return GeminiProvider(
        GeminiProviderConfig(**values),
        client_factory=lambda _key, _timeout: FakeClient(api),
        clock=fake_clock,
        sleeper=fake_clock.sleep,
        jitter=lambda _low, _high: 0.5,
        cooldown_seconds=25,
    )


def enabled_privacy(*, ollama: bool = True) -> PrivacySettings:
    return PrivacySettings(
        allow_cloud_model=True,
        allow_gemini_api=True,
        allow_ollama=ollama,
    )


def route(router: ModelRouter, message: str = "explain retry behavior"):
    router.set_mode("gemini")
    return router.route("sanitized prepared context", message, "curious", enabled_privacy())


def test_one_503_retries_once_then_succeeds() -> None:
    api = SequenceModelsAPI([FakeHTTPError(503, "service unavailable"), "tiny success"])
    clock = FakeClock()
    provider = provider_with(api, clock)
    result = provider.generate_reply("sanitized prompt")
    assert result.text == "tiny success"
    assert result.retry_count == 1
    assert result.attempt_count == 2
    assert api.generate_calls == 2
    assert clock.sleeps == [0.5]
    assert provider.status().health_state == "healthy"


def test_two_503s_degrade_provider_and_never_exceed_two_attempts() -> None:
    api = SequenceModelsAPI([
        FakeHTTPError(503, "service unavailable"),
        FakeHTTPError(503, "service unavailable"),
    ])
    provider = provider_with(api)
    result = provider.generate_reply("sanitized prompt")
    assert result.error_category == "temporary_unavailable"
    assert result.retry_count == 1
    assert api.generate_calls == 2
    assert provider.status().health_state == "degraded"
    assert 20 <= provider.status().retry_after_seconds <= 25


def test_immediate_cooldown_is_clear_then_later_request_recovers() -> None:
    clock = FakeClock()
    api = SequenceModelsAPI([
        FakeHTTPError(503, "temporary"),
        FakeHTTPError(503, "temporary"),
        "recovered",
    ])
    provider = provider_with(api, clock)
    provider.generate_reply("first")
    immediate = provider.generate_reply("second")
    assert immediate.error_category == "temporary_unavailable"
    assert immediate.attempt_count == 0
    assert api.generate_calls == 2
    clock.advance(26)
    recovered = provider.generate_reply("third")
    assert recovered.text == "recovered"
    assert api.generate_calls == 3
    assert provider.status().health_state == "healthy"


def test_provider_test_bypasses_cooldown_once_and_restores_health() -> None:
    api = SequenceModelsAPI([
        FakeHTTPError(503, "temporary"),
        FakeHTTPError(503, "temporary"),
        "GEMINI_PROVIDER_OK",
    ])
    provider = provider_with(api)
    provider.generate_reply("first")
    tested = provider.test_connection()
    assert tested.text == "GEMINI_PROVIDER_OK"
    assert tested.attempt_count == 1
    assert api.prompts[-1] == "Reply with GEMINI_PROVIDER_OK."
    assert provider.status().health_state == "healthy"


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_errors_do_not_retry_or_clear_without_success(status: int) -> None:
    api = SequenceModelsAPI([FakeHTTPError(status, "access denied"), "GEMINI_PROVIDER_OK"])
    provider = provider_with(api)
    failed = provider.generate_reply("safe")
    assert failed.error_category == "authentication_error"
    assert api.generate_calls == 1
    assert provider.status().health_state == "configuration_error"
    assert not provider.reset_transient_health()
    blocked = provider.generate_reply("safe again")
    assert blocked.attempt_count == 0
    assert api.generate_calls == 1
    assert provider.test_connection().text == "GEMINI_PROVIDER_OK"
    assert provider.status().health_state == "healthy"


def test_429_is_rate_limited_and_honors_retry_after() -> None:
    provider = provider_with(SequenceModelsAPI([FakeHTTPError(429, "rate limit", "42")]))
    result = provider.generate_reply("safe")
    assert result.error_category == "rate_limit_error"
    assert result.attempt_count == 1
    assert provider.status().health_state == "rate_limited"
    assert provider.status().retry_after_seconds == 42


@pytest.mark.parametrize(
    ("error", "category", "state"),
    [
        (TimeoutError("timed out"), "timeout", "degraded"),
        (FakeHTTPError(404, "model not found"), "model_unavailable", "unavailable"),
        (ValueError("odd failure"), "unknown_provider_error", "unknown"),
    ],
)
def test_error_classification(error: Exception, category: str, state: str) -> None:
    api = SequenceModelsAPI([error])
    provider = provider_with(api)
    result = provider.generate_reply("safe")
    assert result.error_category == category
    assert result.attempt_count == 1
    assert provider.status().health_state == state


def test_model_discovery_is_cached_and_retry_uses_alternate_candidate() -> None:
    api = SequenceModelsAPI([
        FakeHTTPError(503, "temporary"),
        "alternate success",
        "later success",
    ])
    provider = provider_with(api)
    first = provider.generate_reply("first")
    second = provider.generate_reply("second")
    assert first.text == "alternate success"
    assert second.text == "later success"
    assert api.list_calls == 1
    assert api.generated_models[0] != api.generated_models[1]


def test_dead_ollama_is_health_checked_and_skipped_without_generation() -> None:
    api = SequenceModelsAPI([FakeHTTPError(503, "temporary"), FakeHTTPError(503, "temporary")])
    ollama = HealthAwareOllama(healthy=False)
    router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    result = route(router)
    assert ollama.health_calls == 1
    assert ollama.generate_calls == 0
    assert result.provider_used == "fallback"
    assert "temporarily unavailable" in result.reply_text
    assert "asleep" not in result.reply_text
    assert router.last_fallback_status == "unavailable"


def test_visible_ollama_fallback_and_diagnostics() -> None:
    api = SequenceModelsAPI([TimeoutError("timed out")])
    ollama = HealthAwareOllama(healthy=True)
    router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    result = route(router)
    assert result.provider_used == "ollama"
    assert result.fallback_used
    assert router.last_attempted_provider == "gemini"
    assert router.last_fallback_provider == "ollama"
    assert router.last_fallback_status == "used"
    assert result.fallback_latency_ms >= 0


def test_disabled_fallback_never_probes_ollama() -> None:
    api = SequenceModelsAPI([TimeoutError("timed out")])
    ollama = HealthAwareOllama(healthy=True)
    gemini = provider_with(api, fallback_to_ollama=False)
    router = ModelRouter(ollama=ollama, gemini=gemini)
    result = route(router)
    assert result.provider_used == "fallback"
    assert ollama.health_calls == 0
    assert ollama.generate_calls == 0


def test_switching_away_and_back_resets_only_transient_health() -> None:
    api = SequenceModelsAPI([TimeoutError("timed out")])
    provider = provider_with(api)
    provider.generate_reply("safe")
    assert provider.status().health_state == "degraded"
    router = ModelRouter(ollama=HealthAwareOllama(healthy=False), gemini=provider)
    router.set_mode("ollama")
    router.set_mode("gemini")
    assert provider.status().health_state == "unknown"


def test_logs_never_include_key_prompt_or_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "fake-unit-test-key"
    prompt = "raw private prompt marker"
    reply = "raw private response marker"
    provider = provider_with(SequenceModelsAPI([reply]))
    with caplog.at_level(logging.INFO):
        provider.generate_reply(prompt)
    assert secret not in caplog.text
    assert prompt not in caplog.text
    assert reply not in caplog.text


def test_core_preserves_model_router_used_after_provider_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tests.smoke_v012_actions import make_core

    core, _, _ = make_core(tmp_path / "core", [], [])
    api = SequenceModelsAPI([FakeHTTPError(503, "temporary"), FakeHTTPError(503, "temporary")])
    core.model_router = ModelRouter(
        ollama=HealthAwareOllama(healthy=False),
        gemini=provider_with(api),
    )
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True, allow_ollama=True)
    prompt = "explain provider resilience"
    response = core.respond(prompt)
    logs = capsys.readouterr().out
    assert response.display_text
    assert "MODEL_ROUTER_USED: true" in logs
    assert "model is asleep" not in response.display_text
    assert prompt not in logs
    assert response.display_text not in logs


def test_immediate_second_core_request_still_reaches_router(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tests.smoke_v012_actions import make_core

    core, _, _ = make_core(tmp_path / "core-cooldown", [], [])
    api = SequenceModelsAPI([FakeHTTPError(503, "temporary"), FakeHTTPError(503, "temporary")])
    core.model_router = ModelRouter(
        ollama=HealthAwareOllama(healthy=False),
        gemini=provider_with(api),
    )
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True, allow_ollama=True)
    core.respond("explain provider resilience")
    capsys.readouterr()
    second = core.respond("why did the provider fail?")
    logs = capsys.readouterr().out
    assert "MODEL_ROUTER_USED: true" in logs
    assert "cooldown" in (core.model_router.gemini.last_error or "").lower()
    assert "temporarily unavailable" in second.display_text


def test_provider_commands_report_health_and_reset_transient_state(tmp_path: Path) -> None:
    from tests.smoke_v012_actions import make_core

    core, _, _ = make_core(tmp_path / "commands", [], [])
    api = SequenceModelsAPI([TimeoutError("timed out")])
    core.model_router = ModelRouter(
        ollama=HealthAwareOllama(healthy=False),
        gemini=provider_with(api),
    )
    core.model_router.set_mode("gemini")
    core.privacy.update(allow_cloud_model=True, allow_gemini_api=True, allow_ollama=True)
    core.model_router.gemini.generate_reply("safe")
    status = core.respond("/provider status").display_text
    assert "State: degraded" in status
    assert "Last retry count:" in status
    reset = core.respond("/provider reset health").display_text
    assert "transient health reset" in reset


def test_demo_reset_disables_only_demo_rvc(tmp_path: Path) -> None:
    from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine
    from tools.reset_demo_profile import configure_demo_voice

    normal_path = tmp_path / "normal" / "voice_skin_settings.json"
    normal = VoiceSkinSettingsEngine(normal_path)
    normal.update(allow_rvc_voice_skin=True, rvc_enabled=True)
    demo_path = tmp_path / "demo"
    configure_demo_voice(demo_path)
    demo = VoiceSkinSettingsEngine(demo_path / "voice_skin_settings.json")
    assert not demo.settings.rvc_enabled
    assert not demo.settings.allow_rvc_voice_skin
    assert demo.settings.rvc_backend == "disabled"
    assert VoiceSkinSettingsEngine(normal_path).settings.rvc_enabled


@pytest.mark.parametrize(
    "message",
    ["weather today", "latest news", "live prices", "current sports scores"],
)
def test_live_data_questions_explain_capability_without_model(
    tmp_path: Path,
    message: str,
) -> None:
    from tests.smoke_v012_actions import make_core

    core, model, _ = make_core(tmp_path / str(abs(hash(message))), [], [])
    response = core.respond(message)
    assert "live-data source" in response.display_text
    assert model.calls == 0
