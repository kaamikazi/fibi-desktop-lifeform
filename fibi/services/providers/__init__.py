"""Experimental Fibi 0.4 provider selection and generation API."""

from fibi.services.providers.diagnostics import ProviderDiagnostics
from fibi.services.providers.errors import ProviderErrorPresenter
from fibi.services.providers.generation import CompanionGenerationService
from fibi.services.providers.models import (
    PROVIDER_API_VERSION,
    GenerationRequest,
    GenerationResult,
    ProviderConfigurationStatus,
    ProviderDiagnosticsSnapshot,
    ProviderErrorCategory,
    ProviderHealth,
    ProviderSelectionResult,
    ResponseLength,
)
from fibi.services.providers.protocols import LanguageProvider
from fibi.services.providers.registry import ProviderRegistry
from fibi.services.providers.selection import ProviderSelectionService

__all__ = [
    "PROVIDER_API_VERSION",
    "CompanionGenerationService",
    "GenerationRequest",
    "GenerationResult",
    "LanguageProvider",
    "ProviderConfigurationStatus",
    "ProviderDiagnostics",
    "ProviderDiagnosticsSnapshot",
    "ProviderErrorCategory",
    "ProviderErrorPresenter",
    "ProviderHealth",
    "ProviderRegistry",
    "ProviderSelectionResult",
    "ProviderSelectionService",
    "ResponseLength",
]
