from __future__ import annotations

from dataclasses import asdict

from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.models import GenerationResult, ProviderErrorCategory


def test_diagnostics_are_accurate_and_contain_no_prompt_or_secret_fields() -> None:
    diagnostics = ProviderDiagnostics("gemini", True)
    diagnostics.record(
        GenerationResult(
            True,
            "private response must not be retained",
            "gemini",
            "gemini",
            "ollama",
            "qwen",
            12.5,
            ProviderErrorCategory.TIMEOUT,
            fallback_used=True,
            fallback_provider_id="ollama",
            search_grounding_used=False,
        ),
        selected_configured=True,
        fallback_enabled=True,
        fallback_provider_id="ollama",
    )

    payload = asdict(diagnostics.snapshot())
    rendered = repr(payload).lower()
    assert payload["selected_provider_id"] == "gemini"
    assert payload["last_active_provider_id"] == "ollama"
    assert payload["fallback_used"] is True
    assert "private response" not in rendered
    assert "prompt" not in rendered
    assert "api_key" not in rendered
