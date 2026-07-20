"""Pytest wrapper for the v0.21 next-gen RAG smoke test."""

from __future__ import annotations

from tests.smoke_v021_rag_nextgen import run


def test_v021_rag_nextgen_smoke() -> None:
    run()


