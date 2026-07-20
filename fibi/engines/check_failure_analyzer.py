"""Analyze failed project check output without calling a model."""

from __future__ import annotations

import logging
import re

from fibi.engines.types import CheckFailureAnalysis, ErrorLocation, ProjectCheckResult

LOGGER = logging.getLogger(__name__)


class CheckFailureAnalyzer:
    """Extract likely failure type, file path, line number, and message."""

    _TS_PATTERN = re.compile(r"(?P<file>[\w./\\-]+\.(?:ts|tsx|js|jsx))\((?P<line>\d+),(?P<col>\d+)\):\s*error\s*(?P<code>TS\d+):\s*(?P<msg>.+)")
    _COLON_PATTERN = re.compile(r"(?P<file>[\w./\\-]+\.[A-Za-z0-9]+):(?P<line>\d+):(?P<col>\d+)?")
    _PY_FILE_PATTERN = re.compile(r'File "?(?P<file>[^"\n]+\.py)"?, line (?P<line>\d+)')
    _ESLINT_PATTERN = re.compile(r"(?P<file>[\w./\\-]+\.(?:ts|tsx|js|jsx))\n\s*(?P<line>\d+):(?P<col>\d+)\s+error\s+(?P<msg>.+)")

    def analyze(self, result: ProjectCheckResult) -> CheckFailureAnalysis:
        output = f"{result.stdout_preview}\n{result.stderr_preview}".strip()
        error_type = self._detect_error_type(result, output)
        locations = self._extract_locations(output)
        error_message = self._extract_error_message(output, error_type, result)
        suspected = locations[0] if locations else ErrorLocation("", None, None)
        confidence = self._confidence(error_type, locations, output)
        analysis = CheckFailureAnalysis(
            check_id=result.check_id,
            project_id=result.project_id,
            error_type=error_type,
            error_message=error_message[:500],
            related_files=locations,
            suspected_file=suspected.file_path,
            suspected_line=suspected.line,
            confidence=confidence,
            refused_reason="" if output else "no output to analyze",
        )
        LOGGER.info(
            "check_failure_analyzed",
            extra={
                "check_id": result.check_id,
                "error_type": error_type,
                "location_count": len(locations),
                "confidence": confidence,
            },
        )
        return analysis

    def _detect_error_type(self, result: ProjectCheckResult, output: str) -> str:
        lowered = output.lower()
        if result.timed_out or "timed out" in lowered:
            return "timeout"
        if "syntaxerror" in lowered:
            return "python_syntax_error"
        if "modulenotfounderror" in lowered:
            return "python_module_not_found"
        if "importerror" in lowered:
            return "python_import_error"
        if "pytest" in lowered or "assertionerror" in lowered or "failed" in lowered and ".py" in lowered:
            return "pytest_failure"
        if re.search(r"\bts\d{4}\b", output, re.IGNORECASE):
            return "typescript_error"
        if "eslint" in lowered or re.search(r"\n\s*\d+:\d+\s+error\s+", output):
            return "eslint_error"
        if "next.js" in lowered or "next build" in lowered:
            return "nextjs_build_error"
        if "no module named" in lowered or "cannot find module" in lowered:
            return "missing_dependency"
        if "not recognized" in lowered or "command not found" in lowered or "no such file or directory" in lowered:
            return "command_not_found"
        if result.exit_code not in {0, None}:
            return "unknown_failure"
        return "unknown_failure"

    def _extract_locations(self, output: str) -> list[ErrorLocation]:
        locations: list[ErrorLocation] = []
        seen: set[tuple[str, int | None, int | None]] = set()
        for pattern in (self._TS_PATTERN, self._ESLINT_PATTERN, self._PY_FILE_PATTERN, self._COLON_PATTERN):
            for match in pattern.finditer(output):
                raw_file = match.group("file").replace("\\", "/").strip()
                line = self._to_int(match.groupdict().get("line"))
                column = self._to_int(match.groupdict().get("col"))
                key = (raw_file, line, column)
                if key in seen:
                    continue
                seen.add(key)
                locations.append(ErrorLocation(raw_file, line, column, match.group(0)[:300]))
        return locations[:8]

    @staticmethod
    def _extract_error_message(output: str, error_type: str, result: ProjectCheckResult) -> str:
        if not output:
            return result.summary or "check failed with no output"
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        priority_terms = {
            "python_syntax_error": ("SyntaxError",),
            "python_module_not_found": ("ModuleNotFoundError", "No module named"),
            "python_import_error": ("ImportError",),
            "typescript_error": ("error TS",),
            "eslint_error": ("error",),
            "pytest_failure": ("AssertionError", "FAILED", "failed"),
        }.get(error_type, ("error", "failed", "Traceback"))
        for line in lines:
            if any(term.lower() in line.lower() for term in priority_terms):
                return line
        return lines[-1][:500] if lines else result.summary

    @staticmethod
    def _confidence(error_type: str, locations: list[ErrorLocation], output: str) -> float:
        if error_type in {"timeout", "command_not_found", "unknown_failure"}:
            return 0.35 if output else 0.15
        if locations:
            return 0.82 if error_type in {"python_syntax_error", "typescript_error", "eslint_error"} else 0.7
        return 0.45

    @staticmethod
    def _to_int(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
