"""Create safe fix suggestions from failed check analysis."""

from __future__ import annotations

import logging
from pathlib import Path

from fibi.engines.diff_generator import DiffGenerator
from fibi.engines.types import (
    CheckFailureAnalysis,
    CheckFixPlan,
    EditSuggestionResult,
    RelatedFileCandidate,
    UnifiedDiffSuggestion,
)

LOGGER = logging.getLogger(__name__)

HIGH_RISK_HINTS = ("auth", "login", "token", "secret", "password", "permission", "payment", "security")


class CheckFixPlanner:
    """Plan local safe fixes and refuse risky/ambiguous fixes."""

    def __init__(self, diff: DiffGenerator | None = None) -> None:
        self.diff = diff or DiffGenerator()

    def plan(
        self,
        analysis: CheckFailureAnalysis,
        candidates: list[RelatedFileCandidate],
        user_request: str = "",
    ) -> CheckFixPlan:
        safe_candidates = [candidate for candidate in candidates if candidate.safe_to_read and candidate.snippet]
        if not safe_candidates:
            return self._refused(analysis, "i see the scream, not the source.", "blocked")
        candidate = safe_candidates[0]
        if self._high_risk(candidate.relative_path, analysis.error_message, user_request):
            return self._refused(analysis, "too sharp. manual review.", "high", candidate.relative_path)
        if analysis.error_type == "python_syntax_error":
            plan = self._python_syntax_plan(analysis, candidate)
            if plan is not None:
                LOGGER.info("fix_plan_created", extra={"check_id": analysis.check_id, "risk_level": plan.risk_level, "error_type": analysis.error_type})
                return plan
        return self._refused(analysis, "manual review. tiny brain can point, not patch.", "medium", candidate.relative_path)

    def _python_syntax_plan(self, analysis: CheckFailureAnalysis, candidate: RelatedFileCandidate) -> CheckFixPlan | None:
        if "never closed" not in analysis.error_message.lower() and "unexpected eof" not in analysis.error_message.lower():
            return None
        lines = self._snippet_lines(candidate.snippet)
        line_no = candidate.suspected_line or analysis.suspected_line
        if line_no is None or line_no not in lines:
            return None
        before_line = lines[line_no]
        if before_line.rstrip().endswith(")") or before_line.count("(") <= before_line.count(")"):
            return None
        after_line = before_line.rstrip() + ")"
        before_text, after_text = self._replace_line(candidate.absolute_path, line_no, after_line)
        if before_text == after_text:
            return None
        diff = self.diff.unified_diff(candidate.relative_path, before_text, after_text)
        block = self.diff.replacement_block(
            candidate.relative_path,
            before_text,
            after_text,
            "Add a missing closing parenthesis for the syntax error.",
        )
        suggestion = EditSuggestionResult(
            True,
            project_id=analysis.project_id,
            target_files=[candidate.relative_path],
            user_request="fix failed check syntax error",
            summary=f"Fix missing parenthesis in {candidate.relative_path}.",
            risk_level="low",
            requires_user_review=True,
            can_apply_automatically=False,
            suggested_diff=UnifiedDiffSuggestion(candidate.relative_path, diff.diff_text, diff.line_count),
            replacement_blocks=[block],
            explanation=block.explanation,
            display_text=f"tiny fix ready for {candidate.relative_path}:{line_no}.",
        )
        return CheckFixPlan(
            analysis.check_id,
            analysis.project_id,
            analysis.error_type,
            analysis.error_message,
            [candidate.relative_path],
            candidate.relative_path,
            line_no,
            min(0.9, max(analysis.confidence, 0.75)),
            suggestion.summary,
            "low",
            "",
            True,
            "",
            suggestion,
        )

    @staticmethod
    def _snippet_lines(snippet: str) -> dict[int, str]:
        lines: dict[int, str] = {}
        for raw in snippet.splitlines():
            prefix, sep, value = raw.partition(": ")
            if not sep:
                continue
            try:
                lines[int(prefix)] = value
            except ValueError:
                continue
        return lines

    @staticmethod
    def _replace_line(path: str, line_no: int, replacement: str) -> tuple[str, str]:
        try:
            before_text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return "", ""
        lines = before_text.splitlines(keepends=True)
        if line_no < 1 or line_no > len(lines):
            return before_text, before_text
        newline = "\n" if lines[line_no - 1].endswith("\n") else ""
        lines[line_no - 1] = replacement + newline
        return before_text, "".join(lines)

    @staticmethod
    def _high_risk(path: str, message: str, user_request: str) -> bool:
        haystack = f"{path} {message} {user_request}".lower()
        return any(hint in haystack for hint in HIGH_RISK_HINTS)

    @staticmethod
    def _refused(
        analysis: CheckFailureAnalysis,
        reason: str,
        risk_level: str = "blocked",
        suspected_file: str = "",
    ) -> CheckFixPlan:
        LOGGER.info(
            "fix_suggestion_refused",
            extra={"check_id": analysis.check_id, "risk_level": risk_level, "error_type": analysis.error_type},
        )
        return CheckFixPlan(
            analysis.check_id,
            analysis.project_id,
            analysis.error_type,
            analysis.error_message,
            [suspected_file] if suspected_file else [],
            suspected_file or analysis.suspected_file,
            analysis.suspected_line,
            analysis.confidence,
            "",
            risk_level,
            "",
            True,
            reason,
            None,
        )
