"""Execute safe direct desktop actions for Fibi v0.12."""

from __future__ import annotations

import os
import re
import subprocess
import webbrowser
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import quote_plus
from urllib.parse import urlparse

from fibi.engines.action_allowlists import ALLOWED_WEB_HOSTS, SAFE_COMMANDS, contains_secret_marker, named_user_folders
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.path_safety import canonical_path, contains_reparse_point, is_within
from fibi.paths import data_path
from fibi.engines.types import ActionErrorCategory, ActionIntent, DesktopActionResult


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
        file_searcher: Callable[[str], list[str]] | None = None,
        note_writer: Callable[[str], bool] | None = None,
        note_lister: Callable[[], list[str]] | None = None,
        work_session_starter: Callable[[str], str | None] | None = None,
    ) -> None:
        self.app_index = app_index or AppIndexEngine()
        self.browser_open = browser_open or webbrowser.open_new_tab
        self.app_launcher = app_launcher or self._default_launch
        self.clipboard_writer = clipboard_writer or self._default_copy
        self.keyboard_writer = keyboard_writer or self._default_type
        self.screenshot_taker = screenshot_taker or self._default_screenshot
        self.command_runner = command_runner or self._default_command
        self.project_launcher = project_launcher or self._default_project_launch
        self.file_searcher = file_searcher
        self.note_writer = note_writer
        self.note_lister = note_lister
        self.work_session_starter = work_session_starter
        self.allowed_folder_roots = {path.resolve() for path in named_user_folders().values()}

    def register_allowed_path(self, path: str | Path) -> bool:
        """Allow one user-registered project root for later manual actions."""

        candidate = Path(path).expanduser()
        if not candidate.exists() or not candidate.is_dir() or self._contains_reparse_point(candidate):
            return False
        self.allowed_folder_roots.add(candidate.resolve())
        return True

    def set_productivity_callbacks(
        self,
        *,
        file_searcher: Callable[[str], list[str]] | None = None,
        note_writer: Callable[[str], bool] | None = None,
        note_lister: Callable[[], list[str]] | None = None,
        work_session_starter: Callable[[str], str | None] | None = None,
    ) -> None:
        """Attach existing project/session owners after composition is complete."""

        self.file_searcher = file_searcher
        self.note_writer = note_writer
        self.note_lister = note_lister
        self.work_session_starter = work_session_starter

    def is_path_allowed(self, path: str | Path) -> bool:
        """Expose the existing allowlist for Core intent preparation."""

        return self._path_allowed(Path(path).expanduser())

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
        if action == "open_file":
            return self._open_file(intent.target)
        if action == "open_project":
            return self._open_project(intent.target, intent.query)
        if action == "open_project_vscode":
            return self._open_project_vscode(intent.target, intent.query)
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
                return self._failure("couldn't find that creature.", action, intent.query, "app_not_found")
            names = ", ".join(entry.display_name for entry in result.matches[:3])
            return DesktopActionResult(True, f"i know {names}.", action, self._safe_target(action, intent.query))
        if action == "search_files":
            return self._search_files(intent.query or intent.target)
        if action == "save_note":
            return self._save_note(intent.target)
        if action == "list_notes":
            return self._list_notes()
        if action == "start_work_session":
            return self._start_work_session(intent.target)
        return self._failure("not touching that yet.", action, intent.target or intent.query, "unsupported_action")

    def _open_url(self, url: str, action: str, target: str, message: str) -> DesktopActionResult:
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower().rstrip(".")
        except ValueError:
            return self._failure("that internet hole looks weird.", action, target, "unsafe_url")
        if (
            parsed.scheme not in {"http", "https"}
            or hostname not in ALLOWED_WEB_HOSTS
            or not parsed.netloc
        ):
            return self._failure("that internet hole looks weird.", action, target, "unsafe_url")
        try:
            opened = self.browser_open(url)
            if opened is False:
                return self._failure("browser creature resisted.", action, target, "browser_open_failed")
            return DesktopActionResult(
                True,
                message,
                action,
                self._safe_target(action, target),
                metadata={"host": hostname},
                reversible=True,
            )
        except Exception:
            return self._failure("browser creature resisted.", action, target, "browser_open_failed")

    def _open_app(self, target: str) -> DesktopActionResult:
        entry = self.app_index.resolve_app(target)
        if entry is None:
            name = self.app_index.display_name_for(target)
            if self._looks_like_local_path(target):
                message = "that application was not found. Register its path in Settings > Actions."
            else:
                message = f"{name[:80]} was not found. Register its path in Settings > Actions."
            return self._failure(message, "open_app", target, "app_not_found")
        try:
            self.app_launcher(entry.path)
            if entry.source in {"path", "known-location", "start-menu", "windows-app-id"}:
                self.app_index.add_entry(entry.display_name, entry.path, entry.source, entry.confidence)
            return DesktopActionResult(
                True,
                f"{entry.display_name} opened.",
                "open_app",
                entry.display_name,
                metadata={"source": entry.source},
            )
        except Exception:
            return self._failure(f"{entry.display_name} could not be opened.", "open_app", target, "app_launch_failed")

    def _open_folder(self, target: str) -> DesktopActionResult:
        path = Path(target).expanduser()
        if not self._path_allowed(path):
            return self._failure("folder is outside the allowlist.", "open_folder", target, "unsafe_path")
        path = path.resolve()
        if not path.exists() or not path.is_dir():
            return self._failure("folder crumb missing.", "open_folder", target, "folder_not_found")
        try:
            self.app_launcher(str(path))
            return DesktopActionResult(
                True,
                "folder opened.",
                "open_folder",
                "[approved folder]",
                reversible=True,
            )
        except Exception:
            return self._failure("folder resisted.", "open_folder", "[approved folder]", "folder_open_failed")

    def _open_file(self, target: str) -> DesktopActionResult:
        path = Path(target).expanduser()
        if not self._path_allowed(path):
            return self._failure("file is outside the allowlist.", "open_file", target, "unsafe_path")
        path = path.resolve()
        if self._secret_filename(path.name):
            return self._failure("secret files stay closed.", "open_file", path.name, "secret_file")
        if path.suffix.casefold() in {
            ".exe", ".com", ".bat", ".cmd", ".ps1", ".py", ".pyw",
            ".js", ".vbs", ".vbe", ".wsf", ".wsh", ".scr", ".msi",
            ".msp", ".lnk", ".url", ".reg", ".hta",
        }:
            return self._failure("use a registered application or editor for executable files.", "open_file", error_code="executable_file_blocked")
        if not path.exists() or not path.is_file():
            return self._failure("file crumb missing.", "open_file", target, "file_not_found")
        try:
            self.app_launcher(str(path))
            return DesktopActionResult(
                True,
                f"Opened file {path.name}.",
                "open_file",
                "[approved file]",
                reversible=True,
            )
        except Exception:
            return self._failure("file resisted.", "open_file", "[approved file]", "file_open_failed")

    def _open_project(self, target: str, project_name: str = "") -> DesktopActionResult:
        project = canonical_path(target)
        if project is None or not self._path_allowed(project) or not project.is_dir():
            return self._failure("project folder is missing or not registered.", "open_project", target, "project_not_found")
        try:
            self.app_launcher(str(project))
            label = project_name.strip() or project.name or "project"
            if self._looks_like_local_path(label):
                label = project.name or "project"
            return DesktopActionResult(
                True,
                f"Opened project {label}.",
                "open_project",
                "[registered project]",
                reversible=True,
            )
        except Exception:
            return self._failure("project folder could not be opened.", "open_project", "[registered project]", "project_open_failed")

    def _open_project_vscode(self, target: str, project_name: str = "") -> DesktopActionResult:
        project = canonical_path(target)
        if project is None or not self._path_allowed(project) or not project.is_dir():
            return self._failure("project is not registered.", "open_project_vscode", target, "unsafe_project_path")
        resolved = self.app_index.resolve_executable_app("vscode")
        if resolved is None or resolved.path.startswith("shell:AppsFolder"):
            message = "VS Code was not found. Register its path in Settings > Actions."
            return self._failure(message, "open_project_vscode", target, "vscode_not_found")
        executable = Path(resolved.path)
        if executable.suffix.lower() != ".exe" or not executable.exists() or contains_reparse_point(executable):
            return self._failure("VS Code path is unavailable.", "open_project_vscode", target, "invalid_vscode_path")
        try:
            self.project_launcher(str(executable), str(project))
            label = project_name.strip() or project.name or "project"
            if self._looks_like_local_path(label):
                label = project.name or "project"
            return DesktopActionResult(
                True,
                f"Opened {label} in VS Code.",
                "open_project_vscode",
                "[registered project]",
                metadata={"editor": "VS Code"},
                reversible=True,
            )
        except Exception:
            return self._failure("VS Code resisted.", "open_project_vscode", "[registered project]", "vscode_launch_failed")

    def _copy_text(self, text: str) -> DesktopActionResult:
        if not text:
            return self._failure("tell me which text to copy.", "copy_text", error_code="missing_text")
        if len(text) > 4000 or contains_secret_marker(text):
            return self._failure("that text looks sensitive or too large.", "copy_text", error_code="unsafe_text")
        try:
            self.clipboard_writer(text)
            return DesktopActionResult(True, "text copied to clipboard.", "copy_text", "[user-approved text]")
        except Exception as exc:
            return self._failure("clipboard resisted.", "copy_text", error_code="clipboard_write_failed")

    def _type_text(self, text: str) -> DesktopActionResult:
        if not text or len(text) > 1000 or contains_secret_marker(text):
            return self._failure("approved typing text is missing or unsafe.", "type_text", error_code="unsafe_text")
        try:
            self.keyboard_writer(text)
            return DesktopActionResult(True, "approved text typed.", "type_text", "[user-approved text]")
        except Exception as exc:
            return self._failure("keyboard control resisted.", "type_text", error_code="keyboard_write_failed")

    def _create_folder(self, target: str) -> DesktopActionResult:
        path = Path(target).expanduser()
        if not self._path_allowed(path) or path.parent == path or any(part in {"..", "."} for part in Path(target).parts):
            return self._failure("folder path is outside the allowlist.", "create_folder", target, "unsafe_path")
        path = path.resolve()
        if path.exists():
            return self._failure("that folder already exists.", "create_folder", str(path), "already_exists")
        try:
            path.mkdir(parents=False, exist_ok=False)
            return DesktopActionResult(True, "folder created.", "create_folder", "[approved folder]")
        except Exception as exc:
            return self._failure("folder creation failed.", "create_folder", path.name, "folder_create_failed")

    def _run_safe_command(self, command: str, working_directory: str) -> DesktopActionResult:
        args = SAFE_COMMANDS.get(command)
        if args is None:
            return self._failure("command is not allowlisted.", "run_safe_command", command, "command_not_allowlisted")
        cwd = Path(working_directory).expanduser().resolve() if working_directory else Path.cwd().resolve()
        if working_directory and not self._path_allowed(cwd):
            return self._failure("command folder is not registered.", "run_safe_command", command, "unsafe_working_directory")
        try:
            code, stdout, stderr = self.command_runner(args, cwd)
            if code == 0:
                return DesktopActionResult(True, "safe command completed.", "run_safe_command", command)
            return self._failure("safe command failed.", "run_safe_command", command, "command_failed")
        except Exception as exc:
            return self._failure("safe command failed.", "run_safe_command", command, "command_failed")

    def _take_screenshot(self) -> DesktopActionResult:
        path = data_path("screenshots") / datetime.now().strftime("fibi_%Y%m%d_%H%M%S.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.screenshot_taker(path)
            return DesktopActionResult(True, "screenshot saved locally.", "screenshot", "[local screenshot]")
        except Exception as exc:
            return self._failure("screenshot failed.", "screenshot", error_code="screenshot_failed")

    def _search_files(self, query: str) -> DesktopActionResult:
        clean_query = (query or "").strip()
        if not clean_query or len(clean_query) > 200 or contains_secret_marker(clean_query):
            return self._failure("file search query is missing or unsafe.", "search_files", error_code="unsafe_query")
        if self.file_searcher is None:
            return self._failure("register a project before searching its files.", "search_files", error_code="project_not_registered")
        try:
            matches = []
            for match in self.file_searcher(clean_query):
                safe_match = str(match).replace("\\", "/").strip()
                relative = PurePosixPath(safe_match)
                if (
                    not safe_match
                    or safe_match == "."
                    or relative.is_absolute()
                    or ".." in relative.parts
                    or ":" in safe_match[:3]
                    or self._secret_filename(relative.name)
                ):
                    continue
                matches.append(safe_match)
                if len(matches) >= 5:
                    break
        except Exception:
            return self._failure("file search is unavailable right now.", "search_files", error_code="file_search_failed")
        if not matches:
            return DesktopActionResult(True, "no safe project files matched.", "search_files", "[project files]")
        return DesktopActionResult(
            True,
            f"Found {len(matches)} safe project file{'s' if len(matches) != 1 else ''}: " + ", ".join(match[:120] for match in matches) + ".",
            "search_files",
            "[project files]",
            metadata={"match_count": str(len(matches))},
        )

    def _save_note(self, text: str) -> DesktopActionResult:
        clean_text = (text or "").strip()
        if not clean_text or len(clean_text) > 500 or contains_secret_marker(clean_text):
            return self._failure("that note is empty, too large, or looks sensitive.", "save_note", error_code="unsafe_note")
        if self.note_writer is None:
            return self._failure("notes need a registered project.", "save_note", error_code="project_not_registered")
        try:
            if not self.note_writer(clean_text):
                return self._failure("notes need a registered project.", "save_note", error_code="project_not_registered")
        except Exception:
            return self._failure("note could not be saved.", "save_note", error_code="note_write_failed")
        return DesktopActionResult(True, "Note saved to the current project.", "save_note", "[project note]")

    def _list_notes(self) -> DesktopActionResult:
        if self.note_lister is None:
            return self._failure("register a project before listing notes.", "list_notes", error_code="project_not_registered")
        try:
            notes = [self._safe_note_summary(note) for note in self.note_lister() if str(note).strip()]
        except Exception:
            return self._failure("recent notes are unavailable right now.", "list_notes", error_code="notes_read_failed")
        if not notes:
            return DesktopActionResult(True, "No recent project notes.", "list_notes", "[project notes]", metadata={"note_count": "0"}, reversible=True)
        return DesktopActionResult(
            True,
            "Recent notes: " + " | ".join(notes[:5]),
            "list_notes",
            "[project notes]",
            metadata={"note_count": str(min(len(notes), 5))},
            reversible=True,
        )

    def _start_work_session(self, goal: str) -> DesktopActionResult:
        clean_goal = (goal or "").strip()
        if not clean_goal or len(clean_goal) > 500:
            return self._failure("tell me the work-session goal.", "start_work_session", error_code="missing_goal")
        if self.work_session_starter is None:
            return self._failure("use /session start for a guided work session.", "start_work_session", error_code="session_unavailable")
        try:
            result = self.work_session_starter(clean_goal)
        except Exception:
            return self._failure("work session could not start.", "start_work_session", error_code="session_start_failed")
        if not result:
            return self._failure("work session could not start.", "start_work_session", error_code="session_start_failed")
        if str(result).lower().startswith("work session already active"):
            return self._failure(str(result)[:240], "start_work_session", "[work session]", "session_already_active")
        return DesktopActionResult(
            True,
            self._safe_note_summary(result),
            "start_work_session",
            "[work session]",
            reversible=True,
        )

    def _path_allowed(self, path: Path) -> bool:
        if self._contains_reparse_point(path):
            return False
        return any(is_within(root, path) for root in self.allowed_folder_roots)

    @staticmethod
    def _contains_reparse_point(path: Path) -> bool:
        """Reject symlink/junction chains before resolving a user path."""

        return contains_reparse_point(path)

    @staticmethod
    def _failure(message: str, action: str, target: str = "", error_code: str = "native_action_failed") -> DesktopActionResult:
        return DesktopActionResult(
            False,
            message,
            action,
            DesktopActionEngine._safe_target(action, target),
            error=error_code,
            error_code=error_code,
            error_category=DesktopActionEngine._error_category(error_code),
        )

    @staticmethod
    def _safe_target(action: str, target: str) -> str:
        """Keep private paths and action payloads out of result objects."""

        value = str(target or "")
        if action in {"open_folder", "open_file", "open_project", "open_project_vscode", "create_folder"}:
            return {
                "open_folder": "[approved folder]",
                "open_file": "[approved file]",
                "open_project": "[registered project]",
                "open_project_vscode": "[registered project]",
                "create_folder": "[approved folder]",
            }[action]
        if action == "copy_text" or action == "type_text":
            return "[user-approved text]"
        if action == "save_note":
            return "[project note]"
        if action == "list_notes":
            return "[project notes]"
        if DesktopActionEngine._looks_like_local_path(value):
            return "[application path]"
        return value[:160]

    @staticmethod
    def _looks_like_local_path(value: str) -> bool:
        clean = str(value or "").strip()
        return (
            (len(clean) > 2 and clean[1] == ":" and clean[2:3] in {"/", "\\"})
            or clean.startswith(("/", "\\\\"))
        )

    @staticmethod
    def _error_category(error_code: str) -> str:
        if error_code in {"app_not_found", "folder_not_found", "file_not_found", "project_not_found", "project_not_registered", "vscode_not_found", "notes_unavailable"}:
            return ActionErrorCategory.NOT_FOUND.value
        if error_code in {
            "unsafe_path",
            "unsafe_project_path",
            "unsafe_working_directory",
            "secret_file",
            "executable_file_blocked",
            "unsafe_text",
            "unsafe_note",
            "unsafe_query",
            "command_not_allowlisted",
            "invalid_vscode_path",
            "session_already_active",
            "permission_denied",
            "destructive_action_blocked",
            "already_exists",
        }:
            return ActionErrorCategory.NOT_ALLOWED.value
        if error_code in {"missing_text", "missing_goal", "invalid_action_context"}:
            return ActionErrorCategory.INVALID_INPUT.value
        if error_code == "confirmation_required":
            return ActionErrorCategory.CONFIRMATION_REQUIRED.value
        if error_code == "unsupported_action":
            return ActionErrorCategory.UNSUPPORTED.value
        return ActionErrorCategory.PLATFORM_ERROR.value

    @staticmethod
    def _safe_note_summary(note: object) -> str:
        """Keep note previews useful without echoing local absolute paths."""

        value = re.sub(r"\s+", " ", str(note).replace("\r", " ").replace("\n", " ")).strip()
        value = re.sub(r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^|,;]+", "[local path]", value)
        value = re.sub(r"(?<![A-Za-z0-9_])/(?:Users|home|private|tmp|var)/[^|,;\s]+", "[local path]", value, flags=re.IGNORECASE)
        return value[:180]

    @staticmethod
    def _secret_filename(name: str) -> bool:
        lowered = name.lower()
        return (
            lowered in {".env", ".env.local", ".env.production", ".env.development"}
            or lowered.endswith((".pem", ".key", ".p12", ".pfx", ".token", ".secret"))
            or lowered.startswith(("secret.", "secrets.", "credential.", "credentials."))
        )

    @staticmethod
    def _media_key(action: str) -> DesktopActionResult:
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return DesktopActionEngine._failure("volume buttons missing.", action, error_code="pyautogui_unavailable")
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
            return DesktopActionEngine._failure("volume creature resisted.", action, error_code="media_key_failed")

    @staticmethod
    def _safe_url(target: str) -> str:
        clean = (target or "").strip()
        if clean.lower().startswith(("http://", "https://")):
            return clean
        return "https://" + clean

    @staticmethod
    def _default_launch(path: str) -> None:
        if path.startswith("shell:AppsFolder\\") and os.name == "nt":
            subprocess.Popen(["explorer.exe", path], close_fds=True)
            return
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
