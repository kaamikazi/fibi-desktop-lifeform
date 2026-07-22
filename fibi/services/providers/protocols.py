"""Structural contracts for the experimental Fibi 0.4 provider API."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fibi.services.providers.models import (
    GenerationRequest,
    GenerationResult,
    ProviderConfigurationStatus,
    ProviderHealth,
)


@runtime_checkable
class LanguageProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    def configuration_status(self) -> ProviderConfigurationStatus: ...

    def health(self) -> ProviderHealth: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...


class ProviderSettingsStore(Protocol):
    @property
    def settings(self): ...

    def update(self, **values): ...
