"""Focused regression tests for the completed provider compatibility migration."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.model_router import ModelRouter
from fibi.services.providers.factory import build_provider_subsystem
from tests.smoke_v012_actions import make_core
from tests.test_v0301_gemini_provider import CountingOllama, FakeModelsAPI, provider_with
from tests.test_v0304_provider_resilience import HealthAwareOllama


def _core_with_mocked_gemini(tmp_path: Path, *, response_text: str = "GEMINI_PROVIDER_OK"):
    core, _, _ = make_core(tmp_path, [], [])
    api = FakeModelsAPI(response_text=response_text)
    ollama = CountingOllama("OLLAMA_PROVIDER_OK")
    core.model_router = ModelRouter(ollama=ollama, gemini=provider_with(api))
    core.model_router.set_mode("gemini")
    core.privacy.update(
        allow_cloud_model=True,
        allow_gemini_api=True,
        allow_ollama=True,
    )
    core.get_provider_status()
    return core, api, ollama


def test_status_reads_authoritative_diagnostics_without_network(tmp_path: Path) -> None:
    settings = AppSettingsEngine(tmp_path / "settings.json")
    settings.update(language_provider="ollama")
    ollama = HealthAwareOllama(healthy=True)
    subsystem = build_provider_subsystem(ModelRouter(ollama=ollama), settings)

    metadata = subsystem.registry.model_metadata("ollama")
    snapshot = subsystem.diagnostics.snapshot()

    assert metadata.provider_id == "ollama"
    assert metadata.model_id
    assert snapshot.selected_provider_id == "ollama"
    assert ollama.health_calls == 0


def test_provider_list_uses_normalized_registry_metadata(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path, [], [])
    result = core.respond("/provider list").display_text
    assert "ollama" in result.lower()
    assert "gemini" in result.lower()
    assert "object at 0x" not in result.lower()


def test_gemini_metadata_is_normalized_without_remote_discovery(tmp_path: Path) -> None:
    core, api, _ = _core_with_mocked_gemini(tmp_path)
    metadata = core.provider_registry.model_metadata("gemini")

    assert metadata.provider_id == "gemini"
    assert metadata.display_name == "Gemini"
    assert metadata.configuration_source == "FIBI_GEMINI_MODEL"
    assert metadata.supports("search_grounding")
    assert api.list_calls == 0
    assert "FakeModelsAPI" not in repr(metadata)


def test_provider_use_updates_selection_and_diagnostics(tmp_path: Path) -> None:
    core, _, _ = _core_with_mocked_gemini(tmp_path)
    core.respond("/provider use ollama")
    assert core.provider_selection.get_selected_provider_id() == "ollama"
    assert core.provider_diagnostics.snapshot().selected_provider_id == "ollama"
    assert core.model_router.selected_provider() == "ollama"


def test_status_command_reports_each_manual_selection(tmp_path: Path) -> None:
    core, _, _ = _core_with_mocked_gemini(tmp_path)
    gemini_status = core.respond("/provider status").display_text
    core.respond("/provider use ollama")
    ollama_status = core.respond("/provider status").display_text

    assert "Selected: gemini" in gemini_status
    assert "Selected: ollama" in ollama_status


def test_provider_test_disables_fallback_and_preserves_selection(tmp_path: Path) -> None:
    core, api, ollama = _core_with_mocked_gemini(tmp_path)
    core.update_settings(automatic_provider_fallback=True)
    selected_before = core.provider_selection.get_selected_provider_id()

    result = core.respond("/provider test")

    assert "test ok" in result.display_text.lower()
    assert api.generate_calls == 1
    assert ollama.calls == 0
    assert core.provider_selection.get_selected_provider_id() == selected_before


def test_privacy_and_context_preview_are_content_free(tmp_path: Path) -> None:
    core, _, _ = _core_with_mocked_gemini(tmp_path)
    secret = "fake-secret-marker"
    core._approved_cloud_memory_hints = lambda _message: [secret]  # type: ignore[method-assign]

    privacy = core.respond("/provider privacy").display_text
    preview = core.respond("/provider context-preview").display_text

    assert secret not in privacy
    assert secret not in preview
    assert "Approved memory summaries: 1" in preview
    assert "API keys and secrets: excluded" in preview


def test_benchmark_is_explicit_normalized_and_selection_safe(tmp_path: Path) -> None:
    core, api, ollama = _core_with_mocked_gemini(tmp_path)
    selected_before = core.provider_selection.get_selected_provider_id()
    diagnostics_before = core.provider_diagnostics.snapshot()

    result = core.respond("/provider benchmark")

    assert "Gemini" in result.display_text and "Ollama" in result.display_text
    assert api.generate_calls == 1
    assert ollama.calls == 1
    assert core.provider_selection.get_selected_provider_id() == selected_before
    assert core.provider_diagnostics.snapshot() == diagnostics_before


def test_legacy_facade_projects_authoritative_diagnostics(tmp_path: Path) -> None:
    core, _, _ = _core_with_mocked_gemini(tmp_path, response_text="useful provider answer")
    response = core.respond("explain provider ownership")
    snapshot = core.provider_diagnostics.snapshot()

    assert response.display_text == "useful provider answer"
    assert core.model_router.last_provider_used == snapshot.last_active_provider_id
    assert core.model_router.last_attempted_provider == snapshot.last_attempted_provider_id
    assert core.model_router.last_duration_ms == snapshot.last_latency_ms
    assert core.model_router.last_retry_count == snapshot.retry_count

    payload = repr(asdict(snapshot)).lower()
    assert "useful provider answer" not in payload
    assert "api_key" not in payload
