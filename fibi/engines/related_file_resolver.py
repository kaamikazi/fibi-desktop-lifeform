"""Resolve check failure paths to safe registered project files."""

from __future__ import annotations

import logging
from pathlib import Path

from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import CheckFailureAnalysis, ErrorLocation, RelatedFileCandidate

LOGGER = logging.getLogger(__name__)


class RelatedFileResolver:
    """Map analyzer paths to project files and read small safe snippets."""

    def __init__(self, workspace: ProjectWorkspaceEngine, snippet_radius: int = 4) -> None:
        self.workspace = workspace
        self.snippet_radius = snippet_radius

    def resolve(self, analysis: CheckFailureAnalysis) -> list[RelatedFileCandidate]:
        project = self.workspace.current()
        if project is None:
            return []
        root = Path(project.root_path).resolve()
        candidates: list[RelatedFileCandidate] = []
        for location in analysis.related_files or [ErrorLocation(analysis.suspected_file, analysis.suspected_line)]:
            if not location.file_path:
                continue
            candidate = self._resolve_one(root, location)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: item.score, reverse=True)
        LOGGER.info(
            "related_file_resolved",
            extra={
                "check_id": analysis.check_id,
                "candidate_count": len(candidates),
                "safe_count": sum(1 for item in candidates if item.safe_to_read),
            },
        )
        return candidates[:5]

    def _resolve_one(self, root: Path, location: ErrorLocation) -> RelatedFileCandidate | None:
        raw = location.file_path.replace("\\", "/").strip().strip('"')
        relative = self._normalize_relative_path(root, raw)
        if not relative:
            return RelatedFileCandidate(raw, "", False, 0.0, "outside project", suspected_line=location.line, refused_reason="outside project")
        entry = next((item for item in self.workspace.files() if item.relative_path == relative), None)
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return RelatedFileCandidate(relative, str(target), False, 0.0, "outside project", suspected_line=location.line, refused_reason="outside project")
        if entry is None:
            return RelatedFileCandidate(relative, str(target), False, 0.2, "not in project scan", suspected_line=location.line, refused_reason="not scanned")
        if not entry.safe_to_read:
            return RelatedFileCandidate(relative, str(target), False, 0.1, "unsafe file", suspected_line=location.line, refused_reason=entry.ignored_reason or "unsafe file")
        snippet = self._snippet(target, location.line)
        return RelatedFileCandidate(relative, str(target), True, 0.95 if location.line else 0.75, "matched error path", snippet, location.line)

    @staticmethod
    def _normalize_relative_path(root: Path, raw: str) -> str:
        if not raw or ".." in Path(raw).parts:
            return ""
        path = Path(raw)
        if path.is_absolute():
            try:
                return path.resolve().relative_to(root).as_posix()
            except ValueError:
                return ""
        clean = raw.replace("\\", "/")
        if clean.startswith("./"):
            clean = clean[2:]
        elif clean.startswith("/"):
            clean = clean.lstrip("/")
        target = (root / clean).resolve()
        try:
            return target.relative_to(root).as_posix()
        except ValueError:
            return ""

    def _snippet(self, target: Path, line: int | None) -> str:
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""
        lines = text.splitlines()
        if not lines:
            return ""
        if line is None or line < 1:
            start, end = 0, min(len(lines), self.snippet_radius * 2 + 1)
        else:
            start = max(0, line - self.snippet_radius - 1)
            end = min(len(lines), line + self.snippet_radius)
        numbered = [f"{idx + 1}: {lines[idx]}" for idx in range(start, end)]
        return "\n".join(numbered)
