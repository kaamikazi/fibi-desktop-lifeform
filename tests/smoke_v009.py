"""Direct smoke tests for Fibi v0.09 social safety."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.boundary_engine import BoundaryEngine
from fibi.engines.core import FibiCore
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.relationship_engine import RelationshipEngine
from fibi.engines.social_context_engine import SocialContextEngine
from fibi.engines.types import BoundaryState, ModelResult, Observation, QuietModeState, ReactionCandidate, RelationshipState


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "late_night", "Code", "focused", None)


class CountingModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("tabs are breeding [happy]", "counting", 0.01, None)


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        state_path = root / "fibi_state.json"
        db_path = root / "fibi_memory.db"
        state_path.write_text(json.dumps({"v008_field": "keep"}), encoding="utf-8")

        relationship = RelationshipEngine(state_path)
        boundary = BoundaryEngine(state_path)
        social = SocialContextEngine()

        assert json.loads(state_path.read_text(encoding="utf-8"))["v008_field"] == "keep"
        assert relationship.state.interaction_style == "shy"
        assert boundary.detect("not now, busy").level == "soft"
        hard = boundary.detect("leave me alone")
        assert hard and hard.level == "hard" and hard.quiet_minutes >= 60

        boundary.apply_boundary(hard)
        assert boundary.quiet.active
        assert boundary.boundary.active
        boundary.quiet.expires_at = (datetime.now().astimezone() - timedelta(seconds=1)).isoformat()
        boundary.boundary.expires_at = boundary.quiet.expires_at
        boundary.save()
        boundary.refresh()
        assert not boundary.quiet.active

        relationship.state.user_prefers_playful = True
        relationship.state.familiarity_level = 55
        relationship.state.user_annoyance_level = 5
        relationship.state.teasing_allowed = True
        allowed = social.filter_reaction(
            ReactionCandidate("one more commit, huh.", social_tone="teasing"),
            relationship.state,
            BoundaryState(False),
            QuietModeState(False),
            direct=True,
        )
        assert allowed.action == "allow"

        relationship.state.user_annoyance_level = 80
        blocked = social.filter_reaction(
            ReactionCandidate("one more commit, huh.", social_tone="teasing"),
            relationship.state,
            BoundaryState(False),
            QuietModeState(False),
            direct=True,
        )
        assert blocked.action == "replace"

        quiet_decision = social.filter_reaction(
            ReactionCandidate("guarding desktop.", blocked_when_quiet=True),
            relationship.state,
            BoundaryState(False),
            QuietModeState(True, reason="manual"),
            direct=False,
            event="idle",
        )
        assert quiet_decision.action == "silence"

        first_apology = relationship.apology_line(True)
        second_apology = relationship.apology_line(True)
        assert first_apology in {"sorry.", "okay."}
        assert second_apology == "okay."

        updates = relationship.learn_social_preferences("don't tease me, less voice")
        assert any(update.key == "teasing_allowed" for update in updates)
        assert not relationship.state.teasing_allowed

        model = CountingModel()
        memory = MemoryEngine(db_path)
        journal = JournalEngine(db_path)
        core = FibiCore(
            life=LifeEngine(state_path),
            memory=memory,
            observation=FakeObservation(),
            journal=journal,
            patterns=PatternEngine(memory, journal),
            model=model,
            relationship=relationship,
            boundary=boundary,
            social=social,
        )

        response = core.respond("/quiet 30m")
        assert response.model_used == "local-command"
        assert "silent" in response.display_text or "quiet" in response.display_text
        assert model.calls == 0

        status = core.respond("/status")
        assert "quiet mode" in status.display_text
        assert model.calls == 0

        relation = core.respond("/relationship")
        assert "tiny roommates" in relation.display_text
        assert model.calls == 0

        reset_blocked = core.respond("/relationship reset")
        assert "confirm" in reset_blocked.display_text
        reset = core.respond("/relationship reset confirm")
        assert "reset" in reset.display_text

        boundary_response = core.respond("shut up")
        assert boundary_response.model_used == "local-command"
        assert boundary_response.display_text in {"sorry.", "okay.", "quiet mode."}
        assert model.calls == 0

        # Direct messages are still acknowledged in quiet mode, but idle bubbles are not.
        direct = core.respond("hey")
        assert direct.display_text
        line, _ = core.contextual_idle_reaction()
        assert line == ""

    print("Fibi v0.09 smoke tests passed.")


if __name__ == "__main__":
    run()


