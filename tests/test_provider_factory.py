"""Integration tests for provider subsystem construction and shared state."""

from __future__ import annotations

from types import SimpleNamespace

from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.model_router import ModelRouter
from fibi.services.providers.factory import build_provider_subsystem
from tests.test_v0301_gemini_provider import CountingOllama, FakeModelsAPI, provider_with


def test_manual_selection_updates_safe_diagnostics_without_generation(tmp_path) -> None:
    settings = AppSettingsEngine(tmp_path / "settings.json")
    settings.update(language_provider="ollama")
    router = ModelRouter(
        ollama=CountingOllama(),
        nvidia=SimpleNamespace(),
        generic_cloud=SimpleNamespace(),
        gemini=provider_with(FakeModelsAPI()),
    )
    subsystem = build_provider_subsystem(router, settings)

    result = subsystem.selection.select_provider("gemini")
    snapshot = subsystem.diagnostics.snapshot()

    assert result.provider_id == "gemini"
    assert snapshot.selected_provider_id == "gemini"
    assert snapshot.selected_provider_configured is True
    assert snapshot.last_attempted_provider_id == ""
    assert subsystem.selection.get_selected_provider_id() == "gemini"
    assert router.selected_provider() == "gemini"
