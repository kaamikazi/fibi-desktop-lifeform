"""Hotfix smoke tests for direct-message routing vs idle thought bubbles."""

from __future__ import annotations

import random
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.inner_life_engine import InnerLifeEngine
from fibi.engines.local_micro_brain import LocalMicroBrain

from tests.smoke_v010 import CountingModel, make_core


def assert_not_tiny_thought(text: str) -> None:
    assert text.strip().lower() not in {"tiny thought", "tiny thought."}


def run() -> None:
    classifier = FastResponseClassifier()
    assert classifier.classify("hi").category == "greeting"
    assert classifier.classify("how are you?").category == "complex_chat"
    assert classifier.classify("What is Python?").category == "complex_chat"
    assert classifier.classify("explain this code").category == "complex_chat"
    assert classifier.classify("how do I fix this error?").category == "complex_chat"
    assert classifier.classify("this unknown sentence has more than four words").category == "complex_chat"
    assert classifier.classify("what do you remember about me?").category == "complex_chat"
    assert classifier.classify("it worked").category == "simple_chat"
    assert classifier.classify("this is broken").category == "simple_chat"

    micro = LocalMicroBrain()
    for _ in range(20):
        simple_probe = micro.reply("simple_chat")
        unknown_probe = micro.reply("unknown")
        assert simple_probe.text is None
        assert simple_probe.confidence == "low"
        assert simple_probe.handled is False
        assert unknown_probe.text is None
        assert unknown_probe.confidence == "low"
        assert unknown_probe.handled is False

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        model = CountingModel("python is a friendly code snake. [thinking]")
        core = make_core(root, model)

        start = time.perf_counter()
        greeting = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert_not_tiny_thought(greeting.display_text)
        assert greeting.model_used == "local-greeting"
        assert model.calls == 0

        simple = core.respond("how are you?")
        assert_not_tiny_thought(simple.display_text)
        assert simple.model_used == "counting-model"
        assert model.calls == 1

        calls_before_complex = model.calls
        complex_reply = core.respond("What is Python?")
        assert_not_tiny_thought(complex_reply.display_text)
        assert complex_reply.model_used == "counting-model"
        assert model.calls == calls_before_complex + 1

        explain_reply = core.respond("explain this code")
        assert_not_tiny_thought(explain_reply.display_text)
        assert explain_reply.model_used == "counting-model"

        fix_reply = core.respond("how do I fix this error?")
        assert_not_tiny_thought(fix_reply.display_text)
        assert fix_reply.model_used == "counting-model"

        slash = core.respond("/status")
        assert_not_tiny_thought(slash.display_text)
        assert slash.model_used == "local-command"

        blocked_line, _ = core.contextual_idle_reaction(event_source="user_message", user_text="hi")
        assert blocked_line == ""

        unavailable = CountingModel("", error="offline")
        unavailable_core = make_core(root / "offline", unavailable)
        fallback = unavailable_core.respond("What is a desktop assistant?")
        assert fallback.display_text
        assert_not_tiny_thought(fallback.display_text)
        assert fallback.model_used == "local-fallback"
        assert fallback.used_fallback is True

        inner = InnerLifeEngine(root / "inner.db")
        original_random = random.random
        original_choice = random.choice
        try:
            random.random = lambda: 0.0
            random.choice = lambda values: "tiny thought." if "tiny thought." in values else values[0]
            candidate = inner.thought_bubble_candidate(100, focused=False, busy=False, mood="idle")
            assert candidate is not None
            assert candidate.text == "tiny thought."
            assert inner.thought_bubble_candidate(
                100,
                focused=False,
                busy=False,
                mood="idle",
                event_source="user_message",
                user_text="hi",
            ) is None
        finally:
            random.random = original_random
            random.choice = original_choice

    print("Fibi v0.10 hotfix smoke tests passed.")


if __name__ == "__main__":
    run()


