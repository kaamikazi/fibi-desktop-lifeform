"""Local beta issue tracker for Fibi.

Issues stay on disk. Nothing is uploaded or sent automatically.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from fibi.build_info import APP_VERSION, BUILD_MODE
from fibi.paths import data_path
from fibi.runtime_paths import is_packaged, reports_dir

CATEGORIES = {"crash", "gui", "voice", "rvc", "memory", "project", "patch", "check", "session", "packaging", "performance", "other"}
SEVERITIES = {"low", "medium", "high", "critical"}
STATUSES = {"open", "investigating", "fixed", "wontfix", "closed"}


@dataclass(slots=True)
class IssueRecord:
    issue_id: str
    created_at: str
    updated_at: str
    app_version: str
    build_mode: str
    packaged: bool
    category: str = "other"
    severity: str = "medium"
    title: str = ""
    description: str = ""
    reproduction_steps: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    status: str = "open"
    tags: list[str] = field(default_factory=list)
    linked_support_bundle: str = ""
    linked_error_report: str = ""
    last_route_decision_summary: str = ""
    health_snapshot_summary: str = ""


class IssueTrackerEngine:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else data_path("issues/issues.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        title: str,
        description: str = "",
        *,
        category: str = "other",
        severity: str = "medium",
        tags: list[str] | None = None,
        last_route_decision_summary: str = "",
        health_snapshot_summary: str = "",
    ) -> IssueRecord:
        now = _now()
        issue = IssueRecord(
            issue_id="ISS-" + uuid.uuid4().hex[:8],
            created_at=now,
            updated_at=now,
            app_version=APP_VERSION,
            build_mode=BUILD_MODE,
            packaged=is_packaged(),
            category=category if category in CATEGORIES else "other",
            severity=severity if severity in SEVERITIES else "medium",
            title=title.strip()[:160] or "beta issue",
            description=description.strip()[:4000],
            tags=tags or [],
            last_route_decision_summary=last_route_decision_summary[:500],
            health_snapshot_summary=health_snapshot_summary[:1500],
        )
        self._append(issue)
        return issue

    def list(self, limit: int = 20) -> list[IssueRecord]:
        return self._read()[-limit:]

    def last(self) -> IssueRecord | None:
        issues = self._read()
        return issues[-1] if issues else None

    def get(self, issue_id: str) -> IssueRecord | None:
        normalized = issue_id.strip().upper()
        for issue in self._read():
            if issue.issue_id.upper() == normalized:
                return issue
        return None

    def update_status(self, issue_id: str, status: str) -> IssueRecord | None:
        if status not in STATUSES:
            return None
        issues = self._read()
        found: IssueRecord | None = None
        for issue in issues:
            if issue.issue_id.upper() == issue_id.strip().upper():
                issue.status = status
                issue.updated_at = _now()
                found = issue
                break
        if found is not None:
            self._write_all(issues)
        return found

    def link_support_bundle(self, issue_id: str, bundle_path: Path) -> IssueRecord | None:
        issues = self._read()
        found: IssueRecord | None = None
        for issue in issues:
            if issue.issue_id.upper() == issue_id.strip().upper():
                issue.linked_support_bundle = str(bundle_path)
                issue.linked_error_report = str(bundle_path)
                issue.updated_at = _now()
                found = issue
                break
        if found is not None:
            self._write_all(issues)
        return found

    def export(self, issue_id: str) -> Path | None:
        issue = self.get(issue_id)
        if issue is None:
            return None
        target = reports_dir() / f"{issue.issue_id}_issue_export.md"
        target.write_text(self._markdown(issue), encoding="utf-8")
        return target

    def export_all(self) -> Path:
        target = reports_dir() / "fibi_issues_export.json"
        target.write_text(json.dumps([asdict(issue) for issue in self._read()], indent=2), encoding="utf-8")
        return target

    def summary(self) -> dict[str, int]:
        issues = self._read()
        return {
            "total": len(issues),
            "open": sum(1 for issue in issues if issue.status == "open"),
            "critical": sum(1 for issue in issues if issue.severity == "critical" and issue.status != "closed"),
        }

    def _append(self, issue: IssueRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(issue), ensure_ascii=False) + "\n")

    def _read(self) -> list[IssueRecord]:
        if not self.path.exists():
            return []
        records: list[IssueRecord] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                records.append(IssueRecord(**json.loads(line)))
            except (TypeError, json.JSONDecodeError):
                continue
        return records

    def _write_all(self, issues: list[IssueRecord]) -> None:
        self.path.write_text("\n".join(json.dumps(asdict(issue), ensure_ascii=False) for issue in issues) + ("\n" if issues else ""), encoding="utf-8")

    @staticmethod
    def _markdown(issue: IssueRecord) -> str:
        return (
            f"# {issue.issue_id}: {issue.title}\n\n"
            f"- status: {issue.status}\n"
            f"- severity: {issue.severity}\n"
            f"- category: {issue.category}\n"
            f"- created: {issue.created_at}\n"
            f"- version: {issue.app_version} {issue.build_mode}\n\n"
            f"## Description\n\n{issue.description or 'not provided'}\n\n"
            f"## Reproduction\n\n{issue.reproduction_steps or 'not provided'}\n\n"
            f"## Expected\n\n{issue.expected_behavior or 'not provided'}\n\n"
            f"## Actual\n\n{issue.actual_behavior or 'not provided'}\n\n"
            f"## Support Bundle\n\n{issue.linked_support_bundle or 'none'}\n"
        )


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

