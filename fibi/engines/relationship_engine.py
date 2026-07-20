"""Local relationship stance for Fibi.

This is social pacing, not romance. Fibi becomes warmer slowly, respects
boundaries quickly, and never guilt-trips the user for wanting space.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import BondState, BoundarySignal, RelationshipState, SocialPreferenceUpdate

STYLES = {
    "shy",
    "sleepy_friend",
    "playful_roommate",
    "quiet_companion",
    "chaotic_gremlin",
    "focused_guardian",
}


class RelationshipEngine:
    """Manage Fibi's local social distance and warmth."""

    KEY = "relationship_state"

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()
        self.save()

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _load(self) -> RelationshipState:
        raw = self._read_state().get(self.KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(RelationshipState())
        defaults.update({key: raw[key] for key in defaults if key in raw})
        defaults["interaction_style"] = defaults["interaction_style"] if defaults["interaction_style"] in STYLES else "shy"
        return RelationshipState(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.state)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def export(self) -> dict:
        return asdict(self.state)

    def reset(self, confirm: bool = False) -> str:
        if not confirm:
            return "relationship reset needs confirm."
        self.state = RelationshipState()
        self.save()
        return "tiny roommate settings reset."

    def update_from_bond(self, bond: BondState) -> RelationshipState:
        """Warmth follows trust slowly; it never jumps to clingy attachment."""
        target_familiarity = round(bond.trust * 0.35 + bond.affection * 0.25 + bond.comfort * 0.2)
        self.state.familiarity_level = self._approach(self.state.familiarity_level, target_familiarity, 2)
        if self.state.user_annoyance_level <= 25:
            self.state.social_warmth = self._approach(self.state.social_warmth, min(80, target_familiarity + 10), 2)
        self._choose_style(bond)
        self._refresh_teasing()
        self.save()
        return self.state

    def apply_boundary(self, signal: BoundarySignal) -> str:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        self.state.last_boundary_signal_at = now
        self.state.user_annoyance_level = min(100, self.state.user_annoyance_level + (30 if signal.level == "hard" else 15))
        self.state.social_distance = min(100, self.state.social_distance + (25 if signal.level == "hard" else 12))
        self.state.social_warmth = max(0, self.state.social_warmth - (10 if signal.level == "hard" else 4))
        self.state.teasing_allowed = False
        self.state.user_prefers_quiet = True
        self._choose_style()
        self.save()
        return self.apology_line(signal.should_apologize)

    def learn_social_preferences(self, user_message: str) -> list[SocialPreferenceUpdate]:
        text = user_message.lower()
        updates: list[SocialPreferenceUpdate] = []
        if any(phrase in text for phrase in ("be quiet", "talk less", "less noise")):
            self.state.user_prefers_quiet = True
            self.state.comfort_with_silence = min(100, self.state.comfort_with_silence + 15)
            updates.append(SocialPreferenceUpdate("user_prefers_quiet", True, 0.8, "explicit quiet request"))
        if any(phrase in text for phrase in ("talk more", "say more")):
            self.state.user_prefers_quiet = False
            self.state.comfort_with_silence = max(20, self.state.comfort_with_silence - 10)
            updates.append(SocialPreferenceUpdate("user_prefers_quiet", False, 0.75, "explicit talk request"))
        if any(phrase in text for phrase in ("don't tease me", "dont tease me", "no teasing")):
            self.state.teasing_allowed = False
            updates.append(SocialPreferenceUpdate("teasing_allowed", False, 0.9, "explicit no teasing"))
        if any(phrase in text for phrase in ("that was funny", "you're funny", "you are funny")):
            self.state.user_prefers_playful = True
            self.state.user_annoyance_level = max(0, self.state.user_annoyance_level - 8)
            updates.append(SocialPreferenceUpdate("user_prefers_playful", True, 0.7, "explicit playful response"))
        if any(phrase in text for phrase in ("you're annoying", "you are annoying", "that was annoying")):
            self.state.user_annoyance_level = min(100, self.state.user_annoyance_level + 25)
            self.state.teasing_allowed = False
            updates.append(SocialPreferenceUpdate("user_annoyance_level", self.state.user_annoyance_level, 0.85, "explicit annoyance"))
        if any(phrase in text for phrase in ("stay with me", "hang out")):
            self.state.social_warmth = min(80, self.state.social_warmth + 5)
            updates.append(SocialPreferenceUpdate("social_warmth", self.state.social_warmth, 0.55, "explicit companionship"))
        if updates:
            self._refresh_teasing()
            self._choose_style()
            self.save()
        return updates

    def cool_down_annoyance(self, kind: bool = False) -> None:
        amount = 4 if kind else 1
        self.state.user_annoyance_level = max(0, self.state.user_annoyance_level - amount)
        self.state.social_distance = max(0, self.state.social_distance - 1)
        self._refresh_teasing()
        self._choose_style()
        self.save()

    def apology_line(self, should_apologize: bool = True) -> str:
        if not should_apologize:
            return "quiet mode."
        now = datetime.now().astimezone()
        last = self._parse(self.state.last_apology_at)
        if last and (now - last).total_seconds() < 20 * 60:
            return "okay."
        self.state.last_apology_at = now.isoformat(timespec="seconds")
        self.save()
        return "sorry."

    @staticmethod
    def _approach(current: int, target: int, step: int) -> int:
        if current < target:
            return min(target, current + step)
        if current > target:
            return max(target, current - step)
        return current

    def _refresh_teasing(self) -> None:
        self.state.teasing_allowed = (
            self.state.user_prefers_playful
            and self.state.familiarity_level >= 35
            and self.state.user_annoyance_level <= 20
            and not self.state.user_prefers_quiet
        )

    def _choose_style(self, bond: BondState | None = None) -> None:
        if self.state.user_prefers_quiet or self.state.user_annoyance_level >= 35:
            self.state.interaction_style = "quiet_companion"
        elif self.state.teasing_allowed and self.state.social_warmth >= 50:
            self.state.interaction_style = "playful_roommate"
        elif bond and bond.mischief >= 70 and self.state.teasing_allowed:
            self.state.interaction_style = "chaotic_gremlin"
        elif self.state.familiarity_level >= 30:
            self.state.interaction_style = "sleepy_friend"
        else:
            self.state.interaction_style = "shy"

    @staticmethod
    def _parse(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
