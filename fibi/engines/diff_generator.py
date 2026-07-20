"""Unified diff and replacement block helpers for safe edit suggestions."""

from __future__ import annotations

import difflib

from fibi.engines.types import ReplacementBlock, UnifiedDiffSuggestion


class DiffGenerator:
    """Generate suggestions without writing patches to disk."""

    def __init__(self, max_chars: int = 120_000) -> None:
        self.max_chars = max_chars

    def unified_diff(self, file_path: str, before: str, after: str) -> UnifiedDiffSuggestion:
        if len(before) > self.max_chars or len(after) > self.max_chars:
            return UnifiedDiffSuggestion(file_path, "Refused: file crumb too big for one safe diff.", 0)
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm="",
            )
        )
        diff_text = "\n".join(diff_lines)
        return UnifiedDiffSuggestion(file_path, diff_text, len(diff_lines))

    def replacement_block(
        self,
        file_path: str,
        before: str,
        after: str,
        explanation: str = "",
    ) -> ReplacementBlock:
        start, end, before_block, after_block = self._changed_region(before, after)
        return ReplacementBlock(file_path, start, end, before_block, after_block, explanation)

    @staticmethod
    def _changed_region(before: str, after: str) -> tuple[int, int, str, str]:
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                return (
                    i1 + 1,
                    max(i1 + 1, i2),
                    "\n".join(before_lines[i1:i2]),
                    "\n".join(after_lines[j1:j2]),
                )
        return 1, 1, "", ""
