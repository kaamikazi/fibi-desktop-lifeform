"""Mock-only tests for Fibi v0.30.1 optional Gemini provider."""

from __future__ import annotations

import logging
import importlib.util
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.logging_config import mask_secrets
from fibi.engines.model_router import ModelRouter
from fibi.engines.error_report_engine import ErrorReportEngine
from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
from fibi.engines.types import ModelResult, PrivacySettings
from fibi.providers.gemini_provider import GeminiProvider, ProviderError
from fibi.providers.types import GeminiProviderConfig


@dataclass
class FakeModel:
    name: str
    supported_actions: tuple[str, ...] = ("generateContent",)


class FakeModelsAPI:
    def __init__(self, *, response_text: str = "tiny cloud reply", error: Exception | None = None) -> None:
        self.response_text = response_text
        self.error = error
        self.list_calls = 0
        self.generate_calls = 0
        self.prompts: list[str] = []
        self.configs: list[object] = []
        self.models = [
            FakeModel("models/gemini-3.5-flash"),
            FakeModel("models/gemini-3.5-flash-preview"),
            FakeModel("models/gemini-3.0-pro"),
            FakeModel("models/gemini-embedding-001", ("embedContent",)),
            FakeModel("models/imagen-4"),
        ]

    def list(self):
        self.list_calls += 1
        if self.error:
            raise self.error
        return list(self.models)

    def generate_content(self, *, model: str, contents: str, config: dict):
        self.generate_calls += 1
        self.prompts.append(contents)
        self.configs.append(config)
        if self.error:
            raise self.error
        usage = SimpleNamespace(prompt_token_count=5, candidates_token_count=3, total_token_count=8)
        return SimpleNamespace(text=self.response_text, usage_metadata=usage)

    def generate_content_stream(self, *, model: str, contents: str, config: dict):
        self.generate_calls += 1
        self.prompts.append(contents)
        self.configs.append(config)
        if self.error:
            raise self.error
        return iter([SimpleNamespace(text="tiny "), SimpleNamespace(text="stream")])


class FakeClient:
    def __init__(self, models: FakeModelsAPI) -> None:
        self.models = models


class CountingOllama:
    def __init__(self, text: str = "local answer", error: str | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult(self.text, "fake-ollama", 0.01, self.error)


class FakeAPIError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def config(**values) -> GeminiProviderConfig:
    defaults = {
        "selected_provider": "gemini",
        "api_key": "fake-unit-test-key",
        "model": "",
        "timeout_seconds": 25,
        "fallback_to_ollama": True,
        "streaming": False,
        "context_preview": True,
    }
    defaults.update(values)
    return GeminiProviderConfig(**defaults)


def provider_with(api: FakeModelsAPI, **values) -> GeminiProvider:
    return GeminiProvider(config(**values), client_factory=lambda _key, _timeout: FakeClient(api))


def test_default_provider_is_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIBI_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FIBI_GEMINI_MODEL", raising=False)
    monkeypatch.delenv("FIBI_GEMINI_STREAMING", raising=False)
    monkeypatch.delenv("FIBI_GEMINI_GOOGLE_SEARCH", raising=False)
    loaded = GeminiProviderConfig.from_env()
    assert loaded.selected_provider == "ollama"
    assert not loaded.api_key
    assert loaded.model == "gemini-3.1-flash-lite"
    assert loaded.streaming
    assert loaded.google_search


def test_example_placeholder_is_not_a_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
    assert not GeminiProviderConfig.from_env().api_key


def test_blank_optional_flags_use_documented_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIBI_GEMINI_STREAMING", "")
    monkeypatch.setenv("FIBI_GEMINI_GOOGLE_SEARCH", "")
    loaded = GeminiProviderConfig.from_env()
    assert loaded.streaming
    assert loaded.google_search


def test_provider_is_lazy_and_missing_key_is_safe() -> None:
    provider = GeminiProvider(config(api_key=""))
    result = provider.generate_reply("safe prompt")
    assert result.error == "GEMINI_API_KEY is not configured"
    assert provider.last_error_category == "authentication_error"


def test_missing_sdk_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fibi.providers.gemini_provider.importlib.util.find_spec",
        lambda name: None if name == "google.genai" else importlib.util.find_spec(name),
    )
    provider = GeminiProvider(config())
    result = provider.generate_reply("safe prompt")
    assert result.error == "google-genai SDK is not installed"
    assert provider.last_error_category == "model_unavailable"


def test_model_discovery_filters_and_prefers_stable_flash() -> None:
    api = FakeModelsAPI()
    provider = provider_with(api)
    models = provider.list_models()
    assert "gemini-3.5-flash" in models
    assert "gemini-embedding-001" not in models
    assert "imagen-4" not in models
    assert provider.select_model() == "gemini-3.5-flash"
    assert api.list_calls == 1


def test_configured_model_is_validated() -> None:
    provider = provider_with(FakeModelsAPI(), model="gemini-does-not-exist")
    with pytest.raises(ProviderError) as captured:
        provider.select_model()
    assert captured.value.category == "model_unavailable"


def test_successful_mocked_response_and_usage() -> None:
    api = FakeModelsAPI(response_text="hehe from cloud")
    provider = provider_with(api)
    result = provider.generate_reply("sanitized prompt only")
    assert result.text == "hehe from cloud"
    assert result.error is None
    assert result.model == "gemini-3.5-flash"
    assert provider.last_usage.total_tokens == 8
    assert api.generate_calls == 1


def test_streaming_joins_text() -> None:
    api = FakeModelsAPI()
    provider = provider_with(api, streaming=True)
    result = provider.generate_reply("sanitized prompt only")
    assert result.text == "tiny stream"
    assert api.generate_calls == 1


def test_minimal_thinking_and_search_are_request_scoped() -> None:
    api = FakeModelsAPI()
    provider = provider_with(api)
    provider.generate_reply("normal chat")
    provider.generate_reply("current weather", use_google_search=True)
    normal, grounded = api.configs
    assert normal["thinking_config"] == {"thinking_level": "minimal"}
    assert "tools" not in normal
    assert grounded["tools"] == [{"google_search": {}}]


def test_empty_response_is_normalized() -> None:
    provider = provider_with(FakeModelsAPI(response_text="  "))
    result = provider.generate_reply("safe")
    assert not result.text
    assert provider.last_error_category == "malformed_response"


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (FakeAPIError(401, "bad credential fake-unit-test-key"), "authentication_error"),
        (FakeAPIError(429, "quota"), "quota_error"),
        (FakeAPIError(404, "missing model"), "model_unavailable"),
        (TimeoutError("timed out"), "timeout"),
        (ConnectionError("network down"), "network_error"),
    ],
)
def test_provider_errors_are_safe(error: Exception, category: str) -> None:
    provider = provider_with(FakeModelsAPI(error=error))
    result = provider.generate_reply("safe")
    assert not result.text
    assert provider.last_error_category == category
    assert "fake-unit-test-key" not in (result.error or "")


def test_gemini_success_does_not_call_ollama() -> None:
    gemini = provider_with(FakeModelsAPI())
    ollama = CountingOllama()
    router = ModelRouter(ollama=ollama, gemini=gemini)
    router.set_mode("gemini")
    result = router.route(
        "local rich prompt",
        "explain recursion",
        "curious",
        PrivacySettings(allow_cloud_model=True, allow_gemini_api=True),
    )
    assert result.provider_used == "gemini"
    assert ollama.calls == 0


def test_one_attempt_visible_ollama_fallback() -> None:
    api = FakeModelsAPI(error=TimeoutError("timed out"))
    gemini = provider_with(api)
    ollama = CountingOllama("local rescue")
    router = ModelRouter(ollama=ollama, gemini=gemini)
    router.set_mode("gemini")
    result = router.route(
        "local rich prompt",
        "explain recursion",
        "curious",
        PrivacySettings(allow_cloud_model=True, allow_gemini_api=True),
    )
    assert api.list_calls == 1
    assert ollama.calls == 1
    assert result.provider_used == "ollama"
    assert result.fallback_used
    assert "used Ollama" in result.reply_text


def test_disabled_fallback_never_calls_ollama() -> None:
    gemini = provider_with(
        FakeModelsAPI(error=TimeoutError("timed out")),
        fallback_to_ollama=False,
    )
    ollama = CountingOllama()
    router = ModelRouter(ollama=ollama, gemini=gemini)
    router.set_mode("gemini")
    result = router.route(
        "local rich prompt",
        "explain recursion",
        "curious",
        PrivacySettings(allow_cloud_model=True, allow_gemini_api=True),
    )
    assert ollama.calls == 0
    assert result.provider_used == "fallback"


def test_context_preview_and_prompt_exclude_private_categories() -> None:
    sanitizer = CloudContextSanitizer()
    preview = sanitizer.preview(approved_memory_summaries=["one", "two"], recent_turn_count=9)
    text = preview.format()
    assert "Approved memory summaries: 2" in text
    assert "Raw memory database: excluded" in text
    assert "Project source files: excluded" in text
    assert "Browser history/cookies/passwords: excluded" in text
    prompt = sanitizer.build_prompt(
        "API_KEY=fake-unit-test-key explain this",
        "curious",
        "memory_hint",
        memory_hints=["approved summary"],
    )
    assert "fake-unit-test-key" not in prompt
    assert "approved summary" in prompt


def test_gemini_key_patterns_are_masked_and_blocked() -> None:
    fake_key = "AIza" + "A" * 28
    assert fake_key not in mask_secrets(f"GEMINI_API_KEY={fake_key}")
    assert SensitiveMemoryGuard().assess(f"remember {fake_key}").blocked


def test_provider_status_never_exposes_key() -> None:
    provider = provider_with(FakeModelsAPI())
    status = provider.status(selected=True)
    assert status.configured
    assert "fake-unit-test-key" not in repr(status)


def test_provider_test_uses_only_neutral_prompt() -> None:
    api = FakeModelsAPI(response_text="GEMINI_PROVIDER_OK")
    provider = provider_with(api)
    result = provider.test_connection()
    assert result.text == "GEMINI_PROVIDER_OK"
    assert api.prompts == ["Reply with GEMINI_PROVIDER_OK."]


def test_core_provider_commands_are_local_and_opt_in() -> None:
    from tests.smoke_v012_actions import make_core

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        api = FakeModelsAPI(response_text="GEMINI_PROVIDER_OK")
        core.model_router = ModelRouter(model, gemini=provider_with(api))

        status = core.respond("/provider status").display_text
        assert "provider:" in status
        assert api.list_calls == 0
        selected = core.respond("/provider use gemini").display_text
        assert "Cloud request preview" in selected
        assert core.privacy.settings.allow_gemini_api
        tested = core.respond("/provider test").display_text
        assert "Gemini test ok" in tested
        assert api.prompts[-1] == "Reply with GEMINI_PROVIDER_OK."
        local = core.respond("/provider use ollama").display_text
        assert "LOCAL - Ollama" in local
        assert not core.privacy.settings.allow_gemini_api


def test_missing_key_command_does_not_enable_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.smoke_v012_actions import make_core

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])
        response = core.respond("/provider use gemini").display_text
        assert "not configured" in response
        assert not core.privacy.settings.allow_gemini_api
        assert not core.model_router.gemini.is_configured()


def test_cloud_logs_omit_response_text(caplog: pytest.LogCaptureFixture) -> None:
    api = FakeModelsAPI(response_text="private response should not be logged")
    provider = provider_with(api)
    with caplog.at_level(logging.INFO):
        provider.generate_reply("sanitized prompt")
    assert "private response should not be logged" not in caplog.text
    assert "sanitized prompt" not in caplog.text


def test_support_bundle_contains_boolean_not_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_key = "AIza" + "B" * 28
    monkeypatch.setenv("GEMINI_API_KEY", fake_key)
    bundle_path = ErrorReportEngine(tmp_path / "reports").export()
    with zipfile.ZipFile(bundle_path) as bundle:
        names = bundle.namelist()
        assert not any(name.lower().startswith(".env") for name in names)
        payload = bundle.read("provider_status.json").decode("utf-8")
        combined = "\n".join(
            bundle.read(name).decode("utf-8", errors="replace")
            for name in names
            if name.endswith((".txt", ".json"))
        )
    assert '"GEMINI_API_KEY_CONFIGURED": true' in payload
    assert fake_key not in combined


def test_local_greeting_never_calls_gemini() -> None:
    from tests.smoke_v012_actions import make_core

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        api = FakeModelsAPI()
        core.model_router = ModelRouter(model, gemini=provider_with(api))
        response = core.respond("hi")
        assert response.display_text
        assert api.list_calls == 0
        assert api.generate_calls == 0


def test_gui_provider_panel_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    from PyQt6.QtWidgets import QApplication

    from fibi.ui.fibi_window import FibiSettingsDialog
    from tests.smoke_v012_actions import make_core

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])
        app = QApplication.instance() or QApplication([])
        dialog = FibiSettingsDialog(core)
        assert dialog.provider_combo.count() == 2
        assert dialog.provider_combo.itemData(0) == "ollama"
        assert dialog.provider_combo.itemData(1) == "gemini"
        assert "Gemini API key:" in dialog.cloud_label.text()
        dialog.close()
        app.processEvents()
