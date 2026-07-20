"""Select small nonblocking body motions from Fibi's local state."""

from __future__ import annotations

import time

from fibi.engines.types import AttentionResult, HabitState, MotionIntent, RitualResult


MOTIONS: dict[str, MotionIntent] = {
    "idle_breathe": MotionIntent("idle_breathe", 1200, 0.25, None, "breathe", True, "quiet presence"),
    "blink": MotionIntent("blink", 140, 0.3, None, "blink", True, "natural blink"),
    "look_left": MotionIntent("look_left", 500, 0.35, None, "look", True, "small curiosity"),
    "look_right": MotionIntent("look_right", 500, 0.35, None, "look", True, "small curiosity"),
    "tiny_hop": MotionIntent("tiny_hop", 420, 0.55, "happy", "hop", False, "playful attention"),
    "happy_bounce": MotionIntent("happy_bounce", 700, 0.7, "happy", "happy", False, "happy mood"),
    "sleepy_sway": MotionIntent("sleepy_sway", 1400, 0.4, "sleepy", "sleepy", True, "sleepy mood"),
    "annoyed_shake": MotionIntent("annoyed_shake", 480, 0.65, "angry", "annoyed", False, "annoyed reaction"),
    "thinking_tilt": MotionIntent("thinking_tilt", 900, 0.4, "thinking", "thinking", True, "thinking"),
    "wake_stretch": MotionIntent("wake_stretch", 900, 0.65, "happy", "wake", False, "waking"),
    "nap_settle": MotionIntent("nap_settle", 1100, 0.45, "sleepy", "nap", False, "settling to nap"),
    "drag_squish": MotionIntent("drag_squish", 500, 0.55, None, "drag", True, "being dragged"),
    "pet_recoil": MotionIntent("pet_recoil", 350, 0.45, "happy", "pet", False, "direct pet"),
    "celebration_pop": MotionIntent("celebration_pop", 850, 0.9, "happy", "celebration", False, "success"),
}


class MotionEngine:
    """Choose a motion intent with cooldown and repetition protection."""

    COOLDOWNS = {"look": 20.0, "hop": 15.0, "happy": 8.0, "sleepy": 12.0, "annoyed": 8.0, "thinking": 4.0, "wake": 5.0, "nap": 30.0, "drag": 1.0, "pet": 2.0, "celebration": 10.0}

    def __init__(self) -> None:
        self._last_at: dict[str, float] = {}
        self._recent: list[str] = []

    def select(
        self,
        *,
        mood: str,
        presence_state: str,
        event: str = "idle",
        time_of_day: str = "",
        attention: AttentionResult | None = None,
        ritual: RitualResult | None = None,
        habit: HabitState | None = None,
        now: float | None = None,
    ) -> MotionIntent | None:
        current = time.monotonic() if now is None else now
        name = self._motion_name(mood, presence_state, event, time_of_day, ritual, habit)
        intent = MOTIONS[name]
        if attention and attention.attention_level < 20 and event == "idle":
            return None
        last = self._last_at.get(intent.cooldown_key)
        if last is not None and current - last < self.COOLDOWNS.get(intent.cooldown_key, 2.0):
            return None
        if self._recent[-2:].count(name) >= 2 and event == "idle":
            return None
        self._last_at[intent.cooldown_key] = current
        self._recent = (self._recent + [name])[-6:]
        return intent

    @staticmethod
    def _motion_name(mood: str, presence: str, event: str, time_of_day: str, ritual, habit) -> str:
        event_map = {"click": "pet_recoil", "drag_start": "drag_squish", "success": "celebration_pop", "celebration": "celebration_pop", "wake": "wake_stretch", "nap": "nap_settle", "frustration": "annoyed_shake"}
        if event in event_map:
            return event_map[event]
        if presence == "being_dragged":
            return "drag_squish"
        if presence == "thinking":
            return "thinking_tilt"
        if mood == "annoyed":
            return "annoyed_shake"
        if mood in {"happy", "excited"}:
            return "happy_bounce"
        if mood == "sleepy" or time_of_day == "late_night":
            return "sleepy_sway"
        if ritual and ritual.triggered:
            return "tiny_hop"
        if habit and "cursor" in habit.name:
            return "look_left"
        return "idle_breathe"
