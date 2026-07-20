"""Local app index for safe known-app launching."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import AppIndexEntry, AppSearchResult
from fibi.paths import data_path

APP_INDEX_PATH = data_path("app_index.json")


def normalize_app_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class AppIndexEngine:
    """Build and search a local allowlist of apps Fibi may open."""

    def __init__(self, index_path: Path = APP_INDEX_PATH) -> None:
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
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
            return target if target.exists() else path
        except Exception:
            return path

    @staticmethod
    def _subsequence_score(needle: str, haystack: str) -> int:
        index = 0
        for char in haystack:
            if index < len(needle) and needle[index] == char:
                index += 1
        return 40 if index == len(needle) and len(needle) >= 3 else 0
