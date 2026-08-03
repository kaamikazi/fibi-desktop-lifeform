"""Fast synthetic smoke check for the Stage 1 memory read boundary."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.memory.context_preview import ContextBrokerPreview
from fibi.memory.query_models import MemoryReadSource
from fibi.memory.shadow_comparison import MemoryShadowSettings


def main() -> None:
    assert {source.value for source in MemoryReadSource} == {"legacy", "rag"}
    assert MemoryShadowSettings().enabled is False
    assert ContextBrokerPreview(SecretSanitizer()).enabled is False
    print("Memory Stage 1 read boundary smoke tests passed.")


if __name__ == "__main__":
    main()
