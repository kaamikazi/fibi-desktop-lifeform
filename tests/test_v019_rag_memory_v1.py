"""Pytest wrapper for the v1 RAG memory smoke test."""

from __future__ import annotations

from tests.smoke_v019_rag_memory_v1 import run


def test_v019_rag_memory_v1() -> None:
    run()


