"""Hotfix smoke tests for local date/time routing."""

from __future__ import annotations

import sys
import tempfile
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.fast_response_classifier import FastResponseClassifier
from tests.smoke_v012_actions import make_core


def run() -> None:
    detector = ActionIntentDetector()
    classifier = FastResponseClassifier()

    for text in (
        "what's the date",
        "whatâ€™s the date",
        "what is the date",
        "today's date",
        "date today",
        "current date",
        "what day is it",
        "can you tell me the date?",
    ):
        intent = detector.detect(text)
        assert intent is not None
        assert intent.action_type == "tell_date"
        category = classifier.classify(text)
        assert category.category == "local_utility"
        assert category.should_use_model is False

    for text in ("what time is it", "current time", "time now", "what's the time", "tell me the time?"):
        intent = detector.detect(text)
        assert intent is not None
        assert intent.action_type == "tell_time"
        category = classifier.classify(text)
        assert category.category == "local_utility"
        assert category.should_use_model is False

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root, opened, launched)

        for text in ("what's the date", "whatâ€™s the date", "what is the date", "today's date", "can you tell me the date?"):
            output = StringIO()
            start = time.perf_counter()
            with redirect_stdout(output):
                response = core.respond(text)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logs = output.getvalue()
            assert response.model_used == "local-action"
            assert "today is" in response.display_text.lower()
            assert elapsed_ms < 300
            assert model.calls == 0
            assert "ACTION_INTENT_CHECKED: true" in logs
            assert "ACTION_INTENT_DETECTED: true" in logs
            assert "ACTION_TYPE: tell_date" in logs
            assert "ACTION_ROUTE_USED: true" in logs
            assert "MODEL_ROUTER_USED: false" in logs

        output = StringIO()
        start = time.perf_counter()
        with redirect_stdout(output):
            time_response = core.respond("what time is it")
        elapsed_ms = (time.perf_counter() - start) * 1000
        logs = output.getvalue()
        assert time_response.model_used == "local-action"
        assert "it is" in time_response.display_text.lower()
        assert elapsed_ms < 300
        assert model.calls == 0
        assert "ACTION_INTENT_CHECKED: true" in logs
        assert "ACTION_INTENT_DETECTED: true" in logs
        assert "ACTION_TYPE: tell_time" in logs
        assert "ACTION_ROUTE_USED: true" in logs
        assert "MODEL_ROUTER_USED: false" in logs
        assert opened == []
        assert launched == []
        assert core.privacy.settings.allow_cloud_model is False

        output = StringIO()
        with redirect_stdout(output):
            complex_response = core.respond("what is Python?")
        logs = output.getvalue()
        assert model.calls > 0
        assert complex_response.model_used != "local-action"
        assert "ACTION_INTENT_DETECTED: false" in logs
        assert "MODEL_ROUTER_USED: true" in logs

    print("Fibi v0.12 date/time routing hotfix smoke tests passed.")


if __name__ == "__main__":
    run()


