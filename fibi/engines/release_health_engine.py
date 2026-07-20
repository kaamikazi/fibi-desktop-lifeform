"""Local release health summary for beta builds."""

from __future__ import annotations

from pathlib import Path

from fibi.build_info import APP_VERSION
from fibi.paths import data_path
from fibi.runtime_paths import reports_dir, runtime_info
from fibi.engines.issue_tracker_engine import IssueTrackerEngine
from fibi.engines.update_manifest_engine import UpdateManifestEngine


class ReleaseHealthEngine:
    def __init__(
        self,
        issues: IssueTrackerEngine,
        updates: UpdateManifestEngine,
    ) -> None:
        self.issues = issues
        self.updates = updates
        self.last_self_test_result = ""

    def summary_line(self) -> str:
        info = runtime_info()
        counts = self.issues.summary()
        support = _latest(reports_dir(), "fibi_error_report_*.zip")
        startup = data_path("startup_diagnostics.json")
        crash = data_path("shutdown_marker.json")
        update_status = self.updates.status_line()
        parts = [
            f"release health v{APP_VERSION}.",
            "packaged." if info.packaged else "dev mode.",
            f"issues {counts['total']}, open {counts['open']}, critical {counts['critical']}.",
            f"last crash marker: {'yes' if crash.exists() else 'none'}.",
            f"last support: {support.name if support else 'none'}.",
            f"startup diag: {'yes' if startup.exists() else 'none'}.",
            f"self test: {self.last_self_test_result or 'not run here'}.",
            update_status,
        ]
        return " ".join(parts)


def _latest(folder: Path, pattern: str) -> Path | None:
    matches = sorted(folder.glob(pattern), key=lambda path: path.stat().st_mtime if path.exists() else 0)
    return matches[-1] if matches else None

