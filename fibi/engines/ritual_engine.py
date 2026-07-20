"""Small recurring rituals that make sessions feel connected."""

from __future__ import annotations

from datetime import datetime, timedelta

from fibi.engines.reaction_library import ReactionLibrary
from fibi.engines.types import CreatureReaction, RitualResult, RitualState


class RitualEngine:
    """Evaluate explicit local rituals with once-per-window cooldowns."""

    def __init__(
        self,
        reactions: ReactionLibrary,
        saved_states: dict[str, dict] | None = None,
    ) -> None:
        self.reactions = reactions
        self.states = {
            name: RitualState(
                name=name,
                last_triggered_at=value.get("last_triggered_at"),
                times_triggered=int(value.get("times_triggered", 0) or 0),
            )
            for name, value in (saved_states or {}).items()
        }

    def startup(
        self,
        time_of_day: str,
        affection: int,
        gap_hours: float | None,
        project: str | None = None,
        now: datetime | None = None,
    ) -> RitualResult:
        current = now or datetime.now().astimezone()
        if self._startup_ritual_recent(current):
            return RitualResult(name="startup", reaction=None, triggered=False)
        if project and self._eligible("project_revisit", timedelta(hours=12), current):
            return self._trigger("project_revisit", "ritual_project_return", affection, time_of_day, {"project": project}, current)
        if gap_hours is not None and gap_hours >= 3 and self._eligible("return_after_absence", timedelta(hours=3), current):
            return self._trigger("return_after_absence", "ritual_daily_return", affection, time_of_day, {}, current)
        first = self.states.get("first_start_of_day")
        if not first or not first.last_triggered_at or first.last_triggered_at[:10] != current.date().isoformat():
            category = self._time_category(time_of_day)
            return self._trigger("first_start_of_day", category, affection, time_of_day, {}, current)
        time_rituals = {
            "morning": ("morning_greeting", "ritual_morning"),
            "afternoon": ("afternoon_checkin", "ritual_afternoon"),
            "evening": ("evening_settle", "ritual_evening"),
            "late_night": ("late_night_warning", "late_night"),
        }
        if time_of_day in time_rituals:
            name, category = time_rituals[time_of_day]
            if self._eligible(name, timedelta(hours=12), current):
                return self._trigger(name, category, affection, time_of_day, {}, current)
        return RitualResult(name="startup", reaction=None, triggered=False)

    def _startup_ritual_recent(self, now: datetime) -> bool:
        for name in (
            "project_revisit", "return_after_absence", "first_start_of_day",
            "morning_greeting", "afternoon_checkin", "evening_settle", "late_night_warning",
        ):
            state = self.states.get(name)
            if not state or not state.last_triggered_at:
                continue
            try:
                previous = datetime.fromisoformat(state.last_triggered_at)
                if previous.tzinfo is None:
                    previous = previous.astimezone()
                if now - previous < timedelta(minutes=20):
                    return True
            except ValueError:
                continue
        return False

    def shutdown(self, affection: int, time_of_day: str, now: datetime | None = None) -> RitualResult:
        current = now or datetime.now().astimezone()
        if not self._eligible("tiny_goodbye", timedelta(minutes=20), current):
            return RitualResult("tiny_goodbye", None, False)
        return self._trigger("tiny_goodbye", "ritual_shutdown", affection, time_of_day, {}, current)

    def ambient(
        self,
        time_of_day: str,
        affection: int,
        idle_seconds: float,
        now: datetime | None = None,
    ) -> RitualResult:
        """Evaluate quiet-time rituals without competing with direct messages."""
        current = now or datetime.now().astimezone()
        if time_of_day == "late_night" and self._eligible("late_night_warning", timedelta(hours=2), current):
            return self._trigger("late_night_warning", "late_night", affection, time_of_day, {}, current)
        if time_of_day in {"night", "late_night"} and idle_seconds >= 15 * 60 and self._eligible("bedtime_nap", timedelta(hours=2), current):
            return self._trigger("bedtime_nap", "ritual_bedtime", affection, time_of_day, {}, current)
        return RitualResult("ambient", None, False)

    def bedtime_nap(self, affection: int, time_of_day: str, now: datetime | None = None) -> RitualResult:
        current = now or datetime.now().astimezone()
        if time_of_day not in {"night", "late_night"} or not self._eligible("bedtime_nap", timedelta(hours=2), current):
            return RitualResult("bedtime_nap", None, False)
        return self._trigger("bedtime_nap", "ritual_bedtime", affection, time_of_day, {}, current)

    def mark_daily_summary(self, affection: int, time_of_day: str, now: datetime | None = None) -> RitualResult:
        current = now or datetime.now().astimezone()
        if not self._eligible("daily_summary", timedelta(hours=20), current):
            return RitualResult("daily_summary", None, False)
        return self._trigger("daily_summary", "ritual_daily_summary", affection, time_of_day, {}, current)

    @staticmethod
    def _time_category(time_of_day: str) -> str:
        return {
            "morning": "ritual_morning",
            "afternoon": "ritual_afternoon",
            "evening": "ritual_evening",
            "late_night": "late_night",
        }.get(time_of_day, "greeting")

    def export_state(self) -> dict[str, dict]:
        return {
            name: {
                "last_triggered_at": state.last_triggered_at,
                "times_triggered": state.times_triggered,
            }
            for name, state in self.states.items()
        }

    def _eligible(self, name: str, cooldown: timedelta, now: datetime) -> bool:
        state = self.states.get(name)
        if state is None or not state.last_triggered_at:
            return True
        try:
            previous = datetime.fromisoformat(state.last_triggered_at)
            if previous.tzinfo is None:
                previous = previous.astimezone()
            return now - previous >= cooldown
        except ValueError:
            return True

    def _trigger(
        self,
        name: str,
        category: str,
        affection: int,
        time_of_day: str,
        values: dict[str, str],
        now: datetime,
    ) -> RitualResult:
        picked = self.reactions.choose(
            category, affection=affection, time_of_day=time_of_day, values=values
        )
        state = self.states.setdefault(name, RitualState(name))
        state.last_triggered_at = now.isoformat(timespec="seconds")
        state.times_triggered += 1
        reaction = CreatureReaction(picked.text, picked.mood, name)
        return RitualResult(name, reaction, True)
