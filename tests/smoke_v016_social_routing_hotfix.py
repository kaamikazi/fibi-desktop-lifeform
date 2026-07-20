"""Smoke tests for v0.16 social/greeting routing hotfix."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.local_micro_brain import LocalMicroBrain
from tests.smoke_v012_actions import make_core


BAD_FALLBACK = "Ollama is unavailable"


def assert_local_social_reply(core, model, message: str, expected_category: str) -> None:
    before = model.calls
    started = time.perf_counter()
    response = core.respond(message)
    duration_ms = (time.perf_counter() - started) * 1000
    assert duration_ms < 300, f"{message!r} was too slow: {duration_ms:.1f} ms"
    assert model.calls == before, f"{message!r} called the model"
    assert response.model_used in {"local-greeting", "local-micro-brain"}
    assert BAD_FALLBACK not in response.display_text
    assert core.route_decisions.last_decision.fast_category == expected_category
    assert not core.route_decisions.last_decision.model_router_allowed


def run() -> None:
    classifier = FastResponseClassifier()
    assert classifier.classify("heyyyy").category == "greeting"
    assert classifier.classify("hiiii").category == "greeting"
    assert classifier.classify("hellooo").category == "greeting"
    assert classifier.classify("yooo").category == "greeting"
    assert classifier.classify("suppp").category == "greeting"
    assert classifier.classify("how are you?").category == "social_checkin"
    assert classifier.classify("are you there?").category == "social_checkin"
    assert classifier.classify("what are you doing?").category == "social_checkin"
    assert classifier.classify("what is Python?").category == "complex_chat"

    micro = LocalMicroBrain()
    social = micro.reply("social_checkin", user_message="how are you?")
    assert social.handled and social.confidence == "high" and social.text
    doing = micro.reply("social_checkin", user_message="what are you doing?")
    assert doing.handled and doing.confidence == "high" and doing.text

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root, opened, launched)

        assert_local_social_reply(core, model, "heyyyy", "greeting")
        assert_local_social_reply(core, model, "hiiii", "greeting")
        assert_local_social_reply(core, model, "how are you?", "social_checkin")
        assert_local_social_reply(core, model, "are you there?", "social_checkin")
        assert_local_social_reply(core, model, "what are you doing?", "social_checkin")

        complex_reply = core.respond("what is Python?")
        assert core.route_decisions.last_decision.route_name in {"model_complex_chat", "local_fallback"}
        assert core.route_decisions.last_decision.fast_category == "complex_chat"
        assert complex_reply.display_text

    print("Fibi v0.16 social routing hotfix smoke tests passed.")


if __name__ == "__main__":
    run()


