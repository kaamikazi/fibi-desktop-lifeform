"""Safe subprocess runner for confirmed project checks."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.check_output_summarizer import CheckOutputSummarizer
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import ProjectCheckRequest, ProjectCheckResult
from fibi.paths import data_path

LOGGER = logging.getLogger(__name__)


class ProjectCheckRunner:
    """Run a whitelisted check with shell=False and bounded output."""

    def __init__(
        self,
        output_root: Path | None = None,
        sanitizer: SecretSanitizer | None = None,
        summarizer: CheckOutputSummarizer | None = None,
        max_preview_chars: int = 12_000,
    ) -> None:
        self.output_root = Path(output_root) if output_root is not None else data_path("project_checks")
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.sanitizer = sanitizer or SecretSanitizer()
        self.summarizer = summarizer or CheckOutputSummarizer()
        self.max_preview_chars = max_preview_chars

    def run(self, request: ProjectCheckRequest) -> ProjectCheckResult:
        LOGGER.info("project_check_started", extra={"check_id": request.check_id, "command_key": request.command_key})
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        start = time.perf_counter()
        output_dir = self.output_root / request.check_id
        output_dir.mkdir(parents=True, exist_ok=True)
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        error = ""
        timed_out = False
        try:
            completed = subprocess.run(
                request.command_args,
                cwd=request.cwd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=max(1, request.timeout_seconds),
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            exit_code = int(completed.returncode)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            exit_code = None
            error = "timeout"
        except OSError as exc:
            exit_code = None
            error = str(exc)
            stderr = str(exc)
        clean_stdout = self.sanitizer.sanitize(stdout)
        clean_stderr = self.sanitizer.sanitize(stderr)
        (output_dir / "stdout.txt").write_text(clean_stdout, encoding="utf-8")
        (output_dir / "stderr.txt").write_text(clean_stderr, encoding="utf-8")
        summary = self.summarizer.summarize(clean_stdout, clean_stderr, exit_code, timed_out)
        ended_at = datetime.now().astimezone().isoformat(timespec="seconds")
        result = ProjectCheckResult(
            request.check_id,
            request.project_id,
            request.command_key,
            request.command_args,
            request.cwd,
            request.timeout_seconds,
            started_at,
            ended_at,
            exit_code,
            clean_stdout[: self.max_preview_chars],
            clean_stderr[: self.max_preview_chars],
            str(output_dir),
            summary.summary,
            error,
            request.risk_level,
            timed_out,
        )
        (output_dir / "metadata.json").write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        LOGGER.info(
            "project_check_completed",
            extra={"check_id": request.check_id, "exit_code": exit_code if exit_code is not None else -999, "duration_ms": round((time.perf_counter() - start) * 1000, 1)},
        )
        return result
