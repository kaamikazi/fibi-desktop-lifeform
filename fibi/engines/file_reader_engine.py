"""Safe reader for explicitly provided text/code files."""

from __future__ import annotations

from pathlib import Path

from fibi.engines.context_engine import ContextEngine
from fibi.engines.types import FileDropResult

SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".csv",
    ".html",
    ".css",
    ".log",
    ".yaml",
    ".yml",
}

STUB_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


class FileReaderEngine:
    """Read only files the user explicitly hands to Fibi."""

    def __init__(self, context: ContextEngine, max_bytes: int = 1_000_000) -> None:
        self.context = context
        self.max_bytes = max_bytes

    def read_user_file(self, path: str | Path, source: str = "dropped_file") -> FileDropResult:
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            return FileDropResult(False, message="couldn't find that file crumb.", error="missing")
        suffix = file_path.suffix.lower()
        if suffix in STUB_EXTENSIONS:
            return FileDropResult(False, message="can't chew that file yet.", error="unsupported")
        if suffix not in SUPPORTED_TEXT_EXTENSIONS:
            return FileDropResult(False, message="can't chew that file yet.", error="unsupported")
        try:
            size = file_path.stat().st_size
        except OSError:
            return FileDropResult(False, message="file crumb resisted.", error="stat failed")
        if size > self.max_bytes:
            return FileDropResult(False, message="file crumb too big.", error="too large")
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                return FileDropResult(False, message="can't chew that encoding yet.", error="decode failed")
        except OSError:
            return FileDropResult(False, message="file crumb resisted.", error="read failed")
        item = self.context.add_text(
            content,
            source=source,
            title=file_path.name,
            mime_type=self._mime_type(suffix),
            file_path=str(file_path),
            user_initiated=True,
            can_remember=True,
        )
        return FileDropResult(True, item, "tiny file acquired.", None)

    @staticmethod
    def _mime_type(suffix: str) -> str:
        if suffix == ".md":
            return "text/markdown"
        if suffix == ".json":
            return "application/json"
        if suffix == ".csv":
            return "text/csv"
        if suffix in {".html", ".css"}:
            return "text/html" if suffix == ".html" else "text/css"
        return "text/plain"
