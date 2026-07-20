"""Create local research notes from user-provided page text."""

from __future__ import annotations

import re

from fibi.engines.types import BrowserResearchNote


class BrowserResearchNotesEngine:
    """Summarize only what the user pasted or dropped."""

    def create_note(self, *, session_id: str, text: str, url: str = "", title: str = "", task_goal: str = "") -> BrowserResearchNote:
        summary = self.summarize(text)
        notes = self.manual_next_steps(text)
        return BrowserResearchNote(
            browser_session_id=session_id,
            url=url,
            title=title or "browser research note",
            user_provided_text=text[:1200],
            summary=summary,
            task_goal=task_goal,
            notes=notes,
        )

    def summarize(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = " ".join(lines)
        if not joined:
            return "no readable page crumbs."
        sentences = re.split(r"(?<=[.!?])\s+", joined)
        return " ".join(sentences[:3])[:700]

    def manual_next_steps(self, text: str) -> list[str]:
        lowered = text.lower()
        steps = ["review the page manually", "copy only useful public details", "avoid passwords, payment, and private account data"]
        if any(word in lowered for word in ("contact", "email", "phone")):
            steps.append("draft outreach from the visible public contact info")
        if any(word in lowered for word in ("pricing", "service", "product")):
            steps.append("note what they offer and one possible pain point")
        return steps[:5]
