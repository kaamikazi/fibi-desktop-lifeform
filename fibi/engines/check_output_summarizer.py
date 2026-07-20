"""Local check-output summarizer for Fibi project checks."""

from __future__ import annotations

import re

from fibi.engines.types import ProjectCheckOutputSummary


class CheckOutputSummarizer:
    """Extract tiny useful summaries without calling a model."""

    def summarize(self, stdout: str, stderr: str, exit_code: int | None, timed_out: bool = False) -> ProjectCheckOutputSummary:
        output = f"{stdout}\n{stderr}".strip()
        lowered = output.lower()
        if timed_out:
            return ProjectCheckOutputSummary("timeout", "check timed out. tiny stopwatch gave up.", 1, 0)
        if "command not found" in lowered or "not recognized" in lowered or "no module named" in lowered:
            return ProjectCheckOutputSummary("failure", "missing command or dependency.", 1, 0, ["dependency may be missing"])
        if "syntaxerror" in lowered:
            return ProjectCheckOutputSummary("failure", "syntax error found.", 1, 0)
        if "importerror" in lowered or "modulenotfounderror" in lowered:
            return ProjectCheckOutputSummary("failure", "import error found.", 1, 0)
        if "typescript" in lowered or re.search(r"\bts\d{4}\b", output, re.IGNORECASE):
            return ProjectCheckOutputSummary("failure" if exit_code else "success", "TypeScript check finished.", self._count_errors(output), self._count_warnings(output))
        if "failed" in lowered or "failure" in lowered or (exit_code not in {0, None}):
            count = self._count_errors(output)
            return ProjectCheckOutputSummary("failure", f"check failed with {count or 1} error crumb(s).", count or 1, self._count_warnings(output))
        if exit_code == 0:
            return ProjectCheckOutputSummary("success", "check survived.", 0, self._count_warnings(output))
        return ProjectCheckOutputSummary("error", "check ended weirdly.", 1, self._count_warnings(output))

    @staticmethod
    def _count_errors(text: str) -> int:
        matches = re.findall(r"\b(error|failed|failure|traceback)\b", text, flags=re.IGNORECASE)
        return len(matches)

    @staticmethod
    def _count_warnings(text: str) -> int:
        return len(re.findall(r"\bwarning\b", text, flags=re.IGNORECASE))
