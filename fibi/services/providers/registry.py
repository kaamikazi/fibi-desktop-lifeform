"""Controlled registry of configured language provider adapters."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from fibi.services.providers.errors import DuplicateProviderError, UnknownProviderError
from fibi.services.providers.models import ProviderHealth, ProviderModelMetadata
from fibi.services.providers.protocols import LanguageProvider


class ProviderRegistry:
    def __init__(self, providers: tuple[LanguageProvider, ...] = ()) -> None:
        self._providers: dict[str, LanguageProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: LanguageProvider) -> None:
        provider_id = provider.provider_id.strip().lower()
        if not provider_id:
            raise ValueError("provider_id must not be empty")
        if provider_id in self._providers:
            raise DuplicateProviderError(f"provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> LanguageProvider:
        normalized = str(provider_id or "").strip().lower()
        try:
            return self._providers[normalized]
        except KeyError as error:
            raise UnknownProviderError(f"unknown provider: {normalized or '(empty)'}") from error

    def list(self) -> tuple[LanguageProvider, ...]:
        return tuple(self._providers.values())

    def view(self) -> Mapping[str, LanguageProvider]:
        return MappingProxyType(self._providers)

    def model_metadata(self, provider_id: str) -> ProviderModelMetadata:
        """Return stable model metadata without probing a provider or the network."""

        provider = self.get(provider_id)
        metadata = getattr(provider, "model_metadata", None)
        if callable(metadata):
            return metadata()
        configuration = provider.configuration_status()
        return ProviderModelMetadata(
            provider_id=provider.provider_id,
            model_id=configuration.model_id,
            display_name=provider.display_name,
            configured=configuration.configured,
            available=configuration.configured and configuration.sdk_available,
        )

    def list_model_metadata(self) -> tuple[ProviderModelMetadata, ...]:
        return tuple(self.model_metadata(provider.provider_id) for provider in self.list())

    def health_snapshot(self, provider_id: str) -> ProviderHealth:
        """Read cached health only; ordinary status must never perform I/O."""

        provider = self.get(provider_id)
        cached = getattr(provider, "cached_health", None)
        if callable(cached):
            return cached()
        return ProviderHealth(provider.provider_id, "unknown", False)

    def reset_health(self, provider_id: str) -> bool:
        reset = getattr(self.get(provider_id), "reset_health", None)
        return bool(reset()) if callable(reset) else False
