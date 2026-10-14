"""Registered project workspace support for Fibi v0.15."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from fibi.engines.context_engine import ContextEngine
from fibi.engines.file_reader_engine import FileReaderEngine
from fibi.engines.path_safety import canonical_path, contains_reparse_point
from fibi.engines.project_scanner_engine import ProjectScannerEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import (
    FileDropResult,
    ProjectFileEntry,
    ProjectNote,
    ProjectScanResult,
    ProjectSummary,
    ProjectWorkspace,
    ProjectWorkspaceSettings,
)
from fibi.paths import data_path

PROJECT_WORKSPACES_PATH = data_path("project_workspaces.json")


class ProjectWorkspaceEngine:
    """Manage user-approved project folders without control/autonomy."""

    def __init__(
        self,
        store_path: Path | None = None,
        context: ContextEngine | None = None,
        scanner: ProjectScannerEngine | None = None,
        sanitizer: SecretSanitizer | None = None,
        settings: ProjectWorkspaceSettings | None = None,
    ) -> None:
        self.store_path = Path(store_path) if store_path is not None else data_path("project_workspaces.json")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.context = context or ContextEngine()
        self.sanitizer = sanitizer or SecretSanitizer()
        self.settings = settings or ProjectWorkspaceSettings()
        self.scanner = scanner or ProjectScannerEngine(
            self.sanitizer,
            self.settings.readable_file_limit_bytes,
            max_depth=self.settings.max_scan_depth,
            max_files=self.settings.max_scan_files,
            max_seconds=self.settings.max_scan_seconds,
        )
        self.file_reader = FileReaderEngine(self.context, self.settings.readable_file_limit_bytes)
        self.workspaces: list[ProjectWorkspace] = []
        self.current_project_id: str | None = None
        self.last_scan_files: dict[str, list[ProjectFileEntry]] = {}
        self._load()

    def add_workspace(self, path: str | Path, aliases: list[str] | None = None) -> ProjectScanResult:
        candidate = Path(path).expanduser()
        if self._contains_reparse_point(candidate):
            return ProjectScanResult(False, message="project path is not safe.", error="unsafe_link_or_reparse_point")
        root = canonical_path(candidate)
        if root is None:
            return ProjectScanResult(False, message="project path is not safe.", error="unsafe_link_or_reparse_point")
        if not root.exists() or not root.is_dir():
            return ProjectScanResult(False, message="project nest missing.", error="missing")
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        existing = self._find_by_path(root)
        workspace = existing or ProjectWorkspace(
            project_id=str(uuid.uuid4())[:12],
            name=root.name,
            root_path=str(root),
            created_at=now,
            last_opened_at=now,
            trusted=True,
            user_added=True,
        )
        if existing is None:
            self.workspaces.append(workspace)
        if aliases:
            workspace.aliases = sorted(
                {
                    *workspace.aliases,
                    *(alias.strip() for alias in aliases if alias and alias.strip()),
                },
                key=str.casefold,
            )
        self.current_project_id = workspace.project_id
        result = self.scan_current()
        self._save()
        return result

    def list_workspaces(self) -> list[ProjectWorkspace]:
        return list(self.workspaces)

    def current(self) -> ProjectWorkspace | None:
        if self.current_project_id:
            for workspace in self.workspaces:
                if workspace.project_id == self.current_project_id:
                    return workspace
        return self.workspaces[-1] if self.workspaces else None

    def find(self, name_or_alias: str) -> ProjectWorkspace | None:
        """Find a registered project by name, ID, root name, or explicit alias."""

        needle = self._normalize_name(name_or_alias)
        if not needle:
            return None
        for workspace in self.workspaces:
            candidates = [workspace.name, workspace.project_id, Path(workspace.root_path).name, *workspace.aliases]
            if any(self._normalize_name(candidate) == needle for candidate in candidates):
                return workspace
        return None

    def is_available(self, workspace: ProjectWorkspace | None) -> bool:
        if workspace is None:
            return False
        root = canonical_path(workspace.root_path)
        return root is not None and root.exists() and root.is_dir()

    def workspace_for_path(self, path: str | Path) -> ProjectWorkspace | None:
        """Return the user-approved workspace containing a safe path, if any."""

        if self._contains_reparse_point(Path(path)):
            return None
        target = canonical_path(path)
        if target is None:
            return None
        for workspace in self.workspaces:
            root = canonical_path(workspace.root_path)
            if root is None:
                continue
            try:
                target.relative_to(root)
                return workspace
            except ValueError:
                continue
        return None

    def switch(self, name: str) -> ProjectWorkspace | None:
        workspace = self.find(name)
        if workspace is None:
            return None
        self.current_project_id = workspace.project_id
        workspace.last_opened_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self._save()
        return workspace

    def scan_current(self, cancel_check: Callable[[], bool] | None = None) -> ProjectScanResult:
        workspace = self.current()
        if workspace is None:
            return ProjectScanResult(False, message="no project nest.", error="none")
        result = self.scanner.scan(workspace, cancel_check=cancel_check) if cancel_check else self.scanner.scan(workspace)
        if result.ok and result.workspace:
            self.last_scan_files[workspace.project_id] = result.files
            self._save()
        return result

    def files(self, cancel_check: Callable[[], bool] | None = None) -> list[ProjectFileEntry]:
        workspace = self.current()
        if workspace is None:
            return []
        if workspace.project_id not in self.last_scan_files:
            self.scan_current(cancel_check=cancel_check)
        return self.last_scan_files.get(workspace.project_id, [])

    def search(
        self,
        query: str,
        limit: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[ProjectFileEntry]:
        lowered = " ".join((query or "").lower().split())
        if not lowered or len(lowered) > 200:
            return []
        max_results = max(1, int(limit or self.settings.max_search_results))
        return [
            entry
            for entry in self.files(cancel_check=cancel_check)
            if entry.safe_to_read
            and (lowered in entry.relative_path.lower() or lowered in entry.content_preview.lower())
        ][:max_results]

    def read_file(self, relative_path: str) -> FileDropResult:
        workspace = self.current()
        if workspace is None:
            return FileDropResult(False, message="no project nest.", error="none")
        safe_relative = self._normalize_relative_file_path(relative_path)
        if safe_relative is None:
            return FileDropResult(False, message="nope. outside the project.", error="outside project")
        relative_target, normalized_relative_path = safe_relative
        raw_root = Path(workspace.root_path)
        if self._contains_reparse_point(raw_root):
            return FileDropResult(False, message="nope. unsafe project link.", error="unsafe_link_or_reparse_point")
        root = raw_root.resolve()
        candidate = root / relative_target
        if self._contains_reparse_point(candidate):
            return FileDropResult(False, message="nope. unsafe project link.", error="unsafe_link_or_reparse_point")
        target = candidate.resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return FileDropResult(False, message="nope. outside the project.", error="outside project")
        entry = next((item for item in self.files() if item.relative_path == normalized_relative_path), None)
        if entry and not entry.safe_to_read:
            if "secret" in entry.ignored_reason:
                return FileDropResult(False, message="secret crumbs. not chewing those.", error=entry.ignored_reason)
            return FileDropResult(False, message="can't chew that file yet.", error=entry.ignored_reason)
        result = self.file_reader.read_user_file(target, source="manual_file_open")
        if result.ok and result.item:
            result.item.title = f"{workspace.name}/{result.item.title}"
        return result

    @staticmethod
    def _normalize_relative_file_path(value: str) -> tuple[Path, str] | None:
        """Parse an untrusted file path with both Windows and POSIX rules."""

        if not isinstance(value, str) or not value or "\x00" in value:
            return None
        windows_path = PureWindowsPath(value)
        if windows_path.drive or windows_path.root:
            return None
        portable_path = PurePosixPath(value.replace("\\", "/"))
        if portable_path.is_absolute() or not portable_path.parts:
            return None
        if any(part == ".." or ":" in part for part in portable_path.parts):
            return None
        parts = portable_path.parts
        return Path(*parts), "/".join(parts)

    def summary(self) -> ProjectSummary | None:
        workspace = self.current()
        if workspace is None:
            return None
        files = self.files()
        important = [entry.relative_path for entry in files if entry.file_name in {"package.json", "requirements.txt", "pyproject.toml", "README.md", "app.py", "main.py"}][:8]
        folders = sorted({entry.relative_path.split("/", 1)[0] for entry in files if "/" in entry.relative_path})[:8]
        return ProjectSummary(workspace.project_id, workspace.name, workspace.detected_stack, important, folders, workspace.summary)

    def model_context(self) -> str:
        summary = self.summary()
        if summary is None:
            return ""
        return self.sanitizer.sanitize(
            f"Active project summary for user-approved workspace '{summary.name}': "
            f"stack={', '.join(summary.detected_stack)}; "
            f"folders={', '.join(summary.folders)}; "
            f"important_files={', '.join(summary.important_files)}; "
            f"summary={summary.summary}"
        )

    def note(self, text: str) -> bool:
        workspace = self.current()
        clean_text = (text or "").strip()
        if workspace is None or not clean_text or len(clean_text) > 500:
            return False
        if self.sanitizer.sensitivity_hint(clean_text) == "secret_masked":
            return False
        workspace.notes.append(ProjectNote(clean_text, datetime.now().astimezone().isoformat(timespec="seconds")))
        self._save()
        return True

    def recent_notes(self, limit: int = 5) -> list[str]:
        """Return safe, user-created note summaries without touching memory."""

        rows = [
            (note.created_at, workspace.name, note.text)
            for workspace in self.workspaces
            for note in workspace.notes
        ]
        rows.sort(key=lambda row: row[0], reverse=True)
        return [f"{name}: {text.replace(chr(10), ' ')[:180]}" for _, name, text in rows[:max(1, limit)]]

    def forget(self, name: str) -> bool:
        target = self.switch(name)
        if target is None:
            return False
        self.workspaces = [workspace for workspace in self.workspaces if workspace.project_id != target.project_id]
        self.last_scan_files.pop(target.project_id, None)
        self.current_project_id = self.workspaces[-1].project_id if self.workspaces else None
        self._save()
        return True

    def contains_path(self, path: str | Path) -> bool:
        return self.workspace_for_path(path) is not None

    def _find_by_path(self, root: Path) -> ProjectWorkspace | None:
        for workspace in self.workspaces:
            stored = canonical_path(workspace.root_path)
            if stored is not None and stored == root:
                return workspace
        return None

    @staticmethod
    def _contains_reparse_point(path: Path) -> bool:
        return contains_reparse_point(path)

    @staticmethod
    def _normalize_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())

    def _load(self) -> None:
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        self.current_project_id = raw.get("current_project_id") if isinstance(raw, dict) else None
        self.workspaces = []
        for item in raw.get("workspaces", []) if isinstance(raw, dict) else []:
            notes = [ProjectNote(**note) for note in item.get("notes", []) if isinstance(note, dict)]
            clean = {**item, "notes": notes}
            try:
                self.workspaces.append(ProjectWorkspace(**clean))
            except TypeError:
                continue

    def _save(self) -> None:
        payload = {
            "current_project_id": self.current_project_id,
            "workspaces": [asdict(workspace) for workspace in self.workspaces],
        }
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
