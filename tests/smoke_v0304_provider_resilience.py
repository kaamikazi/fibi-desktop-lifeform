"""Mock-only smoke checks for Fibi v0.30.4 provider resilience."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.model_router import ModelRouter
from tests.test_v0304_provider_resilience import (
    FakeHTTPError,
    HealthAwareOllama,
    SequenceModelsAPI,
    provider_with,
    route,
)


def main() -> None:
    api = SequenceModelsAPI([FakeHTTPError(503, "temporary"), "recovered"])
    router = ModelRouter(
        ollama=HealthAwareOllama(healthy=False),
        gemini=provider_with(api),
    )
    result = route(router)
    assert result.provider_used == "gemini"
    assert result.retry_count == 1
    assert api.generate_calls == 2

    failed_api = SequenceModelsAPI([
        FakeHTTPError(503, "temporary"),
        FakeHTTPError(503, "temporary"),
    ])
    failed_router = ModelRouter(
        ollama=HealthAwareOllama(healthy=False),
        gemini=provider_with(failed_api),
    )
    failed = route(failed_router)
    assert failed.provider_used == "fallback"
    assert "temporarily unavailable" in failed.reply_text
    assert failed_router.gemini.status().health_state == "degraded"
    assert failed_router.last_fallback_status == "unavailable"
    print("Fibi v0.30.4 provider resilience smoke tests passed.")


if __name__ == "__main__":
    main()
