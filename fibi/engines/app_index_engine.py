"""Local app index for safe known-app launching."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping

from fibi.engines.types import AppIndexEntry, AppSearchResult
from fibi.paths import data_path

APP_INDEX_PATH = data_path("app_index.json")

KNOWN_WINDOWS_APPS: dict[str, dict[str, object]] = {
    "vscode": {
        "display": "VS Code",
        "aliases": ("vs code", "vscode", "visual studio code", "code", "code.exe"),
        "commands": ("code", "Code.exe"),
        "locations": (
            ("LOCALAPPDATA", "Programs/Microsoft VS Code/Code.exe"),
            ("ProgramFiles", "Microsoft VS Code/Code.exe"),
            ("ProgramFiles(x86)", "Microsoft VS Code/Code.exe"),
        ),
    },
    "teams": {
        "display": "Teams",
        "aliases": ("teams", "microsoft teams", "ms teams", "ms-teams", "msteams"),
        "commands": ("ms-teams", "msteams", "ms-teams.exe", "msteams.exe"),
        "locations": (
            ("LOCALAPPDATA", "Microsoft/WindowsApps/ms-teams.exe"),
            ("LOCALAPPDATA", "Microsoft/WindowsApps/msteams.exe"),
            ("ProgramFiles", "WindowsApps/MSTeams_*/msteams.exe"),
        ),
        "app_id": "shell:AppsFolder\\MSTeams_8wekyb3d8bbwe!MSTeams",
    },
    "chrome": {
        "display": "Chrome", "aliases": ("chrome", "google chrome", "chrome.exe"),
        "commands": ("chrome", "chrome.exe"),
        "locations": (("ProgramFiles", "Google/Chrome/Application/chrome.exe"), ("ProgramFiles(x86)", "Google/Chrome/Application/chrome.exe"), ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe")),
    },
    "edge": {
        "display": "Edge", "aliases": ("edge", "microsoft edge", "msedge", "msedge.exe"),
        "commands": ("msedge", "msedge.exe"),
        "locations": (("ProgramFiles", "Microsoft/Edge/Application/msedge.exe"), ("ProgramFiles(x86)", "Microsoft/Edge/Application/msedge.exe")),
    },
    "notepad": {
        "display": "Notepad", "aliases": ("notepad", "notepad.exe"),
        "commands": ("notepad", "notepad.exe"),
        "locations": (("SystemRoot", "System32/notepad.exe"),),
    },
    "calculator": {
        "display": "Calculator", "aliases": ("calculator", "calc", "calc.exe"),
        "commands": ("calc", "calc.exe"),
        "locations": (("SystemRoot", "System32/calc.exe"),),
        "app_id": "shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
    },
    "explorer": {
        "display": "File Explorer", "aliases": ("file explorer", "explorer", "explorer.exe"),
        "commands": ("explorer", "explorer.exe"),
        "locations": (("SystemRoot", "explorer.exe"),),
    },
    "powershell": {
        "display": "PowerShell", "aliases": ("powershell", "windows powershell", "powershell.exe"),
        "commands": ("powershell", "powershell.exe"),
        "locations": (("SystemRoot", "System32/WindowsPowerShell/v1.0/powershell.exe"),),
    },
    "terminal": {
        "display": "Terminal", "aliases": ("terminal", "windows terminal", "wt", "wt.exe"),
        "commands": ("wt", "wt.exe"),
        "locations": (("LOCALAPPDATA", "Microsoft/WindowsApps/wt.exe"),),
        "app_id": "shell:AppsFolder\\Microsoft.WindowsTerminal_8wekyb3d8bbwe!App",
    },
}
TRUSTED_APP_IDS = {
    str(config["app_id"])
    for config in KNOWN_WINDOWS_APPS.values()
    if config.get("app_id")
}


def normalize_app_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class AppIndexEngine:
    """Build and search a local allowlist of apps Fibi may open."""

    def __init__(
        self,
        index_path: Path | None = None,
        *,
        which_lookup: Callable[[str], str | None] | None = None,
        environment: Mapping[str, str] | None = None,
        start_menu_roots: list[Path] | None = None,
    ) -> None:
        self.index_path = Path(index_path) if index_path is not None else data_path("app_index.json")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.which_lookup = which_lookup or shutil.which
        self.environment = dict(environment) if environment is not None else dict(os.environ)
        self.start_menu_roots = start_menu_roots
        self.entries = self._load()

    def _load(self) -> list[AppIndexEntry]:
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        entries = []
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and item.get("path"):
                entries.append(AppIndexEntry(**{**asdict(AppIndexEntry("", "", "", "")), **item}))
        return entries

    def save(self) -> None:
        self.index_path.write_text(
            json.dumps([asdict(entry) for entry in self.entries], indent=2),
            encoding="utf-8",
        )

    def add_entry(self, display_name: str, path: str, source: str = "manual", confidence: float = 1.0) -> AppIndexEntry:
        entry = AppIndexEntry(
            display_name=display_name,
            normalized_name=normalize_app_name(display_name),
            path=str(path),
            source=source,
            confidence=confidence,
            last_seen_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        self.entries = [old for old in self.entries if old.normalized_name != entry.normalized_name]
        self.entries.append(entry)
        self.save()
        return entry

    def remove_entry(self, display_name: str) -> bool:
        normalized = normalize_app_name(display_name)
        before = len(self.entries)
        self.entries = [entry for entry in self.entries if entry.normalized_name != normalized]
        if len(self.entries) == before:
            return False
        self.save()
        return True

    def manual_entries(self) -> list[AppIndexEntry]:
        return sorted(
            (entry for entry in self.entries if entry.source == "manual"),
            key=lambda entry: entry.display_name.lower(),
        )

    def register_manual(self, display_name: str, path: str | Path) -> tuple[bool, str]:
        name = display_name.strip()
        if not name or len(name) > 80 or any(token in name for token in ("/", "\\", ":", "--")):
            return False, "Enter a plain application name without paths or arguments."
        valid, result = self.validate_manual_executable(path)
        if not valid:
            return False, result
        self.add_entry(name, result, "manual", 1.0)
        return True, f"{name} registered."

    @staticmethod
    def validate_manual_executable(path: str | Path) -> tuple[bool, str]:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            return False, "Choose an absolute executable path."
        if candidate.suffix.lower() != ".exe":
            return False, "Only .exe application files can be registered."
        if not candidate.exists() or not candidate.is_file():
            return False, "Executable file was not found."
        return True, str(candidate.resolve())

    def resolve_app(self, query: str) -> AppIndexEntry | None:
        """Resolve a safe app without accepting executable paths from chat text."""

        if not query.strip() or any(token in query for token in ("/", "\\", ":")):
            return None
        normalized = normalize_app_name(query)
        registered = next(
            (entry for entry in self.entries if entry.normalized_name == normalized and self._entry_valid(entry)),
            None,
        )
        if registered:
            return registered

        app_key = self._known_app_key(normalized)
        if app_key is None:
            return None
        config = KNOWN_WINDOWS_APPS[app_key]
        display = str(config["display"])
        aliases = {normalize_app_name(str(alias)) for alias in config.get("aliases", ())}
        registered_alias = next(
            (
                entry
                for entry in self.entries
                if entry.normalized_name in aliases and self._entry_valid(entry)
            ),
            None,
        )
        if registered_alias:
            return registered_alias

        for command in config.get("commands", ()):
            resolved = self.which_lookup(str(command))
            if resolved and self._executable_exists(resolved):
                return self._resolved_entry(display, resolved, "path")

        for variable, relative in config.get("locations", ()):
            root = self.environment.get(str(variable), "")
            if not root:
                continue
            candidates = list(Path(root).glob(str(relative))) if "*" in str(relative) else [Path(root) / Path(str(relative))]
            for candidate in candidates:
                if candidate.exists() and candidate.is_file() and candidate.suffix.lower() == ".exe":
                    return self._resolved_entry(display, str(candidate.resolve()), "known-location")

        start_menu = self._find_start_menu_entry(config)
        if start_menu:
            return self._resolved_entry(display, str(start_menu), "start-menu")

        app_id = str(config.get("app_id", ""))
        if app_id in TRUSTED_APP_IDS:
            return self._resolved_entry(display, app_id, "windows-app-id")
        return None

    def display_name_for(self, query: str) -> str:
        key = self._known_app_key(normalize_app_name(query))
        return str(KNOWN_WINDOWS_APPS[key]["display"]) if key else query.strip() or "Application"

    def refresh(self) -> int:
        """Scan common Windows app locations without entering documents deeply."""
        found: dict[str, AppIndexEntry] = {}
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for root in self._scan_roots():
            if not root.exists():
                continue
            for path in self._safe_walk(root):
                resolved = self._resolve_shortcut(path) if path.suffix.lower() == ".lnk" else path
                if resolved is None:
                    continue
                name = path.stem
                normalized = normalize_app_name(name)
                if not normalized:
                    continue
                found[normalized] = AppIndexEntry(
                    name,
                    normalized,
                    str(resolved),
                    str(root),
                    0.8 if path.suffix.lower() == ".lnk" else 0.7,
                    now,
                )
        manual = {entry.normalized_name: entry for entry in self.entries if entry.source == "manual"}
        found.update(manual)
        self.entries = sorted(found.values(), key=lambda entry: entry.display_name.lower())
        self.save()
        return len(self.entries)

    def search(self, query: str, limit: int = 5) -> AppSearchResult:
        normalized = normalize_app_name(query)
        if not normalized:
            return AppSearchResult([], query)
        scored: list[tuple[int, AppIndexEntry]] = []
        for entry in self.entries:
            name = entry.normalized_name
            if normalized == name:
                score = 100
            elif normalized in name:
                score = 80
            elif all(part in name for part in normalized.split()):
                score = 60
            else:
                score = self._subsequence_score(normalized, name)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1].display_name.lower()))
        return AppSearchResult([entry for _, entry in scored[:limit]], query)

    def count(self) -> int:
        return len(self.entries)

    def _scan_roots(self) -> list[Path]:
        roots = [
            Path(os.getenv("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
            Path.home() / r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
            Path.home() / "Desktop",
            Path(os.getenv("PUBLIC", r"C:\Users\Public")) / "Desktop",
            Path(os.getenv("ProgramFiles", r"C:\Program Files")),
            Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ]
        return roots

    def _start_menu_roots(self) -> list[Path]:
        if self.start_menu_roots is not None:
            return self.start_menu_roots
        return self._scan_roots()[:2]

    def _find_start_menu_entry(self, config: dict[str, object]) -> Path | None:
        aliases = {normalize_app_name(str(alias)) for alias in config.get("aliases", ())}
        for root in self._start_menu_roots():
            if not root.exists():
                continue
            for shortcut in self._safe_walk(root):
                if shortcut.suffix.lower() != ".lnk":
                    continue
                name = normalize_app_name(shortcut.stem)
                if not any(alias == name or alias in name for alias in aliases):
                    continue
                resolved = self._resolve_shortcut(shortcut)
                if resolved and resolved.exists() and resolved.suffix.lower() in {".exe", ".lnk"}:
                    return resolved
        return None

    @staticmethod
    def _resolved_entry(display: str, target: str, source: str) -> AppIndexEntry:
        return AppIndexEntry(
            display,
            normalize_app_name(display),
            target,
            source,
            0.95,
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )

    @staticmethod
    def _known_app_key(normalized_query: str) -> str | None:
        for key, config in KNOWN_WINDOWS_APPS.items():
            aliases = {normalize_app_name(str(alias)) for alias in config.get("aliases", ())}
            if normalized_query in aliases:
                return key
        return None

    @staticmethod
    def _executable_exists(path: str) -> bool:
        candidate = Path(path)
        return candidate.exists() and candidate.is_file() and candidate.suffix.lower() in {".exe", ".lnk"}

    @staticmethod
    def _entry_valid(entry: AppIndexEntry) -> bool:
        if entry.source == "windows-app-id":
            return entry.path in TRUSTED_APP_IDS
        return AppIndexEngine._executable_exists(entry.path)

    @staticmethod
    def _safe_walk(root: Path) -> list[Path]:
        matches: list[Path] = []
        try:
            for current, dirs, files in os.walk(root):
                depth = len(Path(current).relative_to(root).parts)
                if depth > 2:
                    dirs[:] = []
                    continue
                for filename in files:
                    path = Path(current) / filename
                    if path.suffix.lower() in {".lnk", ".exe"}:
                        matches.append(path)
        except OSError:
            return matches
        return matches

    @staticmethod
    def _resolve_shortcut(path: Path) -> Path | None:
        try:
            import win32com.client  # type: ignore
        except ImportError:
            return path
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(path))
            target = Path(shortcut.Targetpath)
            return (
                target
                if shortcut.Targetpath and target.is_file() and target.suffix.lower() in {".exe", ".lnk"}
                else path
            )
        except Exception:
            return path

    @staticmethod
    def _subsequence_score(needle: str, haystack: str) -> int:
        index = 0
        for char in haystack:
            if index < len(needle) and needle[index] == char:
                index += 1
        return 40 if index == len(needle) and len(needle) >= 3 else 0
