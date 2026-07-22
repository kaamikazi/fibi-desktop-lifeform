"""Manual, persisted provider selection policy."""

from __future__ import annotations

from collections.abc import Callable

from fibi.services.providers.errors import ProviderSelectionPersistenceError, UnknownProviderError
from fibi.services.providers.models import ProviderConfigurationStatus, ProviderSelectionResult
from fibi.services.providers.protocols import LanguageProvider, ProviderSettingsStore
from fibi.services.providers.registry import ProviderRegistry

SelectionListener = Callable[[str], None]


class ProviderSelectionService:
    """Select providers only through explicit user or settings actions."""

    def __init__(
        self,
        registry: ProviderRegistry,
        settings_store: ProviderSettingsStore,
        *,
        default_provider_id: str = "ollama",
        initial_provider_id: str | None = None,
        on_change: SelectionListener | None = None,
    ) -> None:
        self.registry = registry
        self.settings_store = settings_store
        configured = str(
            initial_provider_id
            or getattr(settings_store.settings, "language_provider", "")
            or default_provider_id
        )
        try:
            self.registry.get(configured)
            self._selected_provider_id = configured
        except UnknownProviderError:
            self._selected_provider_id = default_provider_id
        self._listeners: list[SelectionListener] = []
        if on_change is not None:
            self._listeners.append(on_change)
            on_change(self._selected_provider_id)

    def get_selected_provider_id(self) -> str:
        return self._selected_provider_id

    def get_selected_provider(self) -> LanguageProvider:
        return self.registry.get(self._selected_provider_id)

    def select_provider(self, provider_id: str, *, persist: bool = True) -> ProviderSelectionResult:
        provider = self.registry.get(provider_id)
        normalized = provider.provider_id
        previous = self._selected_provider_id
        if persist:
            try:
                self.settings_store.update(language_provider=normalized)
            except Exception as error:
                raise ProviderSelectionPersistenceError("provider selection could not be saved") from error
        self._selected_provider_id = normalized
        if previous != normalized:
            for listener in tuple(self._listeners):
                listener(normalized)
        return ProviderSelectionResult(
            provider_id=normalized,
            changed=previous != normalized,
            configured=provider.configuration_status().configured,
            persisted=persist,
        )

    def list_provider_options(self) -> tuple[ProviderConfigurationStatus, ...]:
        return tuple(provider.configuration_status() for provider in self.registry.list())

    def add_listener(self, listener: SelectionListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)
