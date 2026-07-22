"""Lifecycle owner for one composed Fibi application instance."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import RLock
from typing import TYPE_CHECKING, Any

from fibi.app.contracts import CoreRuntime
from fibi.environment import EnvironmentStatus
from fibi.runtime_paths import RuntimePathInfo

if TYPE_CHECKING:
    from fibi.app.composition import ApplicationServices

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    """Secret-free configuration resolved once at the application boundary."""

    paths: RuntimePathInfo
    environment: EnvironmentStatus
    gui_smoke: bool = False

    def __repr__(self) -> str:
        return (
            "RuntimeConfiguration("
            f"packaged={self.paths.packaged!r}, portable={self.paths.portable!r}, "
            f"user_data_dir={str(self.paths.user_data_dir)!r}, "
            f"environment_source={self.environment.source!r}, "
            f"gemini_key_configured={self.environment.gemini_key_configured!r}, "
            f"gui_smoke={self.gui_smoke!r})"
        )


@dataclass(slots=True)
class ApplicationRuntime:
    """Own one service graph and coordinate its lifecycle exactly once."""

    configuration: RuntimeConfiguration
    services: ApplicationServices
    core: CoreRuntime
    _started: bool = field(default=False, init=False, repr=False)
    _shutdown: bool = field(default=False, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    @property
    def started(self) -> bool:
        return self._started

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    def start(self) -> bool:
        """Mark this runtime active; feature workers remain opt-in."""

        with self._lock:
            if self._shutdown:
                raise RuntimeError("cannot restart a shut down Fibi runtime")
            if self._started:
                return False
            self._started = True
            LOGGER.info("Fibi application runtime started")
            return True

    def shutdown(self) -> bool:
        """Release the core-owned resources once, even after repeated calls."""

        with self._lock:
            if self._shutdown:
                return False
            self._shutdown = True
        try:
            self.core.shutdown()
        except Exception:
            LOGGER.exception("Fibi application runtime shutdown failed")
        finally:
            self.services.stop_partial()
        LOGGER.info("Fibi application runtime stopped")
        return True

    def duplicate_service_diagnostic(self) -> dict[str, Any]:
        """Verify the core uses the singleton services built by composition."""

        checks = {
            "memory": getattr(self.core, "memory", None) is self.services.memory,
            "legacy_provider_router": getattr(self.core, "model_router", None) is self.services.model_router,
            "provider_registry": getattr(self.core, "provider_registry", None) is self.services.provider_registry,
            "provider_selection": getattr(self.core, "provider_selection", None) is self.services.provider_selection,
            "provider_generation": getattr(self.core, "generation_service", None) is self.services.generation_service,
            "provider_diagnostics": getattr(self.core, "provider_diagnostics", None) is self.services.provider_diagnostics,
            "tts": getattr(self.core, "tts_manager", None) is self.services.tts_manager,
            "actions": getattr(self.core, "desktop_actions", None) is self.services.desktop_actions,
            "project": getattr(self.core, "project_workspace", None) is self.services.project_workspace,
            "stt": getattr(self.core, "speech_recognition", None) is self.services.speech_recognition,
        }
        return {"ok": all(checks.values()), "checks": checks}
