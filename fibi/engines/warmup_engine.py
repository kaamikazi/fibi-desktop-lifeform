"""Background warmup helpers for Fibi."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class WarmupStatus:
    running: bool = False
    completed: bool = False
    failures: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class WarmupEngine:
    """Run optional startup checks after the UI can appear."""

    def __init__(self) -> None:
        self.status = WarmupStatus()

    def start(self, checks: list[tuple[str, Callable[[], object]]]) -> None:
        if self.status.running:
            return

        def worker() -> None:
            start = time.perf_counter()
            self.status.running = True
            for name, check in checks:
                try:
                    check()
                except Exception:
                    self.status.failures.append(name)
            self.status.duration_ms = (time.perf_counter() - start) * 1000
            self.status.running = False
            self.status.completed = True

        threading.Thread(target=worker, daemon=True).start()
