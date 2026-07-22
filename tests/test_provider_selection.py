from __future__ import annotations

from types import SimpleNamespace

import pytest

from fibi.services.providers.errors import UnknownProviderError
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService
from tests.test_provider_registry import FakeProvider


class SettingsStore:
    def __init__(self, selected: str = "ollama") -> None:
        self.settings = SimpleNamespace(language_provider=selected)
        self.updates: list[str] = []

    def update(self, **values):
        selected = values["language_provider"]
        self.settings.language_provider = selected
        self.updates.append(selected)
        return self.settings


def test_manual_selection_persists_and_allows_unconfigured_provider() -> None:
    store = SettingsStore()
    changes: list[str] = []
    registry = ProviderRegistry((FakeProvider("ollama"), FakeProvider("gemini", False)))
    selection = ProviderSelectionService(registry, store, on_change=changes.append)

    result = selection.select_provider("gemini")

    assert result.changed and result.persisted
    assert not result.configured
    assert selection.get_selected_provider_id() == "gemini"
    assert store.updates == ["gemini"]
    assert changes[-1] == "gemini"


def test_unknown_selection_is_rejected_without_changing_provider() -> None:
    store = SettingsStore()
    selection = ProviderSelectionService(ProviderRegistry((FakeProvider("ollama"),)), store)

    with pytest.raises(UnknownProviderError):
        selection.select_provider("other")

    assert selection.get_selected_provider_id() == "ollama"
    assert not store.updates
