"""Asset health checks with optional fallbacks."""

from __future__ import annotations

from pathlib import Path

from fibi.engines.types import AssetHealthResult

PROJECT_DIR = Path(__file__).resolve().parents[1]
ASSET_DIRS = [PROJECT_DIR / "assets", PROJECT_DIR / "ui" / "assets"]
REQUIRED_EXPRESSIONS = ("idle", "happy", "thinking", "sleepy", "angry")
OPTIONAL_ASSETS = ("blink", "talking")


class AssetHealthEngine:
    def check(self) -> AssetHealthResult:
        checks: dict[str, bool] = {}
        for name in REQUIRED_EXPRESSIONS:
            checks[f"{name}_png"] = self._exists(f"{name}.png")
        for name in OPTIONAL_ASSETS:
            checks[f"{name}_optional"] = self._exists(f"{name}.png")
        checks["tray_icon_optional"] = self._exists("tray.png") or self._exists("idle.png")
        checks["sounds_optional"] = any((folder / "sounds").exists() for folder in ASSET_DIRS)
        required_ok = all(checks[f"{name}_png"] for name in REQUIRED_EXPRESSIONS)
        missing_optional = [key for key, ok in checks.items() if not ok and key.endswith("_optional")]
        message = "assets ok." if required_ok else "some expression crumbs missing."
        if missing_optional:
            message += " optional missing but fine."
        return AssetHealthResult(required_ok, message, checks)

    @staticmethod
    def _exists(filename: str) -> bool:
        return any((folder / filename).exists() for folder in ASSET_DIRS)
