"""Safe project edit suggestions for Fibi v0.16.

Fibi can inspect user-approved project files and suggest manual diffs. This
module deliberately does not write files, apply patches, install packages, or
run commands.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.diff_generator import DiffGenerator
from fibi.engines.edit_safety_engine import EditSafetyEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import (
    EditSuggestionResult,
    ProjectEditPlan,
    ProjectEditRequest,
    ReplacementBlock,
    UnifiedDiffSuggestion,
)
from fibi.paths import data_path

EDIT_JOURNAL_PATH = data_path("project_edit_journal.jsonl")
LAST_EDIT_PATH = data_path("last_edit_suggestion.json")

EDIT_INTENT_WORDS = (
    "change",
    "update",
    "modify",
    "replace",
    "fix this file",
    "refactor",
    "add button",
    "make the button",
    "make button",
    "remove text",
    "improve ui",
    "make it look",
    "edit",
)


class ProjectEditPlanner:
    """Plan and render manual-only edit suggestions for active projects."""

    def __init__(
        self,
        workspace: ProjectWorkspaceEngine,
        safety: EditSafetyEngine | None = None,
        diff: DiffGenerator | None = None,
        journal_path: Path = EDIT_JOURNAL_PATH,
        last_path: Path = LAST_EDIT_PATH,
    ) -> None:
        self.workspace = workspace
        self.safety = safety or EditSafetyEngine()
        self.diff = diff or DiffGenerator()
        self.journal_path = Path(journal_path)
        self.last_path = Path(last_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_suggestion: EditSuggestionResult | None = None

    def detects_edit_intent(self, text: str) -> bool:
        lowered = text.lower()
        return any(word in lowered for word in EDIT_INTENT_WORDS)

    def plan(self, user_request: str, target_files: list[str] | None = None, source: str = "user_message") -> EditSuggestionResult:
        project = self.workspace.current()
        if project is None:
            return self._result(False, display_text="no project nest for edit crumbs.", refused_reason="no active project")
        requested_files = target_files or self.find_target_files(user_request)
        safety = self.safety.assess(user_request, requested_files)
        if not safety.allowed:
            result = self._result(
                False,
                project_id=project.project_id,
                target_files=requested_files,
                user_request=user_request,
                risk_level=safety.risk.risk_level,
                refused_reason=safety.refused_reason,
                display_text=safety.fibi_reply,
            )
            self.journal(result, refused=True)
            return result
        if not requested_files:
            candidates = self._candidate_files_for_request(user_request)
            hint = ", ".join(candidates[:3]) if candidates else "tell me the file path"
            result = self._result(
                False,
                project_id=project.project_id,
                user_request=user_request,
                risk_level=safety.risk.risk_level,
                summary="needs explicit file",
                explanation=f"Ambiguous edit request. Candidates: {hint}.",
                display_text=f"which file crumb? maybe {hint}.",
            )
            self.journal(result, refused=False)
            return result
        edit_request = ProjectEditRequest(project.project_id, requested_files, user_request, bool(target_files), source)
        plan = ProjectEditPlan(
            edit_request.project_id,
            edit_request.target_files,
            edit_request.user_request,
            f"Manual-only suggestion for {', '.join(edit_request.target_files)}.",
            safety.risk.risk_level,
            requires_user_review=True,
            can_apply_automatically=False,
            explanation=safety.risk.reason,
        )
        return self.suggest(plan)

    def suggest(self, plan: ProjectEditPlan) -> EditSuggestionResult:
        safety = self.safety.assess(plan.user_request, plan.target_files)
        if not safety.allowed:
            result = self._result(
                False,
                project_id=plan.project_id,
                target_files=plan.target_files,
                user_request=plan.user_request,
                risk_level=safety.risk.risk_level,
                refused_reason=safety.refused_reason,
                display_text=safety.fibi_reply,
            )
            self.journal(result, refused=True)
            return result

        relative_path = plan.target_files[0]
        read = self.workspace.read_file(relative_path)
        if not read.ok or read.item is None:
            result = self._result(
                False,
                project_id=plan.project_id,
                target_files=plan.target_files,
                user_request=plan.user_request,
                risk_level=safety.risk.risk_level,
                refused_reason=read.error or "read failed",
                display_text=read.message or "can't chew that file yet.",
            )
            self.journal(result, refused=True)
            return result

        before = read.item.content_text
        after, explanation = self._local_rewrite(before, plan.user_request, relative_path)
        if before == after:
            explanation = (
                "I can inspect this file, but the requested edit needs a more exact instruction "
                "or model help. Manual only."
            )
        diff = self.diff.unified_diff(relative_path, before, after)
        block = self.diff.replacement_block(relative_path, before, after, explanation)
        display = self._format_display(relative_path, safety.risk.risk_level, diff.diff_text, block.after, explanation)
        result = self._result(
            True,
            project_id=plan.project_id,
            target_files=plan.target_files,
            user_request=plan.user_request,
            summary=plan.summary,
            risk_level=safety.risk.risk_level,
            suggested_diff=diff,
            replacement_blocks=[block],
            explanation=explanation,
            display_text=display,
        )
        self.last_suggestion = result
        self._save_last(result)
        self.journal(result, refused=False)
        return result

    def find_target_files(self, text: str) -> list[str]:
        normalized = text.replace("\\", "/")
        files = self.workspace.files()
        by_path = {entry.relative_path: entry for entry in files}
        matches = []
        for path in by_path:
            if path.lower() in normalized.lower():
                matches.append(path)
        if matches:
            return matches[:3]
        for token in re.findall(r"[\w./-]+\.[A-Za-z0-9]+", normalized):
            clean = token.strip("`'\".,:;")
            if clean in by_path:
                matches.append(clean)
        return matches[:3]

    def explain_last(self) -> str:
        result = self.last_suggestion or self._load_last()
        if result is None:
            return "no edit suggestion yet."
        return f"{result.summary} risk={result.risk_level}. manual only. {result.explanation}"

    def copy_last(self) -> str:
        result = self.last_suggestion or self._load_last()
        if result is None:
            return "no edit suggestion yet."
        if result.suggested_diff and result.suggested_diff.diff_text:
            return result.suggested_diff.diff_text
        if result.replacement_blocks and result.replacement_blocks[0].after:
            return result.replacement_blocks[0].after
        return result.display_text

    def clear_last(self) -> None:
        self.last_suggestion = None
        try:
            self.last_path.unlink(missing_ok=True)
        except OSError:
            pass

    def journal(self, result: EditSuggestionResult, refused: bool) -> None:
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "project_id": result.project_id,
            "requested_files": result.target_files,
            "risk_level": result.risk_level,
            "suggestion_created": bool(result.ok),
            "refused": refused or bool(result.refused_reason),
            "summary": result.summary or result.refused_reason or "edit suggestion event",
        }
        try:
            with self.journal_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
        except OSError:
            pass

    def _candidate_files_for_request(self, request: str) -> list[str]:
        lowered = request.lower()
        files = [entry.relative_path for entry in self.workspace.files() if entry.safe_to_read]
        if "page" in lowered:
            return [path for path in files if path.endswith(("page.tsx", "page.jsx", "index.tsx", "index.jsx", "index.html"))][:4]
        if "button" in lowered:
            return [path for path in files if "button" in path.lower()][:4]
        return files[:4]

    def _local_rewrite(self, content: str, request: str, file_path: str) -> tuple[str, str]:
        lowered = request.lower()
        if "blue" in lowered:
            replaced = self._make_blue(content)
            return replaced, "Suggested a blue UI styling change."
        replacement = self._quoted_replacement(request)
        if replacement:
            before, after = replacement
            if before in content:
                return content.replace(before, after, 1), f"Replace '{before}' with '{after}'."
        if "title" in lowered:
            title = self._quoted_text(request) or "New title"
            return self._replace_title_like(content, title), f"Suggested title text: {title}."
        if "remove text" in lowered:
            text = self._quoted_text(request)
            if text and text in content:
                return content.replace(text, "", 1), f"Remove text: {text}."
        return content, f"Reviewed {file_path}; needs a more specific requested replacement."

    @staticmethod
    def _make_blue(content: str) -> str:
        class_match = re.search(r'className=(["\'])(.*?)\1', content)
        if class_match and "blue" not in class_match.group(2):
            new_class = (class_match.group(2) + " bg-blue-500 text-white").strip()
            return content[: class_match.start(2)] + new_class + content[class_match.end(2) :]
        color_match = re.search(r"color\s*:\s*[^;}\n]+", content)
        if color_match:
            return content[: color_match.start()] + "color: #2563eb" + content[color_match.end() :]
        return content.replace("<button", '<button className="bg-blue-500 text-white"', 1) if "<button" in content else content

    @staticmethod
    def _quoted_replacement(request: str) -> tuple[str, str] | None:
        match = re.search(r"replace\s+['\"](.+?)['\"]\s+with\s+['\"](.+?)['\"]", request, re.IGNORECASE)
        return (match.group(1), match.group(2)) if match else None

    @staticmethod
    def _quoted_text(request: str) -> str:
        match = re.search(r"['\"](.+?)['\"]", request)
        return match.group(1) if match else ""

    @staticmethod
    def _replace_title_like(content: str, title: str) -> str:
        for pattern in (r"(<title>)(.*?)(</title>)", r"(<h1[^>]*>)(.*?)(</h1>)"):
            if re.search(pattern, content, flags=re.IGNORECASE | re.DOTALL):
                return re.sub(
                    pattern,
                    lambda match: f"{match.group(1)}{title}{match.group(3)}",
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL,
                )
        return content

    @staticmethod
    def _format_display(file_path: str, risk: str, diff_text: str, replacement: str, explanation: str) -> str:
        body = diff_text.strip() or replacement.strip() or "No exact local diff generated."
        return (
            f"manual edit suggestion for {file_path}. risk: {risk}. no auto-apply.\n\n"
            f"{explanation}\n\n"
            f"```diff\n{body[:3500]}\n```"
        )

    def _save_last(self, result: EditSuggestionResult) -> None:
        payload = asdict(result)
        try:
            self.last_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_last(self) -> EditSuggestionResult | None:
        try:
            raw = json.loads(self.last_path.read_text(encoding="utf-8"))
            if isinstance(raw.get("suggested_diff"), dict):
                raw["suggested_diff"] = UnifiedDiffSuggestion(**raw["suggested_diff"])
            raw["replacement_blocks"] = [
                ReplacementBlock(**item)
                for item in raw.get("replacement_blocks", [])
                if isinstance(item, dict)
            ]
            return EditSuggestionResult(**raw)
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _result(ok: bool, **kwargs) -> EditSuggestionResult:
        return EditSuggestionResult(ok=ok, can_apply_automatically=False, **kwargs)
