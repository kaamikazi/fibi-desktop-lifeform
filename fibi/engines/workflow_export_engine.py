"""Safe local exports for workflow runs."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import WorkflowExport, WorkflowRun, WorkflowRunSummary
from fibi.runtime_paths import reports_dir


SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
)


class WorkflowExportEngine:
    """Write concise workflow summaries without raw logs or source dumps."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = Path(output_dir) if output_dir is not None else reports_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, run: WorkflowRun) -> WorkflowExport:
        now = _now()
        summary = self.summarize(run, completed_at=now if run.status == "completed" else "")
        base = self.output_dir / f"workflow_run_{run.run_id}"
        markdown_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        payload = asdict(summary)
        payload["excluded"] = [
            "secrets",
            "raw logs",
            "full project source",
            "memory database",
            "raw browser page text",
        ]
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        markdown_path.write_text(self._markdown(summary), encoding="utf-8")
        return WorkflowExport(
            run_id=run.run_id,
            markdown_path=str(markdown_path),
            json_path=str(json_path),
            created_at=now,
            excluded=payload["excluded"],
        )

    def summarize(self, run: WorkflowRun, completed_at: str = "") -> WorkflowRunSummary:
        return WorkflowRunSummary(
            run_id=run.run_id,
            recipe_name=run.recipe_name,
            status=run.status,
            started_at=run.created_at,
            completed_at=completed_at,
            steps_completed=len(run.completed_steps),
            total_steps=len(run.steps),
            skipped_steps=list(run.skipped_steps),
            linked_issues=[self._sanitize(item) for item in run.linked_issue_ids],
            linked_support_bundles=[self._sanitize(item) for item in run.linked_support_bundles],
            linked_release_artifacts=[self._sanitize(item) for item in run.linked_release_artifacts],
            safe_summaries=[self._sanitize(item) for item in run.safe_summaries[-8:]],
        )

    def _markdown(self, summary: WorkflowRunSummary) -> str:
        lines = [
            f"# Workflow Run {summary.run_id}",
            "",
            f"- recipe: {summary.recipe_name}",
            f"- status: {summary.status}",
            f"- started: {summary.started_at}",
            f"- completed: {summary.completed_at or 'not completed'}",
            f"- steps: {summary.steps_completed}/{summary.total_steps}",
            "",
            "## Safe Summaries",
            "",
        ]
        lines.extend(f"- {item}" for item in summary.safe_summaries[:8])
        if not summary.safe_summaries:
            lines.append("- none")
        lines.extend(
            [
                "",
                "## Links",
                "",
                f"- issues: {', '.join(summary.linked_issues) if summary.linked_issues else 'none'}",
                f"- support bundles: {', '.join(summary.linked_support_bundles) if summary.linked_support_bundles else 'none'}",
                f"- release artifacts: {', '.join(summary.linked_release_artifacts) if summary.linked_release_artifacts else 'none'}",
                "",
                "## Excluded",
                "",
                "- secrets",
                "- raw logs",
                "- full project source",
                "- memory database",
                "- raw browser page text",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _sanitize(text: str) -> str:
        cleaned = str(text)[:1000]
        for pattern in SECRET_PATTERNS:
            cleaned = pattern.sub("[redacted]", cleaned)
        return cleaned


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
