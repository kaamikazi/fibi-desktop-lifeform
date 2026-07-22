"""Thread-safe, content-free provider diagnostics."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from threading import RLock

from fibi.services.providers.models import GenerationResult, ProviderDiagnosticsSnapshot


class ProviderDiagnostics:
    def __init__(self, selected_provider_id: str, configured: bool) -> None:
        self._lock = RLock()
        self._snapshot = ProviderDiagnosticsSnapshot.empty(selected_provider_id, configured)

    def record(
        self,
        result: GenerationResult,
        *,
        selected_configured: bool,
        fallback_enabled: bool,
        fallback_provider_id: str,
    ) -> ProviderDiagnosticsSnapshot:
        snapshot = ProviderDiagnosticsSnapshot(
            selected_provider_id=result.selected_provider_id,
            selected_provider_configured=selected_configured,
            last_attempted_provider_id=result.attempted_provider_id,
            last_active_provider_id=result.provider_id if result.success else "",
            last_model_id=result.model_id,
            last_success=result.success,
            last_error_category=result.error_category.value if result.error_category else "",
            last_latency_ms=result.latency_ms,
            retry_count=result.retry_count,
            fallback_enabled=fallback_enabled,
            fallback_provider_id=fallback_provider_id,
            fallback_used=result.fallback_used,
            search_grounding_used=result.search_grounding_used,
            timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        with self._lock:
            self._snapshot = snapshot
        return snapshot

    def selection_changed(self, provider_id: str, configured: bool) -> None:
        with self._lock:
            self._snapshot = replace(
                self._snapshot,
                selected_provider_id=provider_id,
                selected_provider_configured=configured,
                timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
            )

    def snapshot(self) -> ProviderDiagnosticsSnapshot:
        with self._lock:
            return self._snapshot
