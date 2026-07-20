"""Pytest wrapper for v0.17 RAG smoke tests."""

from tests.smoke_v017_rag_memory import run


def test_v017_rag_memory() -> None:
    run()


