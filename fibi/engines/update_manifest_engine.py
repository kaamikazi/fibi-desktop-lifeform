"""Local-only update manifest parser for future update support."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fibi.build_info import APP_VERSION
from fibi.runtime_paths import app_root
from fibi.engines.version_compare import VersionComparison, compare_versions


@dataclass(slots=True)
class UpdateManifest:
    latest_version: str = ""
    channel: str = ""
    release_date: str = ""
    release_notes: str = ""
    download_url: str = ""
    sha256: str = ""
    required: bool = False
    min_supported_version: str = ""


class UpdateManifestEngine:
    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = Path(manifest_path) if manifest_path is not None else app_root() / "updates" / "update_manifest.json"
        self.last_manifest: UpdateManifest | None = None
        self.last_comparison: VersionComparison | None = None

    def load_local(self) -> UpdateManifest | None:
        if not self.manifest_path.exists():
            return None
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        manifest = UpdateManifest(**{key: raw.get(key, getattr(UpdateManifest(), key)) for key in UpdateManifest.__dataclass_fields__})
        self.last_manifest = manifest
        self.last_comparison = compare_versions(APP_VERSION, manifest.latest_version)
        return manifest

    def status_line(self) -> str:
        manifest = self.load_local()
        if manifest is None:
            return "updates local only. no manifest crumb."
        relation = self.last_comparison.relation if self.last_comparison else "unknown"
        return f"local update manifest: {manifest.latest_version} ({relation}). no download paws."

    def notes_line(self) -> str:
        manifest = self.last_manifest or self.load_local()
        if manifest is None:
            return "no local update notes."
        return manifest.release_notes[:500] or "local manifest has no notes."

    @staticmethod
    def safety_line() -> str:
        return "update safety: no network, no auto-download, no auto-install. local manifest only."

