"""Registered project workspace support for Fibi v0.15."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.context_engine import ContextEngine
from fibi.engines.file_reader_engine import FileReaderEngine
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
        self.scanner = scanner or ProjectScannerEngine(self.sanitizer, self.settings.readable_file_limit_bytes)
        self.file_reader = FileReaderEngine(self.context, self.settings.readable_file_limit_bytes)
        self.workspaces: list[ProjectWorkspace] = []
        self.current_project_id: str | None = None
        self.last_scan_files: dict[str, list[ProjectFileEntry]] = {}
        self._load()

    def add_workspace(self, path: str | Path) -> ProjectScanResult:
        root = Path(path).expanduser().resolve()
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

    def switch(self, name: str) -> ProjectWorkspace | None:
        lowered = name.lower().strip()
        for workspace in self.workspaces:
            if workspace.name.lower() == lowered or workspace.project_id == name:
                self.current_project_id = workspace.project_id
                workspace.last_opened_at = datetime.now().astimezone().isoformat(timespec="seconds")
                self._save()
                return workspace
        return None

    def scan_current(self) -> ProjectScanResult:
        workspace = self.current()
        if workspace is None:
            return ProjectScanResult(False, message="no project nest.", error="none")
        result = self.scanner.scan(workspace)
        if result.ok and result.workspace:
            self.last_scan_files[workspace.project_id] = result.files
            self._save()
        return result

    def files(self) -> list[ProjectFileEntry]:
        workspace = self.current()
        if workspace is None:
            return []
        if workspace.project_id not in self.last_scan_files:
            self.scan_current()
        return self.last_scan_files.get(workspace.project_id, [])

    def search(self, query: str) -> list[ProjectFileEntry]:
        lowered = query.lower()
        return [entry for entry in self.files() if lowered in entry.relative_path.lower() or lowered in entry.content_preview.lower()][:12]

    def read_file(self, relative_path: str) -> FileDropResult:
        workspace = self.current()
        if workspace is None:
            return FileDropResult(False, message="no project nest.", error="none")
        root = Path(workspace.root_path).resolve()
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return FileDropResult(False, message="nope. outside the project.", error="outside project")
        entry = next((item for item in self.files() if item.relative_path == relative_path.replace("\\", "/")), None)
        if entry and not entry.safe_to_read:
            if "secret" in entry.ignored_reason:
                return FileDropResult(False, message="secret crumbs. not chewing those.", error=entry.ignored_reason)
            return FileDropResult(False, message="can't chew that file yet.", error=entry.ignored_reason)
        result = self.file_reader.read_user_file(target, source="manual_file_open")
        if result.ok and result.item:
            result.item.title = f"{workspace.name}/{result.item.title}"
        return result

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
        if workspace is None:
            return False
        workspace.notes.append(ProjectNote(text[:500], datetime.now().astimezone().isoformat(timespec="seconds")))
        self._save()
        return True

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
        target = Path(path).resolve()
        for workspace in self.workspaces:
            try:
                target.relative_to(Path(workspace.root_path).resolve())
                return True
            except ValueError:
                continue
        return False

    def _find_by_path(self, root: Path) -> ProjectWorkspace | None:
        for workspace in self.workspaces:
            if Path(workspace.root_path).resolve() == root:
                return workspace
        return None

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
