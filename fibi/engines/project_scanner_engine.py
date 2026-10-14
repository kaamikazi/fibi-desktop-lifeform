"""Safe metadata scanner for registered project folders."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from fibi.engines.file_reader_engine import SUPPORTED_TEXT_EXTENSIONS
from fibi.engines.path_safety import contains_reparse_point, is_reparse_point
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import ProjectFileEntry, ProjectScanResult, ProjectWorkspace

IGNORED_DIRS = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "out",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "coverage",
    ".cache",
    "cache",
}

SECRET_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}

SECRET_PREFIXES = ("secrets.", "secret.", "credentials.", "credential.")
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".mov",
    ".zip",
    ".exe",
    ".dll",
    ".pdf",
    ".docx",
}


class ProjectScannerEngine:
    """Scan project metadata without reading private or generated content."""

    def __init__(
        self,
        sanitizer: SecretSanitizer | None = None,
        readable_limit_bytes: int = 1_000_000,
        max_depth: int = 12,
        max_files: int = 10_000,
        max_seconds: float = 5.0,
    ) -> None:
        self.sanitizer = sanitizer or SecretSanitizer()
        self.readable_limit_bytes = readable_limit_bytes
        self.max_depth = max(0, int(max_depth))
        self.max_files = max(1, int(max_files))
        self.max_seconds = max(0.0, float(max_seconds))

    def scan(
        self,
        workspace: ProjectWorkspace,
        cancel_check: Callable[[], bool] | None = None,
    ) -> ProjectScanResult:
        candidate_root = Path(workspace.root_path)
        if contains_reparse_point(candidate_root):
            return ProjectScanResult(False, workspace, message="project path is not safe.", error="unsafe_link_or_reparse_point")
        root = candidate_root.resolve()
        if not root.exists() or not root.is_dir():
            return ProjectScanResult(False, workspace, message="project nest missing.", error="missing")
        files: list[ProjectFileEntry] = []
        ignored_count = 0
        cancelled = False
        bounded = False
        timed_out = False
        deadline = time.monotonic() + self.max_seconds
        for current, dirs, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            try:
                depth = len(current_path.relative_to(root).parts)
            except ValueError:
                continue
            if time.monotonic() >= deadline:
                timed_out = True
                break
            if cancel_check and cancel_check():
                cancelled = True
                break
            dirs[:] = [
                name
                for name in dirs
                if depth < self.max_depth
                and not self._ignore_dir(name)
                and not is_reparse_point(current_path / name)
            ]
            for filename in filenames:
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                if cancel_check and cancel_check():
                    cancelled = True
                    break
                if len(files) >= self.max_files:
                    bounded = True
                    break
                path = current_path / filename
                if is_reparse_point(path):
                    ignored_count += 1
                    continue
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    ignored_count += 1
                    continue
                entry = self._entry(path, relative)
                if not entry.safe_to_read:
                    ignored_count += 1
                files.append(entry)
            if cancelled or bounded or timed_out:
                break
        stack = self.detect_stack(root, files)
        workspace.file_count = len([entry for entry in files if entry.safe_to_read])
        workspace.detected_stack = stack
        workspace.last_scanned_at = datetime.now().astimezone().isoformat(timespec="seconds")
        workspace.summary = self.summary_text(workspace, files)
        if cancelled:
            return ProjectScanResult(False, workspace, files, ignored_count, "file scan canceled.", "cancelled")
        if timed_out:
            return ProjectScanResult(False, workspace, files, ignored_count, "file scan timed out.", "timeout")
        message = "found code crumbs."
        if bounded:
            message = f"found code crumbs. scan bounded at {self.max_files} files."
        return ProjectScanResult(True, workspace, files, ignored_count, message, None)

    def _entry(self, path: Path, relative: str) -> ProjectFileEntry:
        suffix = path.suffix.lower()
        reason = ""
        safe = True
        if self._secret_file(path.name):
            safe = False
            reason = "secret file"
        elif suffix in BINARY_EXTENSIONS:
            safe = False
            reason = "binary metadata only"
        elif suffix not in SUPPORTED_TEXT_EXTENSIONS and path.name not in {"package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod"}:
            safe = False
            reason = "unsupported type"
        try:
            stat = path.stat()
            size = int(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
        except OSError:
            size = 0
            modified = ""
            safe = False
            reason = "stat failed"
        if size > self.readable_limit_bytes:
            safe = False
            reason = "too large"
        preview = ""
        if safe and size <= 12_000:
            try:
                preview = self.sanitizer.sanitize(path.read_text(encoding="utf-8", errors="replace")[:700])
            except OSError:
                preview = ""
        return ProjectFileEntry(
            relative,
            path.name,
            suffix,
            size,
            modified,
            safe,
            reason,
            preview,
            max(1, size // 4) if safe else 0,
        )

    def detect_stack(self, root: Path, files: list[ProjectFileEntry]) -> list[str]:
        names = {entry.relative_path.replace("\\", "/") for entry in files}
        stack: list[str] = []
        if "package.json" in names:
            stack.append("Node")
            package = root / "package.json"
            try:
                raw = json.loads(package.read_text(encoding="utf-8"))
                deps = {**raw.get("dependencies", {}), **raw.get("devDependencies", {})}
                if "react" in deps:
                    stack.append("React")
                if "next" in deps:
                    stack.append("Next.js")
                if "vite" in deps:
                    stack.append("Vite")
                if "tailwindcss" in deps:
                    stack.append("Tailwind")
            except (OSError, json.JSONDecodeError):
                pass
        if "requirements.txt" in names or "pyproject.toml" in names:
            stack.append("Python")
        if "tsconfig.json" in names:
            stack.append("TypeScript")
        if any(name.startswith("vite.config.") for name in names):
            stack.append("Vite")
        if any(name.startswith("next.config.") for name in names):
            stack.append("Next.js")
        if any(name.startswith("tailwind.config.") for name in names):
            stack.append("Tailwind")
        if any(name.startswith("supabase/") for name in names):
            stack.append("Supabase")
        if any(name.startswith("prisma/") for name in names):
            stack.append("Prisma")
        if "Cargo.toml" in names:
            stack.append("Rust")
        if "go.mod" in names:
            stack.append("Go")
        ordered = []
        for item in stack:
            if item not in ordered:
                ordered.append(item)
        return ordered or ["unknown"]

    @staticmethod
    def summary_text(workspace: ProjectWorkspace, files: list[ProjectFileEntry]) -> str:
        important = [entry.relative_path for entry in files if entry.file_name in {"package.json", "requirements.txt", "pyproject.toml", "README.md", "app.py", "main.py"}]
        folders = sorted({entry.relative_path.split("/", 1)[0] for entry in files if "/" in entry.relative_path})[:8]
        stack = " + ".join(workspace.detected_stack) if workspace.detected_stack else "unknown"
        bits = [f"This looks like a {stack} project."]
        if folders:
            bits.append("Folders: " + ", ".join(folders) + ".")
        if important:
            bits.append("Important crumbs: " + ", ".join(important[:8]) + ".")
        return " ".join(bits)

    @staticmethod
    def _ignore_dir(name: str) -> bool:
        return name in IGNORED_DIRS or name.startswith(".") and name not in {".github"}

    @staticmethod
    def _secret_file(name: str) -> bool:
        lowered = name.lower()
        return lowered in SECRET_FILENAMES or lowered.endswith(".pem") or lowered.endswith(".key") or lowered.startswith(SECRET_PREFIXES)

    @staticmethod
    def _is_reparse_point(path: Path) -> bool:
        return is_reparse_point(path)
