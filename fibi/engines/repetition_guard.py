"""Tiny persisted buffers that make repetition resolve to alternatives or silence."""

from __future__ import annotations

from fibi.engines.types import RepetitionState


class RepetitionGuard:
    LIMIT = 8

    def __init__(self, saved: dict | None = None) -> None:
        data = saved or {}
        self.state = RepetitionState(**{
            field: list(data.get(field, []))[-self.LIMIT:]
            for field in RepetitionState.__dataclass_fields__
        })

    def allows_line(self, text: str, *, direct: bool = False) -> bool:
        return direct or bool(text.strip()) and text.strip().lower() not in self.state.spoken_lines[-5:]

    def allows_category(self, category: str, *, direct: bool = False) -> bool:
        return direct or self.state.reaction_categories[-3:].count(category) < 2

    def allows_motion(self, motion_name: str) -> bool:
        return self.state.motion_names[-3:].count(motion_name) < 2

    def remember(self, *, line: str = "", category: str = "", motion: str = "", ritual: str = "", idle: str = "", project: str = "") -> None:
        pairs = (("spoken_lines", line.lower().strip()), ("reaction_categories", category), ("motion_names", motion), ("rituals", ritual), ("idle_reactions", idle.lower().strip()), ("project_references", project.lower().strip()))
        for field, value in pairs:
            if value:
                values = getattr(self.state, field)
                setattr(self.state, field, (values + [value])[-self.LIMIT:])

    def export_state(self) -> dict[str, list[str]]:
        return {field: list(getattr(self.state, field)) for field in RepetitionState.__dataclass_fields__}
