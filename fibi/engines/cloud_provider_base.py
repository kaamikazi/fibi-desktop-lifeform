"""Provider-agnostic cloud model interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class CloudProviderReply:
    text: str
    model: str
    duration_ms: float
    error: str | None = None
    error_category: str = ""
    retry_count: int = 0
    attempt_count: int = 0


class CloudProviderBase(ABC):
    name: str = "disabled"
    timeout_seconds: int = 8
    max_tokens: int = 60
    supports_streaming: bool = False
    privacy_level: str = "minimal"
    last_error: str | None = None

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this provider can be used."""

    @abstractmethod
    def generate_reply(self, context: str) -> CloudProviderReply:
        """Generate one reply from sanitized context."""


class DisabledCloudProvider(CloudProviderBase):
    name = "disabled"

    def is_available(self) -> bool:
        return False

    def generate_reply(self, context: str) -> CloudProviderReply:
        return CloudProviderReply("", "disabled", 0.0, "cloud disabled")
