"""Optional Windows startup-folder autostart."""

from __future__ import annotations

import os
from pathlib import Path

from fibi.engines.types import AutostartState


class AutostartEngine:
    """Use the user's Startup folder with a small cmd launcher."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2])
        self.startup_dir = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        self.launcher_path = self.startup_dir / "Fibi.cmd"

    def status(self) -> AutostartState:
        return AutostartState(
            self.launcher_path.exists(),
            "startup_folder",
            str(self.launcher_path),
            None if self.startup_dir.exists() else "startup folder unavailable",
        )

    def enable(self, confirm: bool = False) -> AutostartState:
        if not confirm:
            return AutostartState(False, "startup_folder", str(self.launcher_path), "confirm required")
        try:
            self.startup_dir.mkdir(parents=True, exist_ok=True)
            command = f'@echo off\r\ncd /d "{self.project_root}"\r\npython app.py\r\n'
            self.launcher_path.write_text(command, encoding="utf-8")
            return self.status()
        except OSError as error:
            return AutostartState(False, "startup_folder", str(self.launcher_path), str(error))

    def disable(self) -> AutostartState:
        try:
            if self.launcher_path.exists():
                self.launcher_path.unlink()
            return self.status()
        except OSError as error:
            return AutostartState(False, "startup_folder", str(self.launcher_path), str(error))
