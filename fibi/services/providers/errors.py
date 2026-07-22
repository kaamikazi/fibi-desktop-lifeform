"""Normalized provider errors and concise user-facing presentation."""

from __future__ import annotations

from fibi.services.providers.models import GenerationResult, ProviderErrorCategory


class ProviderSubsystemError(RuntimeError):
    """Base class for safe provider subsystem failures."""


class DuplicateProviderError(ProviderSubsystemError):
    pass


class UnknownProviderError(ProviderSubsystemError):
    pass


class ProviderSelectionPersistenceError(ProviderSubsystemError):
    pass


LEGACY_ERROR_MAP = {
    "authentication_error": ProviderErrorCategory.AUTHENTICATION_ERROR,
    "quota_error": ProviderErrorCategory.QUOTA_ERROR,
    "rate_limit_error": ProviderErrorCategory.RATE_LIMITED,
    "rate_limited": ProviderErrorCategory.RATE_LIMITED,
    "timeout": ProviderErrorCategory.TIMEOUT,
    "network_error": ProviderErrorCategory.NETWORK_ERROR,
    "temporary_unavailable": ProviderErrorCategory.TEMPORARY_UNAVAILABLE,
    "model_unavailable": ProviderErrorCategory.MODEL_UNAVAILABLE,
    "malformed_response": ProviderErrorCategory.INVALID_REQUEST,
    "invalid_request": ProviderErrorCategory.INVALID_REQUEST,
    "safety_block": ProviderErrorCategory.SAFETY_BLOCK,
    "cancelled": ProviderErrorCategory.CANCELLED,
    "empty_response": ProviderErrorCategory.EMPTY_RESPONSE,
    "not_configured": ProviderErrorCategory.NOT_CONFIGURED,
    "unknown_provider_error": ProviderErrorCategory.PROVIDER_INTERNAL_ERROR,
    "provider_error": ProviderErrorCategory.PROVIDER_INTERNAL_ERROR,
}


def normalize_error_category(category: str, message: str = "") -> ProviderErrorCategory:
    normalized = str(category or "").strip().lower()
    if normalized in LEGACY_ERROR_MAP:
        return LEGACY_ERROR_MAP[normalized]
    lowered = str(message or "").lower()
    if "api key" in lowered or "not configured" in lowered or "not installed" in lowered:
        return ProviderErrorCategory.NOT_CONFIGURED
    if "timed out" in lowered or "timeout" in lowered:
        return ProviderErrorCategory.TIMEOUT
    if any(token in lowered for token in ("connect", "network", "unreachable", "connection")):
        return ProviderErrorCategory.NETWORK_ERROR
    if "model" in lowered and any(token in lowered for token in ("missing", "not found", "unavailable")):
        return ProviderErrorCategory.MODEL_UNAVAILABLE
    return ProviderErrorCategory.PROVIDER_INTERNAL_ERROR


class ProviderErrorPresenter:
    """Translate normalized failures without exposing implementation details."""

    _MESSAGES = {
        ProviderErrorCategory.NOT_CONFIGURED: "{provider} is selected but not configured. Check Settings > Provider.",
        ProviderErrorCategory.AUTHENTICATION_ERROR: "{provider} authentication failed. Check its configuration in Settings.",
        ProviderErrorCategory.QUOTA_ERROR: "{provider} quota is unavailable. Check the account or try later.",
        ProviderErrorCategory.RATE_LIMITED: "{provider} is temporarily rate-limited. Try again shortly.",
        ProviderErrorCategory.TIMEOUT: "The selected provider timed out.",
        ProviderErrorCategory.NETWORK_ERROR: "The selected provider could not be reached.",
        ProviderErrorCategory.TEMPORARY_UNAVAILABLE: "The selected provider is temporarily unavailable.",
        ProviderErrorCategory.MODEL_UNAVAILABLE: "The selected provider model is unavailable.",
        ProviderErrorCategory.INVALID_REQUEST: "The selected provider could not process that request.",
        ProviderErrorCategory.SAFETY_BLOCK: "The selected provider declined that request for safety reasons.",
        ProviderErrorCategory.EMPTY_RESPONSE: "The selected provider returned an empty response.",
        ProviderErrorCategory.CANCELLED: "The provider request was cancelled.",
        ProviderErrorCategory.PROVIDER_INTERNAL_ERROR: "The selected provider could not answer. Try again shortly.",
    }

    def present(self, result: GenerationResult, provider_display_name: str) -> str:
        if "disabled by current privacy settings" in result.error_message.lower():
            return (
                "The selected provider was not changed. "
                f"{provider_display_name} is disabled by current privacy settings."
            )
        category = result.error_category or ProviderErrorCategory.PROVIDER_INTERNAL_ERROR
        message = self._MESSAGES[category].format(provider=provider_display_name)
        if category is ProviderErrorCategory.CANCELLED:
            return message
        # Lead with the manual-selection invariant so concise reply enforcement
        # cannot trim the fact that Fibi kept the user's chosen provider.
        return "The selected provider was not changed. " + message

    @staticmethod
    def fallback_notice(primary_display_name: str, fallback_display_name: str) -> str:
        return f"Answered using {fallback_display_name} because {primary_display_name} was temporarily unavailable."
