"""Explicit one-call manual Gemini provider test.

This tool never includes Fibi memory, conversation history, project context, or
browser data. It may consume API quota and therefore refuses to run unless the
user supplies the confirmation flag.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.providers.gemini_provider import GeminiProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one neutral Gemini API test.")
    parser.add_argument("--confirm-api-call", action="store_true")
    args = parser.parse_args()
    if not args.confirm_api_call:
        print("REFUSED: pass --confirm-api-call to make one quota-consuming request.")
        return 2
    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("GEMINI_PROVIDER_BLOCKED: GEMINI_API_KEY is not configured locally.")
        return 1

    print("Making one neutral Gemini provider request. API quota may be consumed.")
    result = GeminiProvider().test_connection()
    if result.error:
        print(f"GEMINI_PROVIDER_FAILED: {result.error}")
        return 1
    print(f"GEMINI_PROVIDER_OK model={result.model} latency_ms={result.duration_ms:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
