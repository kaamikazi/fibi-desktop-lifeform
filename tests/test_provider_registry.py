from __future__ import annotations

import pytest

from fibi.services.providers.errors import DuplicateProviderError, UnknownProviderError
from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderConfigurationStatus,
    ProviderHealth,
)
from fibi.services.providers.registry import ProviderRegistry


class FakeProvider:
    def __init__(self, provider_id: str, configured: bool = True) -> None:
        self.provider_id = provider_id
        self.display_name = provider_id.title()
        self.configured = configured

    def configuration_status(self) -> ProviderConfigurationStatus:
        return ProviderConfigurationStatus(self.provider_id, self.configured, True, "test-model")

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.provider_id, "healthy", True)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(True, "ok", self.provider_id, self.provider_id, self.provider_id, "test-model", 1.0)


def test_registry_registers_stable_gemini_and_ollama_ids() -> None:
    registry = ProviderRegistry((FakeProvider("ollama"), FakeProvider("gemini", False)))

    assert tuple(registry.view()) == ("ollama", "gemini")
    assert registry.get("GEMINI").provider_id == "gemini"
    assert not registry.get("gemini").configuration_status().configured


def test_registry_rejects_duplicate_and_unknown_ids() -> None:
    registry = ProviderRegistry((FakeProvider("ollama"),))

    with pytest.raises(DuplicateProviderError):
        registry.register(FakeProvider("ollama"))
    with pytest.raises(UnknownProviderError):
        registry.get("missing")
