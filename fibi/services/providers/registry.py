"""Controlled registry of configured language provider adapters."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from fibi.services.providers.errors import DuplicateProviderError, UnknownProviderError
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
