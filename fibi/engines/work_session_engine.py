"""Local guided work-session state for supervised project workflows."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import WorkSession, WorkSessionPlan, WorkSessionProgress, WorkSessionState, WorkSessionStep, WorkSessionSummary
from fibi.paths import data_path

LOGGER = logging.getLogger(__name__)


class WorkSessionEngine:
    """Persist one active supervised workflow session locally."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else data_path("work_sessions.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def create_session(self, project_id: str, user_goal: str, plan: WorkSessionPlan) -> WorkSession:
        now = self._now()
        session = WorkSession(
            session_id=uuid.uuid4().hex[:12],
            project_id=project_id,
            user_goal=user_goal.strip(),
            status="active",
            created_at=now,
            updated_at=now,
            steps=plan.steps,
            notes=plan.notes,
            risk_level=plan.risk_level,
        )
        self.state.sessions.append(session)
        self.state.active_session_id = session.session_id
        self._save()
        LOGGER.info("session_created", extra={"session_id": session.session_id, "step_count": len(session.steps)})
        return session

    def active(self) -> WorkSession | None:
        if not self.state.active_session_id:
            return None
        return self.get(self.state.active_session_id)

    def get(self, session_id: str) -> WorkSession | None:
        return next((session for session in self.state.sessions if session.session_id == session_id), None)

    def resume(self) -> WorkSession | None:
        session = self.active()
        if session is None:
            return None
        if session.status == "paused":
            session.status = "active"
            session.updated_at = self._now()
            self._save()
            LOGGER.info("session_resumed", extra={"session_id": session.session_id})
        return session

    def pause(self) -> WorkSession | None:
        session = self.active()
        if session is None:
            return None
        session.status = "paused"
        session.updated_at = self._now()
        self._save()
        LOGGER.info("session_paused", extra={"session_id": session.session_id})
        return session

    def cancel(self) -> WorkSession | None:
        session = self.active()
        if session is None:
            return None
        session.status = "cancelled"
        session.updated_at = self._now()
        self.state.active_session_id = ""
        self._save()
        LOGGER.info("session_cancelled", extra={"session_id": session.session_id})
        return session

    def complete(self, summary: str = "") -> WorkSession | None:
        session = self.active()
        if session is None:
            return None
        session.status = "completed"
        session.last_result_summary = summary or session.last_result_summary
        session.updated_at = self._now()
        self.state.active_session_id = ""
        self._save()
        LOGGER.info("session_completed", extra={"session_id": session.session_id})
        return session

    def current_step(self, session: WorkSession | None = None) -> WorkSessionStep | None:
        session = session or self.active()
        if session is None or not session.steps:
            return None
        if session.current_step_index >= len(session.steps):
            return None
        return session.steps[session.current_step_index]

    def mark_step(self, step: WorkSessionStep, status: str, summary: str = "", error: str = "") -> None:
        session = self.active()
        if session is None:
            return
        step.status = status
        step.result_summary = summary or step.result_summary
        step.error = error or step.error
        if status == "completed" and step.step_id not in session.completed_steps:
            session.completed_steps.append(step.step_id)
            session.current_step_index = min(session.current_step_index + 1, len(session.steps))
            LOGGER.info("session_step_completed", extra={"session_id": session.session_id, "step_type": step.step_type})
        elif status == "active":
            LOGGER.info("session_step_started", extra={"session_id": session.session_id, "step_type": step.step_type})
        session.last_result_summary = summary or session.last_result_summary
        session.updated_at = self._now()
        self._save()

    def progress(self) -> WorkSessionProgress | None:
        session = self.active()
        if session is None:
            return None
        current = self.current_step(session)
        next_index = session.current_step_index + 1
        next_step = session.steps[next_index] if next_index < len(session.steps) else None
        summary = f"{len(session.completed_steps)}/{len(session.steps)} crumbs done."
        return WorkSessionProgress(session.session_id, session.status, session.current_step_index, len(session.steps), list(session.completed_steps), current, next_step, summary)

    def summaries(self, limit: int = 5) -> list[WorkSessionSummary]:
        rows = self.state.sessions[-max(1, limit):]
        return [
            WorkSessionSummary(
                session.session_id,
                session.project_id,
                session.user_goal,
                session.status,
                len(session.completed_steps),
                len(session.steps),
                session.last_result_summary,
            )
            for session in rows
        ]

    def clear_completed(self) -> int:
        before = len(self.state.sessions)
        self.state.sessions = [session for session in self.state.sessions if session.status != "completed"]
        if self.state.active_session_id and not self.get(self.state.active_session_id):
            self.state.active_session_id = ""
        self._save()
        return before - len(self.state.sessions)

    def _load(self) -> WorkSessionState:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return WorkSessionState()
        sessions: list[WorkSession] = []
        for item in raw.get("sessions", []) if isinstance(raw, dict) else []:
            try:
                steps = [WorkSessionStep(**step) for step in item.get("steps", [])]
                sessions.append(WorkSession(**{**item, "steps": steps}))
            except TypeError:
                continue
        return WorkSessionState(str(raw.get("active_session_id", "")), sessions)

    def _save(self) -> None:
        payload = {
            "active_session_id": self.state.active_session_id,
            "sessions": [asdict(session) for session in self.state.sessions],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
