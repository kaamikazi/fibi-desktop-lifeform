"""Execute safe direct desktop actions for Fibi v0.12."""

from __future__ import annotations

import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.types import ActionIntent, DesktopActionResult


class DesktopActionEngine:
    """Run only safe, direct, local actions."""

    def __init__(
        self,
        app_index: AppIndexEngine | None = None,
        browser_open: Callable[[str], bool] | None = None,
        app_launcher: Callable[[str], None] | None = None,
    ) -> None:
        self.app_index = app_index or AppIndexEngine()
        self.browser_open = browser_open or webbrowser.open_new_tab
        self.app_launcher = app_launcher or self._default_launch

    def execute(self, intent: ActionIntent) -> DesktopActionResult:
        action = intent.action_type
        if action == "open_website":
            return self._open_url(self._safe_url(intent.target), action, intent.target, "internet hole opened.")
        if action == "web_search":
            return self._open_url(
                f"https://www.google.com/search?q={quote_plus(intent.query)}",
                action,
                intent.query,
                "search hole opened.",
            )
        if action == "youtube_search":
            return self._open_url(
                f"https://www.youtube.com/results?search_query={quote_plus(intent.query)}",
                action,
                intent.query,
                "youtube tunnel opened.",
            )
        if action == "wikipedia_search":
            return self._open_url(
                f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(intent.query)}",
                action,
                intent.query,
                "wiki crumbs opened.",
            )
        if action == "tell_time":
            return DesktopActionResult(True, datetime.now().strftime("it is %I:%M %p.").replace(" 0", " "), action)
        if action == "tell_date":
            return DesktopActionResult(True, datetime.now().strftime("today is %A, %B %d, %Y.").replace(" 0", " "), action)
        if action in {"volume_up", "volume_down", "mute", "unmute"}:
            return self._media_key(action)
        if action == "open_app":
            return self._open_app(intent.target)
        if action == "open_folder":
            return self._open_folder(intent.target)
        if action == "refresh_app_index":
            count = self.app_index.refresh()
            return DesktopActionResult(True, f"app crumbs refreshed. found {count} creatures.", action)
        if action == "list_known_apps":
            count = self.app_index.count()
            return DesktopActionResult(True, f"i know {count} app creatures.", action)
        if action == "search_known_apps":
            result = self.app_index.search(intent.query or intent.target)
            if not result.matches:
                return DesktopActionResult(False, "couldn't find that creature.", action, intent.query)
            names = ", ".join(entry.display_name for entry in result.matches[:3])
            return DesktopActionResult(True, f"i know {names}.", action, intent.query)
        return DesktopActionResult(False, "not touching that yet.", action, intent.target or intent.query, error="unsupported")

    def _open_url(self, url: str, action: str, target: str, message: str) -> DesktopActionResult:
        if not url.startswith(("http://", "https://")):
            return DesktopActionResult(False, "that internet hole looks weird.", action, target, error="unsafe url")
        try:
            self.browser_open(url)
            return DesktopActionResult(True, message, action, target)
        except Exception as exc:
            return DesktopActionResult(False, "browser creature resisted.", action, target, error=str(exc))

    def _open_app(self, target: str) -> DesktopActionResult:
        search = self.app_index.search(target, limit=1)
        if not search.matches:
            return DesktopActionResult(False, "couldn't find that creature.", "open_app", target, error="not indexed")
        entry = search.matches[0]
        path = Path(entry.path)
        if path.suffix.lower() not in {".exe", ".lnk"}:
            return DesktopActionResult(False, "unknown launch shape.", "open_app", target, error="unsupported extension")
        if not path.exists():
            return DesktopActionResult(False, "app path vanished.", "open_app", target, error="missing path")
        try:
            self.app_launcher(str(path))
            return DesktopActionResult(True, "app creature summoned.", "open_app", entry.display_name)
        except Exception as exc:
            return DesktopActionResult(False, "app creature resisted.", "open_app", target, error=str(exc))

    def _open_folder(self, target: str) -> DesktopActionResult:
        path = Path(target).expanduser()
        if not path.exists() or not path.is_dir():
            return DesktopActionResult(False, "folder crumb missing.", "open_folder", target, error="missing folder")
        try:
            self.app_launcher(str(path))
            return DesktopActionResult(True, "folder opened.", "open_folder", str(path))
        except Exception as exc:
            return DesktopActionResult(False, "folder resisted.", "open_folder", str(path), error=str(exc))

    @staticmethod
    def _media_key(action: str) -> DesktopActionResult:
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return DesktopActionResult(False, "volume buttons missing.", action, error="pyautogui unavailable")
        key = {
            "volume_up": "volumeup",
            "volume_down": "volumedown",
            "mute": "volumemute",
            "unmute": "volumemute",
        }[action]
        try:
            pyautogui.press(key)
            return DesktopActionResult(True, "tiny volume push.", action)
        except Exception as exc:
            return DesktopActionResult(False, "volume creature resisted.", action, error=str(exc))

    @staticmethod
    def _safe_url(target: str) -> str:
        if target.startswith(("http://", "https://")):
            return target
        return "https://" + target.strip()

    @staticmethod
    def _default_launch(path: str) -> None:
        if hasattr(os, "startfile"):
            os.startfile(path)  # type: ignore[attr-defined]
            return
        raise RuntimeError("app launching is only supported on Windows")
