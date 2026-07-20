"""Local safe browser helper for Fibi v0.27.

Fibi may save links, summarize user-provided page text, and open URLs only after
explicit confirmation. This engine does not fetch remote pages.
"""

from __future__ import annotations

import json
import uuid
import webbrowser
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable

from fibi.engines.browser_research_notes_engine import BrowserResearchNotesEngine
from fibi.engines.browser_safety_engine import BrowserSafetyEngine
from fibi.engines.html_text_extractor import HtmlTextExtractor
from fibi.engines.types import (
    BrowserOpenRequest,
    BrowserPageNote,
    BrowserResearchNote,
    BrowserSession,
    BrowserSummaryResult,
    BrowserTaskPlan,
    PendingBrowserAction,
)
from fibi.paths import data_path


class BrowserHelperEngine:
    def __init__(
        self,
        sessions_path: Path | None = None,
        notes_path: Path | None = None,
        *,
        safety: BrowserSafetyEngine | None = None,
        extractor: HtmlTextExtractor | None = None,
        research: BrowserResearchNotesEngine | None = None,
        browser_open: Callable[[str], bool] | None = None,
    ) -> None:
        self.sessions_path = Path(sessions_path) if sessions_path else data_path("browser/browser_sessions.jsonl")
        self.notes_path = Path(notes_path) if notes_path else data_path("browser/browser_notes.jsonl")
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        self.notes_path.parent.mkdir(parents=True, exist_ok=True)
        self.safety = safety or BrowserSafetyEngine()
        self.extractor = extractor or HtmlTextExtractor()
        self.research = research or BrowserResearchNotesEngine()
        self.browser_open = browser_open or webbrowser.open_new_tab
        self.active_session_id = ""
        self.pending_action: PendingBrowserAction | None = None
        self.last_safety_result = self.safety.classify_request("startup")

    def start_session(self, goal: str, linked_project_id: str = "", linked_issue_id: str = "") -> BrowserSession:
        now = _now()
        session = BrowserSession(
            browser_session_id="BRS-" + uuid.uuid4().hex[:8],
            task_goal=goal.strip()[:500] or "browser helper session",
            created_at=now,
            updated_at=now,
            linked_project_id=linked_project_id,
            linked_issue_id=linked_issue_id,
        )
        self._append(self.sessions_path, asdict(session))
        self.active_session_id = session.browser_session_id
        return session

    def current_session(self) -> BrowserSession | None:
        sessions = self.sessions()
        if self.active_session_id:
            for session in reversed(sessions):
                if session.browser_session_id == self.active_session_id and session.status == "active":
                    return session
        for session in reversed(sessions):
            if session.status == "active":
                self.active_session_id = session.browser_session_id
                return session
        return None

    def sessions(self, limit: int = 20) -> list[BrowserSession]:
        return [BrowserSession(**row) for row in self._read(self.sessions_path)[-limit:]]

    def notes(self, limit: int = 20) -> list[BrowserPageNote]:
        return [BrowserPageNote(**row) for row in self._read(self.notes_path)[-limit:]]

    def clear_session(self) -> bool:
        session = self.current_session()
        if session is None:
            return False
        sessions = self.sessions(limit=500)
        for item in sessions:
            if item.browser_session_id == session.browser_session_id:
                item.status = "closed"
                item.updated_at = _now()
        self._write_all(self.sessions_path, [asdict(item) for item in sessions])
        self.active_session_id = ""
        self.pending_action = None
        return True

    def request_open(self, url: str, title: str = "") -> BrowserOpenRequest | None:
        result = self.safety.validate_url(url)
        self.last_safety_result = result
        if not result.allowed:
            return None
        session = self.current_session() or self.start_session(f"open {result.domain}")
        now = _now()
        request = BrowserOpenRequest(
            browser_session_id=session.browser_session_id,
            url=result.normalized_url,
            title=title,
            created_at=now,
            updated_at=now,
            domain=result.domain,
        )
        self.pending_action = PendingBrowserAction(
            browser_session_id=session.browser_session_id,
            action_type="open_url",
            url=request.url,
            title=title,
            created_at=now,
            updated_at=now,
            domain=result.domain,
        )
        return request

    def confirm_pending(self) -> tuple[bool, str, str]:
        if self.pending_action is None:
            return False, "no browser action waiting.", ""
        url = self.pending_action.url
        domain = self.pending_action.domain
        try:
            self.browser_open(url)
        except Exception as exc:
            return False, "browser resisted.", str(exc)
        self.pending_action = None
        return True, f"opened {domain}. no reading, just doorway.", url

    def cancel_pending(self) -> bool:
        had_pending = self.pending_action is not None
        self.pending_action = None
        return had_pending

    def save_url_note(self, url: str, note: str, title: str = "") -> BrowserPageNote | None:
        safety = self.safety.validate_url(url)
        self.last_safety_result = safety
        if not safety.allowed:
            return None
        session = self.current_session() or self.start_session(f"notes for {safety.domain}")
        now = _now()
        page_note = BrowserPageNote(
            browser_session_id=session.browser_session_id,
            url=safety.normalized_url,
            title=title or safety.domain,
            user_provided_text="",
            summary=note.strip()[:1000] or "saved link",
            created_at=now,
            updated_at=now,
            notes=[note.strip()[:500]] if note.strip() else [],
            note_id="BRN-" + uuid.uuid4().hex[:8],
        )
        self._append(self.notes_path, asdict(page_note))
        return page_note

    def summarize_user_text(self, text: str, title: str = "provided page text") -> BrowserSummaryResult:
        readable = self.extractor.extract(text) if self.extractor.looks_like_html(text) else text
        summary = self.research.summarize(readable)
        return BrowserSummaryResult(True, summary, title=title, source="user_provided_page_text")

    def save_page_text_note(self, text: str, url: str = "", title: str = "provided page text") -> BrowserPageNote:
        session = self.current_session() or self.start_session("summarize provided page")
        summary = self.summarize_user_text(text, title).summary
        now = _now()
        note = BrowserPageNote(
            browser_session_id=session.browser_session_id,
            url=url,
            title=title,
            user_provided_text=text[:1200],
            summary=summary,
            created_at=now,
            updated_at=now,
            note_id="BRN-" + uuid.uuid4().hex[:8],
        )
        self._append(self.notes_path, asdict(note))
        return note

    def research_note(self, text: str, url: str = "", title: str = "") -> BrowserResearchNote:
        session = self.current_session() or self.start_session("browser research")
        readable = self.extractor.extract(text) if self.extractor.looks_like_html(text) else text
        note = self.research.create_note(
            session_id=session.browser_session_id,
            text=readable,
            url=url,
            title=title,
            task_goal=session.task_goal,
        )
        saved = self.save_page_text_note(note.user_provided_text, url=url, title=note.title)
        note.summary = saved.summary
        return note

    def plan(self, goal: str = "") -> BrowserTaskPlan:
        session = self.current_session() or self.start_session(goal or "browser helper")
        now = _now()
        task_goal = goal.strip() or session.task_goal
        steps = [
            "open the URL only if you confirm",
            "review the page manually",
            "paste useful public page text into Fibi",
            "ask Fibi to summarize the provided text",
            "save only the note you approve",
        ]
        if any(word in task_goal.lower() for word in ("contact", "outreach", "business")):
            steps.append("draft outreach manually from user-provided public details")
        return BrowserTaskPlan(session.browser_session_id, task_goal, steps, now, now)

    def status_line(self) -> str:
        session = self.current_session()
        pending = self.pending_action.domain if self.pending_action else "none"
        return f"browser helper on. session: {session.task_goal if session else 'none'}. pending: {pending}."

    def last_safety_line(self) -> str:
        result = self.last_safety_result
        return f"browser safety: {result.safety_level}. blocked={str(result.blocked).lower()}. {result.reason}."

    def _append(self, path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def _read(path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        rows: list[dict[str, object]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict):
                rows.append(raw)
        return rows

    @staticmethod
    def _write_all(path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
