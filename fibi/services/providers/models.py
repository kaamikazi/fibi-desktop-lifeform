"""Typed provider models for the experimental Fibi 0.4 provider API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

PROVIDER_API_VERSION = "0.4-experimental"


class ProviderErrorCategory(str, Enum):
    NOT_CONFIGURED = "not_configured"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_ERROR = "quota_error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    SAFETY_BLOCK = "safety_block"
    EMPTY_RESPONSE = "empty_response"
    CANCELLED = "cancelled"
    PROVIDER_INTERNAL_ERROR = "provider_internal_error"


class ResponseLength(str, Enum):
    CONCISE = "concise"
    NORMAL = "normal"
    DETAILED = "detailed"


@dataclass(frozen=True, slots=True)
class ProviderConfigurationStatus:
    provider_id: str
    configured: bool
    sdk_available: bool
    model_id: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider_id: str
    state: str
    available: bool
    last_error_category: ProviderErrorCategory | None = None
    retry_after_seconds: int = 0


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Provider-relevant, pre-approved input with no credentials or services."""

    user_text: str
    prepared_prompt: str
    mood: str = "idle"
    time_of_day: str = "unknown"
    context_level: str = "minimal"
    approved_context_summaries: tuple[str, ...] = ()
    response_length: ResponseLength = ResponseLength.CONCISE
    response_instruction: str = ""
    search_grounding_allowed: bool = False
    allowed_provider_ids: frozenset[str] = frozenset({"ollama"})
    timeout_seconds: float | None = None
    purpose: str = "conversation"


@dataclass(frozen=True, slots=True)
class GenerationResult:
    success: bool
    text: str
    selected_provider_id: str
    attempted_provider_id: str
    provider_id: str
    model_id: str
    latency_ms: float
    error_category: ProviderErrorCategory | None = None
    error_message: str = ""
    retry_count: int = 0
    fallback_used: bool = False
    fallback_provider_id: str = ""
    fallback_latency_ms: float = 0.0
    search_grounding_used: bool = False
    safe_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderSelectionResult:
    provider_id: str
    changed: bool
    configured: bool
    persisted: bool


@dataclass(frozen=True, slots=True)
class ProviderDiagnosticsSnapshot:
    selected_provider_id: str
    selected_provider_configured: bool
    last_attempted_provider_id: str = ""
    last_active_provider_id: str = ""
    last_model_id: str = ""
    last_success: bool = False
    last_error_category: str = ""
    last_latency_ms: float = 0.0
    retry_count: int = 0
    fallback_enabled: bool = False
    fallback_provider_id: str = ""
    fallback_used: bool = False
    search_grounding_used: bool = False
    timestamp: str = ""

    @classmethod
    def empty(cls, selected_provider_id: str, configured: bool) -> "ProviderDiagnosticsSnapshot":
        return cls(
            selected_provider_id=selected_provider_id,
            selected_provider_configured=configured,
            timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
