from __future__ import annotations

from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.generation import CompanionGenerationService
from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderErrorCategory,
)
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService
from tests.test_provider_registry import FakeProvider
from tests.test_provider_selection import SettingsStore


class ResultProvider(FakeProvider):
    def __init__(self, provider_id: str, results: list[GenerationResult]) -> None:
        super().__init__(provider_id)
        self.results = list(results)
        self.calls = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        return self.results.pop(0)


def result(provider: str, *, text: str = "", error: ProviderErrorCategory | None = None) -> GenerationResult:
    return GenerationResult(
        success=error is None,
        text=text,
        selected_provider_id=provider,
        attempted_provider_id=provider,
        provider_id=provider if error is None else "",
        model_id=f"{provider}-model",
        latency_ms=5.0,
        error_category=error,
        error_message=error.value if error else "",
    )


def build(gemini_results, ollama_results, *, selected="gemini", fallback=False):
    gemini = ResultProvider("gemini", gemini_results)
    ollama = ResultProvider("ollama", ollama_results)
    registry = ProviderRegistry((ollama, gemini))
    selection = ProviderSelectionService(registry, SettingsStore(selected))
    diagnostics = ProviderDiagnostics(selected, True)
    service = CompanionGenerationService(
        registry,
        selection,
        diagnostics,
        fallback_enabled=fallback,
        fallback_provider_id="ollama",
    )
    request = GenerationRequest("question", "prompt", allowed_provider_ids=frozenset({"gemini", "ollama"}))
    return service, selection, diagnostics, gemini, ollama, request


def test_selected_provider_success_is_normalized() -> None:
    service, selection, diagnostics, gemini, ollama, request = build(
        [result("gemini", text="gemini answer")],
        [],
    )

    generated = service.generate(request)

    assert generated.success and generated.text == "gemini answer"
    assert generated.provider_id == "gemini"
    assert gemini.calls == 1 and ollama.calls == 0
    assert selection.get_selected_provider_id() == "gemini"
    assert diagnostics.snapshot().last_active_provider_id == "gemini"


def test_manually_selected_ollama_is_the_only_provider_called() -> None:
    service, selection, diagnostics, gemini, ollama, request = build(
        [],
        [result("ollama", text="local answer")],
        selected="ollama",
    )

    generated = service.generate(request)

    assert generated.success and generated.text == "local answer"
    assert generated.provider_id == "ollama"
    assert ollama.calls == 1 and gemini.calls == 0
    assert selection.get_selected_provider_id() == "ollama"
    assert diagnostics.snapshot().last_active_provider_id == "ollama"


def test_unconfigured_selection_returns_setup_error_before_generation() -> None:
    gemini = ResultProvider("gemini", [result("gemini", text="must not run")])
    gemini.configured = False
    ollama = ResultProvider("ollama", [])
    registry = ProviderRegistry((ollama, gemini))
    selection = ProviderSelectionService(registry, SettingsStore("gemini"))
    diagnostics = ProviderDiagnostics("gemini", False)
    service = CompanionGenerationService(registry, selection, diagnostics)

    generated = service.generate(
        GenerationRequest("question", "prompt", allowed_provider_ids=frozenset({"gemini"}))
    )

    assert not generated.success
    assert generated.error_category is ProviderErrorCategory.NOT_CONFIGURED
    assert gemini.calls == 0 and ollama.calls == 0
    assert "not configured" in service.present_error(generated).lower()
    assert selection.get_selected_provider_id() == "gemini"


def test_fallback_off_returns_clear_primary_failure() -> None:
    service, selection, diagnostics, gemini, ollama, request = build(
        [result("gemini", error=ProviderErrorCategory.TIMEOUT)],
        [result("ollama", text="local answer")],
        fallback=False,
    )

    generated = service.generate(request)

    assert not generated.success
    assert generated.error_category is ProviderErrorCategory.TIMEOUT
    assert ollama.calls == 0
    assert selection.get_selected_provider_id() == "gemini"


def test_explicit_fallback_uses_ollama_without_changing_selection() -> None:
    service, selection, diagnostics, gemini, ollama, request = build(
        [result("gemini", error=ProviderErrorCategory.NETWORK_ERROR)],
        [result("ollama", text="local answer")],
        fallback=True,
    )

    generated = service.generate(request)

    assert generated.success and generated.fallback_used
    assert generated.provider_id == "ollama"
    assert generated.fallback_provider_id == "ollama"
    assert "Answered using Ollama" in generated.text
    assert selection.get_selected_provider_id() == "gemini"
    assert diagnostics.snapshot().selected_provider_id == "gemini"


def test_ineligible_error_never_falls_back() -> None:
    service, selection, diagnostics, gemini, ollama, request = build(
        [result("gemini", error=ProviderErrorCategory.AUTHENTICATION_ERROR)],
        [result("ollama", text="must not run")],
        fallback=True,
    )

    generated = service.generate(request)

    assert not generated.success
    assert ollama.calls == 0
    assert selection.get_selected_provider_id() == "gemini"


def test_fibi_core_delegates_complex_generation_to_use_case(tmp_path) -> None:
    from tests.smoke_v012_actions import make_core

    core, legacy_model, _ = make_core(tmp_path / "core", [], [])

    class StubGeneration:
        fallback_enabled = False
        calls: list[GenerationRequest] = []

        def generate(self, request: GenerationRequest, *, allow_fallback=None):
            self.calls.append(request)
            return result("ollama", text="Python is a programming language.")

        def present_error(self, generated):
            return "provider failed"

        def set_fallback(self, enabled, provider_id="ollama"):
            self.fallback_enabled = enabled

    stub = StubGeneration()
    core.generation_service = stub

    response = core.respond("what is Python?")

    assert response.display_text.startswith("Python is a programming language")
    assert len(stub.calls) == 1
    assert legacy_model.calls == 0
