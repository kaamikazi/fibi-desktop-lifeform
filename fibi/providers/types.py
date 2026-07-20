"""Typed provider configuration and safe diagnostics."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class GeminiProviderConfig:
    """Gemini settings sourced from local environment variables only."""

    selected_provider: str = "ollama"
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 8
    fallback_to_ollama: bool = True
    streaming: bool = True
    context_preview: bool = True
    google_search: bool = True
    thinking_level: str = "minimal"

    @classmethod
    def from_env(cls) -> "GeminiProviderConfig":
        provider = os.getenv("FIBI_PROVIDER", "ollama").strip().lower()
        if provider not in {"ollama", "gemini", "local", "auto"}:
            provider = "ollama"
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key.upper() == "YOUR_GEMINI_API_KEY_HERE":
            api_key = ""
        return cls(
            selected_provider=provider,
            api_key=api_key,
            model=os.getenv("FIBI_GEMINI_MODEL", "gemini-3.1-flash-lite").strip(),
            timeout_seconds=_env_int("FIBI_GEMINI_TIMEOUT_SECONDS", 8, 3, 30),
            fallback_to_ollama=_env_bool("FIBI_GEMINI_FALLBACK_TO_OLLAMA", True),
            streaming=_env_bool("FIBI_GEMINI_STREAMING", True),
            context_preview=_env_bool("FIBI_CLOUD_CONTEXT_PREVIEW", True),
            google_search=_env_bool("FIBI_GEMINI_GOOGLE_SEARCH", True),
            thinking_level="minimal",
        )


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    prompt_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider: str
    selected: bool
    configured: bool
    sdk_available: bool
    model: str
    availability: str
    fallback_enabled: bool
    streaming_enabled: bool
    context_preview_enabled: bool
    last_error: str = ""
    health_state: str = "unknown"
    last_error_category: str = ""
    retry_after_seconds: int = 0
    last_retry_count: int = 0
    candidate_models: tuple[str, ...] = ()
    google_search_enabled: bool = False
    thinking_level: str = "minimal"


@dataclass(frozen=True, slots=True)
class CloudContextPreview:
    """Category-level preview; it intentionally contains no prompt content."""

    user_message_included: bool = True
    personality_included: bool = True
    recent_turn_count: int = 0
    approved_memory_summary_count: int = 0
    raw_memory_database_included: bool = False
    browser_private_data_included: bool = False
    project_files_included: bool = False
    logs_and_reports_included: bool = False
    secrets_included: bool = False

    def format(self) -> str:
        return (
            "Cloud request preview:\n"
            f"- Current user message: {'included' if self.user_message_included else 'excluded'}\n"
            f"- Fibi personality instructions: {'included' if self.personality_included else 'excluded'}\n"
            f"- Recent conversation turns: {self.recent_turn_count}\n"
            f"- Approved memory summaries: {self.approved_memory_summary_count}\n"
            "- Raw memory database: excluded\n"
            "- Browser history/cookies/passwords: excluded\n"
            "- Project source files: excluded\n"
            "- Logs and reports: excluded\n"
            "- API keys and secrets: excluded"
        )


@dataclass(frozen=True, slots=True)
class ProviderBenchmarkResult:
    provider: str
    model: str
    latency_ms: float
    ok: bool
    fallback_used: bool = False
    error_category: str = ""
