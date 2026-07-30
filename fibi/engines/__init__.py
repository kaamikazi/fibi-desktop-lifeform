"""Public engine exports without importing the complete application graph."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "AttentionEngine": ("fibi.engines.attention_engine", "AttentionEngine"),
    "AppSettingsEngine": ("fibi.engines.app_settings_engine", "AppSettingsEngine"),
    "AssetHealthEngine": ("fibi.engines.asset_health_engine", "AssetHealthEngine"),
    "AutostartEngine": ("fibi.engines.autostart_engine", "AutostartEngine"),
    "BoundaryEngine": ("fibi.engines.boundary_engine", "BoundaryEngine"),
    "CloudContextSanitizer": (
        "fibi.engines.cloud_context_sanitizer",
        "CloudContextSanitizer",
    ),
    "CloudProviderBase": ("fibi.engines.cloud_provider_base", "CloudProviderBase"),
    "DataHealthEngine": ("fibi.engines.data_health_engine", "DataHealthEngine"),
    "FibiCore": ("fibi.engines.core", "FibiCore"),
    "FastResponseClassifier": (
        "fibi.engines.fast_response_classifier",
        "FastResponseClassifier",
    ),
    "HabitEngine": ("fibi.engines.habit_engine", "HabitEngine"),
    "InnerLifeEngine": ("fibi.engines.inner_life_engine", "InnerLifeEngine"),
    "JournalEngine": ("fibi.engines.journal_engine", "JournalEngine"),
    "LocalMicroBrain": ("fibi.engines.local_micro_brain", "LocalMicroBrain"),
    "MemoryCareEngine": ("fibi.engines.memory_care_engine", "MemoryCareEngine"),
    "ModelHealthEngine": ("fibi.engines.model_health_engine", "ModelHealthEngine"),
    "ModelRouter": ("fibi.engines.model_router", "ModelRouter"),
    "NvidiaModelEngine": ("fibi.engines.nvidia_model_engine", "NvidiaModelEngine"),
    "OpenAICompatibleProvider": (
        "fibi.engines.openai_compatible_provider",
        "OpenAICompatibleProvider",
    ),
    "OpinionEngine": ("fibi.engines.opinion_engine", "OpinionEngine"),
    "PatternEngine": ("fibi.engines.pattern_engine", "PatternEngine"),
    "PreferenceEngine": ("fibi.engines.preference_engine", "PreferenceEngine"),
    "PrivacySettingsEngine": (
        "fibi.engines.privacy_settings_engine",
        "PrivacySettingsEngine",
    ),
    "RelationshipEngine": ("fibi.engines.relationship_engine", "RelationshipEngine"),
    "ResponseBudgetEngine": (
        "fibi.engines.response_budget_engine",
        "ResponseBudgetEngine",
    ),
    "SocialContextEngine": ("fibi.engines.social_context_engine", "SocialContextEngine"),
    "WarmupEngine": ("fibi.engines.warmup_engine", "WarmupEngine"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve a compatibility export only when a caller requests it."""

    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Include unresolved public exports in interactive discovery."""

    return sorted(set(globals()) | set(__all__))
