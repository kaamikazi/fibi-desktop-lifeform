"""Graceful shutdown coordination for Fibi."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from fibi.paths import data_path

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ShutdownReport:
    ok: bool
    message: str
    created_at: str
    error: str = ""


class ShutdownManager:
    """Persist shutdown markers and run safe shutdown callbacks."""

    def __init__(self, marker_path: Path | None = None) -> None:
        self.marker_path = Path(marker_path) if marker_path is not None else data_path("shutdown_marker.json")
        self.marker_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_error = ""

    def shutdown(self, callbacks: list[tuple[str, object]] | None = None) -> ShutdownReport:
        callbacks = callbacks or []
        errors: list[str] = []
        for name, callback in callbacks:
            try:
                if callable(callback):
                    callback()
            except Exception as exc:  # pragma: no cover - defensive boundary
                LOGGER.exception("shutdown_callback_failed", extra={"callback": name})
                errors.append(f"{name}: {exc}")
        report = ShutdownReport(
            ok=not errors,
            message="guarding paused." if not errors else "sleep mode with one squeak.",
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            error="; ".join(errors)[:500],
        )
        self.last_error = report.error
        self.marker_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        return report

    def last_marker(self) -> dict:
        try:
            return json.loads(self.marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
