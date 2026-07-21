"""Execute safe direct desktop actions for Fibi v0.12."""

from __future__ import annotations

import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus
from urllib.parse import urlparse

from fibi.engines.action_allowlists import ALLOWED_WEB_HOSTS, SAFE_COMMANDS, contains_secret_marker, named_user_folders
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.paths import data_path
from fibi.engines.types import ActionIntent, DesktopActionResult


class DesktopActionEngine:
    """Run only safe, direct, local actions."""

    def __init__(
        self,
        app_index: AppIndexEngine | None = None,
        browser_open: Callable[[str], bool] | None = None,
        app_launcher: Callable[[str], None] | None = None,
        clipboard_writer: Callable[[str], None] | None = None,
        keyboard_writer: Callable[[str], None] | None = None,
        screenshot_taker: Callable[[Path], None] | None = None,
        command_runner: Callable[[tuple[str, ...], Path], tuple[int, str, str]] | None = None,
        project_launcher: Callable[[str, str], None] | None = None,
    ) -> None:
        self.app_index = app_index or AppIndexEngine()
        self.browser_open = browser_open or webbrowser.open_new_tab
        self.app_launcher = app_launcher or self._default_launch
        self.clipboard_writer = clipboard_writer or self._default_copy
        self.keyboard_writer = keyboard_writer or self._default_type
        self.screenshot_taker = screenshot_taker or self._default_screenshot
        self.command_runner = command_runner or self._default_command
        self.project_launcher = project_launcher or self._default_project_launch
        self.allowed_folder_roots = {path for path in named_user_folders().values()}

    def register_allowed_path(self, path: str | Path) -> None:
        """Allow one user-registered project root for later manual actions."""

        self.allowed_folder_roots.add(Path(path).expanduser().resolve())

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
        if action == "open_project_vscode":
            return self._open_project_vscode(intent.target)
        if action == "copy_text":
            return self._copy_text(intent.target)
        if action == "type_text":
            return self._type_text(intent.target)
        if action == "create_folder":
            return self._create_folder(intent.target)
        if action == "run_safe_command":
            return self._run_safe_command(intent.target, intent.query)
        if action == "screenshot":
            return self._take_screenshot()
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
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in ALLOWED_WEB_HOSTS:
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
        path = Path(target).expanduser().resolve()
        if not self._path_allowed(path):
            return DesktopActionResult(False, "folder is outside the allowlist.", "open_folder", target, error="path not allowlisted")
        if not path.exists() or not path.is_dir():
            return DesktopActionResult(False, "folder crumb missing.", "open_folder", target, error="missing folder")
        try:
            self.app_launcher(str(path))
            return DesktopActionResult(True, "folder opened.", "open_folder", str(path))
        except Exception as exc:
            return DesktopActionResult(False, "folder resisted.", "open_folder", str(path), error=str(exc))

    def _open_project_vscode(self, target: str) -> DesktopActionResult:
        project = Path(target).expanduser().resolve()
        if not self._path_allowed(project) or not project.is_dir():
            return DesktopActionResult(False, "project is not registered.", "open_project_vscode", target, error="path not allowlisted")
        search = self.app_index.search("visual studio code", limit=1)
        if not search.matches:
            search = self.app_index.search("vscode", limit=1)
        if not search.matches:
            search = self.app_index.search("code", limit=1)
        if not search.matches:
            return DesktopActionResult(False, "VS Code is not in the app index.", "open_project_vscode", target, error="vscode not indexed")
        executable = Path(search.matches[0].path)
        if executable.suffix.lower() != ".exe" or not executable.exists():
            return DesktopActionResult(False, "VS Code path is unavailable.", "open_project_vscode", target, error="invalid vscode path")
        try:
            self.project_launcher(str(executable), str(project))
            return DesktopActionResult(True, "registered project opened in VS Code.", "open_project_vscode", str(project))
        except Exception as exc:
            return DesktopActionResult(False, "VS Code resisted.", "open_project_vscode", str(project), error=str(exc))

    def _copy_text(self, text: str) -> DesktopActionResult:
        if not text:
            return DesktopActionResult(False, "tell me which text to copy.", "copy_text", error="missing text")
        if len(text) > 4000 or contains_secret_marker(text):
            return DesktopActionResult(False, "that text looks sensitive or too large.", "copy_text", error="unsafe text")
        try:
            self.clipboard_writer(text)
            return DesktopActionResult(True, "text copied to clipboard.", "copy_text", "[user-approved text]")
        except Exception as exc:
            return DesktopActionResult(False, "clipboard resisted.", "copy_text", error=str(exc))

    def _type_text(self, text: str) -> DesktopActionResult:
        if not text or len(text) > 1000 or contains_secret_marker(text):
            return DesktopActionResult(False, "approved typing text is missing or unsafe.", "type_text", error="unsafe text")
        try:
            self.keyboard_writer(text)
            return DesktopActionResult(True, "approved text typed.", "type_text", "[user-approved text]")
        except Exception as exc:
            return DesktopActionResult(False, "keyboard control resisted.", "type_text", error=str(exc))

    def _create_folder(self, target: str) -> DesktopActionResult:
        path = Path(target).expanduser().resolve()
        if not self._path_allowed(path) or path.parent == path or any(part in {"..", "."} for part in Path(target).parts):
            return DesktopActionResult(False, "folder path is outside the allowlist.", "create_folder", target, error="path not allowlisted")
        if path.exists():
            return DesktopActionResult(False, "that folder already exists.", "create_folder", str(path), error="already exists")
        try:
            path.mkdir(parents=False, exist_ok=False)
            return DesktopActionResult(True, "folder created.", "create_folder", str(path))
        except Exception as exc:
            return DesktopActionResult(False, "folder creation failed.", "create_folder", str(path), error=str(exc))

    def _run_safe_command(self, command: str, working_directory: str) -> DesktopActionResult:
        args = SAFE_COMMANDS.get(command)
        if args is None:
            return DesktopActionResult(False, "command is not allowlisted.", "run_safe_command", command, error="command not allowlisted")
        cwd = Path(working_directory).expanduser().resolve() if working_directory else Path.cwd().resolve()
        if working_directory and not self._path_allowed(cwd):
            return DesktopActionResult(False, "command folder is not registered.", "run_safe_command", command, error="path not allowlisted")
        try:
            code, stdout, stderr = self.command_runner(args, cwd)
            summary = (stdout or stderr).strip().replace("\n", " ")[:180]
            if code == 0:
                return DesktopActionResult(True, f"safe command completed. {summary}".strip(), "run_safe_command", command)
            return DesktopActionResult(False, "safe command failed.", "run_safe_command", command, error=summary or f"exit {code}")
        except Exception as exc:
            return DesktopActionResult(False, "safe command failed.", "run_safe_command", command, error=str(exc))

    def _take_screenshot(self) -> DesktopActionResult:
        path = data_path("screenshots") / datetime.now().strftime("fibi_%Y%m%d_%H%M%S.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.screenshot_taker(path)
            return DesktopActionResult(True, f"screenshot saved locally: {path}", "screenshot", str(path))
        except Exception as exc:
            return DesktopActionResult(False, "screenshot failed.", "screenshot", error=str(exc))

    def _path_allowed(self, path: Path) -> bool:
        for root in self.allowed_folder_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False

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

    @staticmethod
    def _default_copy(text: str) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            raise RuntimeError("clipboard requires the running Fibi application")
        app.clipboard().setText(text)

    @staticmethod
    def _default_type(text: str) -> None:
        import pyautogui  # type: ignore

        pyautogui.write(text, interval=0.01)

    @staticmethod
    def _default_screenshot(path: Path) -> None:
        import pyautogui  # type: ignore

        pyautogui.screenshot(str(path))

    @staticmethod
    def _default_command(args: tuple[str, ...], cwd: Path) -> tuple[int, str, str]:
        completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=10, shell=False, check=False)
        return completed.returncode, completed.stdout, completed.stderr

    @staticmethod
    def _default_project_launch(executable: str, project: str) -> None:
        subprocess.Popen([executable, project], close_fds=True)
