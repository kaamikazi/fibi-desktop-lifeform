"""Fibi's presence, mood state machine, and small behavior timing."""

from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime
from pathlib import Path

from fibi.engines.types import (
    BondState,
    Mood,
    MoodDriftResult,
    NapState,
    NestState,
    PresenceState,
    TimePersonalityCurve,
    WindowPosition,
)

from fibi.paths import data_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = data_path("fibi_state.json")

IDLE_REACTIONS = [
    "eepy...",
    "you still there?",
    "guarding desktop.",
    "tiny brain loading...",
    "don't leave me alone with Windows...",
    "hmm...",
]

EXPRESSION_MAP = {
    Mood.HAPPY.value: "happy",
    Mood.SLEEPY.value: "sleepy",
    Mood.CURIOUS.value: "thinking",
    Mood.FOCUSED.value: "thinking",
    Mood.EXCITED.value: "happy",
    Mood.ANNOYED.value: "angry",
    Mood.IDLE.value: "idle",
}


class MoodStateMachine:
    """Small explicit state machine; the model cannot invent mood rules."""

    def __init__(self, initial_mood: str = Mood.IDLE.value) -> None:
        self.current = self.normalize(initial_mood)

    @staticmethod
    def normalize(mood: str) -> str:
        aliases = {
            "angry": Mood.ANNOYED.value,
            "thinking": Mood.CURIOUS.value,
            "talking": Mood.HAPPY.value,
        }
        candidate = aliases.get(str(mood).lower(), str(mood).lower())
        return candidate if candidate in {item.value for item in Mood} else Mood.IDLE.value

    def transition(
        self,
        event: str,
        user_text: str = "",
        reply_text: str = "",
        time_of_day: str = "",
    ) -> str:
        combined = f"{user_text} {reply_text}".lower()
        if event == "speaking":
            return self.current
        if any(word in combined for word in ("nothing works", "i hate this", "i quit", "give up")):
            self.current = Mood.FOCUSED.value
        elif any(word in combined for word in ("error", "bug", "crash", "failed", "broken")):
            self.current = Mood.ANNOYED.value
        elif any(word in combined for word in ("thanks", "good", "cute", "love")):
            self.current = Mood.HAPPY.value
        elif any(word in combined for word in ("wait", "think", "loading", "why", "how")):
            self.current = Mood.CURIOUS.value
        elif any(
            word in combined
            for word in (
                "finished",
                "shipped",
                "worked",
                "success",
                "fixed",
                "done",
                "passed",
                "finally",
                "deployed",
                "launched",
                "solved",
            )
        ):
            self.current = Mood.EXCITED.value
        elif time_of_day in {"night", "late_night"} or any(
            word in combined for word in ("sleep", "tired", "night")
        ):
            self.current = Mood.SLEEPY.value
        elif event == "work":
            self.current = Mood.FOCUSED.value
        else:
            self.current = random.choice([Mood.IDLE.value, Mood.HAPPY.value])
        return self.current


class LifeEngine:
    """Own Fibi's current presence and animation state."""

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        state = self._load_state()
        self._saved_state = dict(state)
        now = datetime.now().astimezone()
        self.previous_last_seen_at = str(state.get("last_seen_at", ""))
        self.last_started_at = now.isoformat(timespec="seconds")
        self.last_seen_at = self.last_started_at
        self.last_shutdown_at = str(state.get("last_shutdown_at", ""))
        self.total_sessions = int(state.get("total_sessions", 0) or 0) + 1
        self.total_interactions = int(
            state.get("total_interactions", state.get("interaction_count", 0)) or 0
        )
        self.startup_line = self._continuity_line(now)

        self.bond = BondState(
            affection=self._score(state.get("affection", 25)),
            trust=self._score(state.get("trust", 20)),
            comfort=self._score(state.get("comfort", 30)),
            mischief=self._score(state.get("mischief", 20)),
            attachment_level=self._score(state.get("attachment_level", 24)),
            last_affection_event_at=state.get("last_affection_event_at"),
        )
        self.nap = NapState(
            is_napping=bool(state.get("is_napping", False)),
            nap_started_at=state.get("nap_started_at"),
            last_woke_at=state.get("last_woke_at"),
            energy=self._score(state.get("energy", 70)),
        )
        self.window_position = self._load_window_position(state)
        self.nest = self._load_nest(state)
        self.ritual_states = dict(state.get("rituals", {}))
        self.repetition_state = dict(state.get("repetition", {}))
        self._nest_candidate = self._load_candidate(state)

        self.mood_machine = MoodStateMachine(state.get("mood", Mood.IDLE.value))
        self.mood = self.mood_machine.current
        self.last_user_message = str(state.get("last_user_message", ""))
        self.interaction_count = int(state.get("interaction_count", 0) or 0)
        self.presence = PresenceState.NAPPING if self.nap.is_napping else PresenceState.IDLE
        self.is_speaking = False
        self.is_thinking = False
        self.is_listening = False

        self.last_interaction_time = time.monotonic()
        self.next_idle_reaction_time = self._next_idle_time()
        self.float_phase = 0.0
        self.breath_phase = 0.0
        self.talk_phase = 0.0
        self._reaction_cooldowns: dict[str, float] = {}
        self._last_idle_lines: list[str] = []
        self._recent_clicks: list[float] = []
        self._recent_drags: list[float] = []
        self.update_bond("session", save=False)
        gap = self.continuity_gap_hours()
        if gap is not None and gap >= 24:
            self.update_bond("long_absence", save=False)
        self.save_state()

    @property
    def expression(self) -> str:
        if self.is_speaking:
            return "talking"
        if self.is_thinking:
            return "thinking"
        if self.nap.is_napping:
            return "sleepy"
        return EXPRESSION_MAP.get(self.mood, "idle")

    def _load_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = dict(self._saved_state)
        state.update(
            {
                "mood": self.mood,
                "last_known_mood": self.mood,
                "last_user_message": self.last_user_message,
                "interaction_count": self.interaction_count,
                "total_interactions": self.total_interactions,
                "last_started_at": self.last_started_at,
                "last_seen_at": self.last_seen_at,
                "last_shutdown_at": self.last_shutdown_at or None,
                "total_sessions": self.total_sessions,
                "affection": self.bond.affection,
                "trust": self.bond.trust,
                "comfort": self.bond.comfort,
                "mischief": self.bond.mischief,
                "attachment_level": self.bond.attachment_level,
                "last_affection_event_at": self.bond.last_affection_event_at,
                "is_napping": self.nap.is_napping,
                "nap_started_at": self.nap.nap_started_at,
                "last_woke_at": self.nap.last_woke_at,
                "energy": self.nap.energy,
                "window_x": self.window_position.x if self.window_position else None,
                "window_y": self.window_position.y if self.window_position else None,
                "nest_x": self.nest.position.x if self.nest.position else None,
                "nest_y": self.nest.position.y if self.nest.position else None,
                "nest_name": self.nest.name,
                "nest_confidence": self.nest.confidence,
                "nest_created_at": self.nest.created_at,
                "last_nested_at": self.nest.last_nested_at,
                "times_returned_to_nest": self.nest.times_returned_to_nest,
                "nest_candidate": self._nest_candidate,
                "rituals": self.ritual_states,
                "repetition": self.repetition_state,
            }
        )
        self._saved_state = state
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def remember_interaction(self, user_message: str, mood: str) -> None:
        self.last_user_message = user_message
        self.interaction_count += 1
        self.total_interactions += 1
        self.last_interaction_time = time.monotonic()
        self.next_idle_reaction_time = self._next_idle_time()
        self.mark_seen(save=False)
        self.nap.energy = self._score(self.nap.energy + 4)
        self.set_mood(mood)

    @staticmethod
    def _score(value: object) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _load_window_position(state: dict) -> WindowPosition | None:
        try:
            x = state.get("window_x")
            y = state.get("window_y")
            if x is None or y is None:
                return None
            return WindowPosition(int(x), int(y))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _load_nest(cls, state: dict) -> NestState:
        try:
            x, y = state.get("nest_x"), state.get("nest_y")
            position = WindowPosition(int(x), int(y)) if x is not None and y is not None else None
        except (TypeError, ValueError):
            position = None
        return NestState(
            position=position,
            name=str(state.get("nest_name", "desktop nest")),
            confidence=max(0.0, min(1.0, float(state.get("nest_confidence", 0.0) or 0.0))),
            created_at=state.get("nest_created_at"),
            last_nested_at=state.get("last_nested_at"),
            times_returned_to_nest=int(state.get("times_returned_to_nest", 0) or 0),
        )

    @staticmethod
    def _load_candidate(state: dict) -> dict:
        candidate = state.get("nest_candidate", {})
        return dict(candidate) if isinstance(candidate, dict) else {}

    def set_ritual_states(self, states: dict[str, dict]) -> None:
        self.ritual_states = states
        self.save_state()

    def set_repetition_state(self, state: dict[str, list[str]]) -> None:
        self.repetition_state = state
        self.save_state()

    def update_bond(self, event: str, intensity: int = 1, save: bool = True) -> BondState:
        """Apply tiny companion-style bond changes; never romantic scoring."""
        changes = {
            "session": (1, 0, 1, 0),
            "greeting": (1, 1, 1, 0),
            "kind_phrase": (2, 1, 1, 0),
            "long_absence": (0, 0, -1, 1),
            "late_overwork": (0, 0, -1, 1),
            "pet": (1, 0, 1, 0),
            "pet_spam": (-1, 0, -1, 2),
            "drag": (0, 0, 0, 1),
            "drag_spam": (-1, 0, -1, 2),
            "frustration": (0, 1, 1, 0),
            "success": (2, 2, 1, 0),
        }
        affection, trust, comfort, mischief = changes.get(event, (0, 0, 0, 0))
        multiplier = max(1, min(3, intensity))
        self.bond.affection = self._score(self.bond.affection + affection * multiplier)
        self.bond.trust = self._score(self.bond.trust + trust * multiplier)
        self.bond.comfort = self._score(self.bond.comfort + comfort * multiplier)
        self.bond.mischief = self._score(self.bond.mischief + mischief * multiplier)
        self.bond.attachment_level = self._score(
            round(
                self.bond.affection * 0.35
                + self.bond.trust * 0.3
                + self.bond.comfort * 0.25
                + self.bond.mischief * 0.1
            )
        )
        if event not in {"session", "long_absence"}:
            self.bond.last_affection_event_at = datetime.now().astimezone().isoformat(timespec="seconds")
        if save:
            self.save_state()
        return self.bond

    def register_click(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        self._recent_clicks = [clicked for clicked in self._recent_clicks if current - clicked <= 8]
        self._recent_clicks.append(current)
        self.last_interaction_time = time.monotonic()
        self.next_idle_reaction_time = self._next_idle_time()
        self.mark_seen(save=False)
        spammed = len(self._recent_clicks) >= 4
        self.update_bond("pet_spam" if spammed else "pet")
        return spammed

    def register_drag(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        self._recent_drags = [dragged for dragged in self._recent_drags if current - dragged <= 30]
        self._recent_drags.append(current)
        self.last_interaction_time = time.monotonic()
        self.next_idle_reaction_time = self._next_idle_time()
        self.mark_seen(save=False)
        spammed = len(self._recent_drags) >= 4
        self.update_bond("drag_spam" if spammed else "drag")
        return spammed

    def click_reaction(self, spammed: bool = False) -> tuple[str, str]:
        if spammed or self.mood == Mood.ANNOYED.value:
            return random.choice(["stop poking the creature.", "rude.", "i felt that."]), "angry"
        if self.nap.is_napping or self.mood == Mood.SLEEPY.value:
            return random.choice(["mm...", "eepy...", "five more pixels."]), "sleepy"
        lines = ["hm?", "eep?", "tiny poke detected.", "yes?", "i was guarding."]
        if self.bond.affection >= 65:
            lines.extend(["oh. hi.", "you found me."])
        if self.bond.mischief >= 65:
            lines.append("poke returned emotionally.")
        return random.choice(lines), "happy" if self.bond.affection >= 55 else "idle"

    def start_drag(self) -> tuple[str, str]:
        self.presence = PresenceState.BEING_DRAGGED
        return random.choice(["weee.", "abduction.", "relocating creature."]), "happy"

    def finish_drag(self, x: int, y: int, spammed: bool = False) -> tuple[str, str]:
        self.presence = PresenceState.IDLE
        self.save_window_position(x, y)
        if spammed:
            return random.choice(["again?", "this is not a carnival."]), "angry"
        became_nest = self.register_nest_placement(x, y)
        if became_nest:
            return random.choice(["oh. this is my nest now.", "claimed this corner."]), "happy"
        return random.choice(["hmm. decent corner.", "placed."]), "idle"

    def save_window_position(self, x: int, y: int) -> None:
        self.window_position = WindowPosition(int(x), int(y))
        self.save_state()

    def register_nest_placement(self, x: int, y: int) -> bool:
        """Promote a location only after repeated deliberate placements nearby."""
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        candidate_x = self._nest_candidate.get("x")
        candidate_y = self._nest_candidate.get("y")
        near_candidate = False
        try:
            near_candidate = math.hypot(int(x) - int(candidate_x), int(y) - int(candidate_y)) <= 80
        except (TypeError, ValueError):
            pass
        count = int(self._nest_candidate.get("count", 0) or 0) + 1 if near_candidate else 1
        self._nest_candidate = {"x": int(x), "y": int(y), "count": count, "first_seen_at": self._nest_candidate.get("first_seen_at", now) if near_candidate else now}
        became_nest = count >= 3
        if became_nest:
            returning = self.nest.position is not None and math.hypot(x - self.nest.position.x, y - self.nest.position.y) <= 80
            self.nest.position = WindowPosition(int(x), int(y))
            self.nest.confidence = min(1.0, max(0.65, self.nest.confidence + 0.15))
            self.nest.created_at = self.nest.created_at or now
            self.nest.last_nested_at = now
            if returning:
                self.nest.times_returned_to_nest += 1
        self.save_state()
        return became_nest

    def consider_nest_stay(
        self,
        x: int,
        y: int,
        minimum_seconds: int = 15 * 60,
        now: datetime | None = None,
    ) -> bool:
        """Promote a candidate after Fibi has remained there for a while."""
        try:
            near = math.hypot(int(x) - int(self._nest_candidate.get("x")), int(y) - int(self._nest_candidate.get("y"))) <= 40
            first_seen = self._parse_datetime(str(self._nest_candidate.get("first_seen_at", "")))
        except (TypeError, ValueError):
            return False
        current = now or datetime.now().astimezone()
        if not near or first_seen is None or (current - first_seen).total_seconds() < minimum_seconds:
            return False
        self._nest_candidate["count"] = max(3, int(self._nest_candidate.get("count", 0) or 0))
        self.nest.position = WindowPosition(int(x), int(y))
        self.nest.confidence = min(1.0, max(0.65, self.nest.confidence + 0.1))
        stamp = current.isoformat(timespec="seconds")
        self.nest.created_at = self.nest.created_at or stamp
        self.nest.last_nested_at = stamp
        self.save_state()
        return True

    def restored_position(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        window_width: int,
        window_height: int,
    ) -> tuple[WindowPosition | None, str]:
        """Restore the latest valid position, then the established nest."""
        if self._position_is_valid(self.window_position, left, top, right, bottom, window_width, window_height):
            return self.window_position, "saved_position"
        if self._position_is_valid(self.nest.position, left, top, right, bottom, window_width, window_height):
            self.nest.times_returned_to_nest += 1
            self.nest.last_nested_at = datetime.now().astimezone().isoformat(timespec="seconds")
            self.window_position = self.nest.position
            self.save_state()
            return self.nest.position, "nest"
        return None, "default"

    @staticmethod
    def _position_is_valid(position: WindowPosition | None, left: int, top: int, right: int, bottom: int, width: int, height: int) -> bool:
        if position is None:
            return False
        return left <= position.x <= right - width + 1 and top <= position.y <= bottom - height + 1

    def restored_window_position(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        window_width: int,
        window_height: int,
    ) -> WindowPosition | None:
        return self.restored_position(left, top, right, bottom, window_width, window_height)[0]

    @staticmethod
    def time_personality_curve(time_of_day: str) -> TimePersonalityCurve:
        curves = {
            "morning": TimePersonalityCurve("morning", 10, -10, 8, "curious"),
            "afternoon": TimePersonalityCurve("afternoon", 15, -15, 5, "focused"),
            "evening": TimePersonalityCurve("evening", 0, 5, 8, "happy"),
            "night": TimePersonalityCurve("night", -12, 18, 2, "sleepy"),
            "late_night": TimePersonalityCurve("late_night", -25, 35, -5, "sleepy"),
        }
        return curves.get(time_of_day, TimePersonalityCurve(time_of_day or "unknown", 0, 0, 0, "idle"))

    def should_nap(self, time_of_day: str, idle_seconds: float) -> bool:
        if self.is_busy() or self.nap.is_napping:
            return False
        effective_energy = self._score(self.nap.energy - int(max(0, idle_seconds) / 300))
        comfort_idle = 10 * 60 if self.bond.comfort >= 65 else 18 * 60
        sleepy_context = time_of_day in {"night", "late_night"} or self.mood == Mood.SLEEPY.value
        return idle_seconds >= comfort_idle and (sleepy_context or effective_energy <= 25)

    def start_nap(self) -> tuple[str, str]:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        self.nap.is_napping = True
        self.nap.nap_started_at = now
        self.nap.energy = self._score(self.nap.energy - 5)
        self.presence = PresenceState.NAPPING
        self.set_mood(Mood.SLEEPY.value)
        return random.choice(["zzz...", "eepy...", "tiny nap."]), "sleepy"

    def wake(self, reason: str = "interaction", save: bool = True) -> tuple[str, str]:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        was_napping = self.nap.is_napping
        self.nap.is_napping = False
        self.nap.nap_started_at = None
        self.nap.last_woke_at = now
        self.nap.energy = self._score(self.nap.energy + (20 if was_napping else 5))
        self.presence = PresenceState.WAKING
        self.mark_seen(save=False)
        if save:
            self.save_state()
        return random.choice(["mm?", "i was guarding with my eyes closed.", "back?", "awake-ish."]), "happy"

    def finish_waking(self) -> None:
        if self.presence == PresenceState.WAKING:
            self.presence = PresenceState.IDLE
            self.save_state()

    def mark_seen(self, save: bool = True) -> None:
        self.last_seen_at = datetime.now().astimezone().isoformat(timespec="seconds")
        if save:
            self.save_state()

    def mark_shutdown(self) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        self.last_seen_at = now
        self.last_shutdown_at = now
        self.save_state()

    def continuity_gap_hours(self) -> float | None:
        previous = self._parse_datetime(self.previous_last_seen_at)
        if previous is None:
            return None
        return max(0.0, (datetime.now().astimezone() - previous).total_seconds() / 3600)

    def _continuity_line(self, now: datetime) -> str:
        previous = self._parse_datetime(self.previous_last_seen_at)
        if previous is None:
            return "hii. new desktop."
        gap_seconds = max(0.0, (now - previous).total_seconds())
        if now.date() != previous.date():
            if now.hour < 12:
                return "morning. i guarded the desktop badly."
            if now.hour >= 22 or now.hour < 5:
                return "again at this hour?"
            return "new day. still here."
        if gap_seconds < 15 * 60:
            return "back already?"
        if gap_seconds >= 3 * 3600:
            return "you vanished."
        if now.hour >= 22 or now.hour < 5:
            return "again at this hour?"
        return "oh. you're back."

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed
        except ValueError:
            return None

    def update_mood(
        self,
        event: str,
        user_text: str = "",
        reply_text: str = "",
        time_of_day: str = "",
    ) -> str:
        self.mood = self.mood_machine.transition(event, user_text, reply_text, time_of_day)
        self.save_state()
        print(f"CURRENT MOOD: {self.mood}")
        return self.mood

    def drift_mood(
        self,
        time_of_day: str,
        idle_seconds: float,
        recent_successes: int = 0,
        recent_frustrations: int = 0,
    ) -> MoodDriftResult:
        """Let mood move slowly from local context, not random noise."""
        previous = self.mood
        new_mood = previous
        reason = "stable"
        strength = 0.0

        if self.nap.is_napping:
            new_mood, reason, strength = Mood.SLEEPY.value, "napping", 0.8
        elif recent_frustrations >= 2:
            new_mood, reason, strength = Mood.FOCUSED.value, "repeated frustration", 0.7
        elif recent_successes >= 1 and previous in {Mood.FOCUSED.value, Mood.ANNOYED.value}:
            new_mood, reason, strength = Mood.HAPPY.value, "success softened mood", 0.55
        elif idle_seconds >= 45 * 60 and time_of_day in {"evening", "night", "late_night"}:
            new_mood, reason, strength = Mood.SLEEPY.value, "long quiet evening", 0.5
        elif idle_seconds >= 20 * 60 and self.bond.comfort >= 60:
            new_mood, reason, strength = Mood.SLEEPY.value, "comfortable quiet", 0.4
        elif time_of_day == "morning" and previous == Mood.IDLE.value:
            new_mood, reason, strength = Mood.CURIOUS.value, "morning curiosity", 0.3

        if new_mood != previous:
            self.set_mood(new_mood)
        return MoodDriftResult(previous, new_mood, reason, strength)

    def set_mood(self, mood: str) -> None:
        self.mood = self.mood_machine.normalize(mood)
        self.mood_machine.current = self.mood
        self.save_state()
        print(f"CURRENT MOOD: {self.mood}")

    def set_thinking(self, thinking: bool) -> None:
        self.is_thinking = thinking
        if thinking:
            self.presence = PresenceState.THINKING
        elif not self.nap.is_napping:
            self.presence = PresenceState.IDLE

    def set_speaking(self, speaking: bool) -> None:
        self.is_speaking = speaking
        if speaking:
            self.presence = PresenceState.SPEAKING
        elif not self.nap.is_napping:
            self.presence = PresenceState.IDLE

    def set_listening(self, listening: bool) -> None:
        self.is_listening = listening
        if listening:
            self.presence = PresenceState.LISTENING
        elif not self.nap.is_napping:
            self.presence = PresenceState.IDLE

    def is_busy(self) -> bool:
        return self.is_speaking or self.is_thinking or self.is_listening

    def should_idle_react(self) -> bool:
        return not self.is_busy() and not self.nap.is_napping and time.monotonic() >= self.next_idle_reaction_time

    def idle_reaction(
        self,
        time_of_day: str = "",
        active_app: str | None = None,
        known_project: str | None = None,
        pattern_reaction: str | None = None,
        idle_seconds: float | None = None,
        now: float | None = None,
    ) -> str:
        self.next_idle_reaction_time = self._next_idle_time()
        current = now if now is not None else time.monotonic()
        category, lines = self._idle_candidates(
            time_of_day, active_app, known_project, pattern_reaction, idle_seconds
        )
        if current < self._reaction_cooldowns.get(category, 0):
            category, lines = "default", ["hm.", "blink blink.", "still here."]

        fresh = [line for line in lines if line not in self._last_idle_lines]
        line = random.choice(fresh or lines)
        self._reaction_cooldowns[category] = current + 10 * 60
        self._last_idle_lines = (self._last_idle_lines + [line])[-4:]
        return line

    def _idle_candidates(
        self,
        time_of_day: str,
        active_app: str | None,
        known_project: str | None,
        pattern_reaction: str | None,
        idle_seconds: float | None,
    ) -> tuple[str, list[str]]:
        app = (active_app or "").lower()
        if idle_seconds is not None and idle_seconds >= 15 * 60:
            return "long_idle", ["did you evaporate?", "guarding desktop."]
        if time_of_day in {"night", "late_night"}:
            return "late_night", ["eepy...", "tiny creature recommends sleep."]
        if pattern_reaction:
            return "pattern", [pattern_reaction]
        if app in {"code", "vscode", "devenv"}:
            lines = ["still building?", "compiler creature nearby."]
            if known_project:
                lines.append(f"{known_project} again?")
            return "coding", lines
        if app in {"chrome", "msedge", "firefox", "brave", "opera"}:
            return "browser", ["research hole?", "you opened one tab. then twenty."]
        if known_project:
            return "project", [f"still working on {known_project}?"]
        return "default", ["hm.", "blink blink.", "still here."]

    @staticmethod
    def _next_idle_time() -> float:
        return time.monotonic() + random.randint(45, 120)

    @staticmethod
    def random_blink_delay_ms() -> int:
        return random.randint(2800, 7200)

    def next_animation_frame(self) -> tuple[int, int, float]:
        self.float_phase += 0.035
        self.breath_phase += 0.025
        if self.is_speaking:
            self.talk_phase += 0.18
        return (
            int(math.sin(self.float_phase) * 5),
            int(math.sin(self.talk_phase) * 2) if self.is_speaking else 0,
            1.0 + math.sin(self.breath_phase) * 0.018,
        )
