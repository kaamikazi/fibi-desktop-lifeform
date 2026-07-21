"""Retrieval strategies for local Fibi RAG."""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass

from fibi.rag.types import RAGSearchResult


class QueryRewriter:
    """Small local query expansion strategy.

    This is not an LLM rewrite. It adds deterministic synonyms useful for
    personal-memory retrieval while preserving privacy and offline behavior.
    """

    SYNONYMS = {
        "remember": ["memory", "mentioned"],
        "project": ["build", "building"],
        "privacy": ["local", "cloud", "safe"],
        "fibi": ["desktop", "lifeform", "assistant"],
        "sleepy": ["eepy", "tired"],
        "study": ["studies", "education"],
        "studies": ["study", "education"],
        "sister": ["family", "relationship"],
        "brother": ["family", "relationship"],
    }

    def rewrite(self, query: str) -> str:
        cleaned = " ".join(query.strip().split())
        words = set(re.findall(r"[a-zA-Z0-9_]{2,}", cleaned.lower()))
        additions: list[str] = []
        for word in sorted(words):
            additions.extend(self.SYNONYMS.get(word, []))
        return " ".join([cleaned, *additions]).strip()


@dataclass(slots=True)
class CacheEntry:
    created_at: float
    results: list[RAGSearchResult]


class RetrievalCache:
    """Tiny TTL LRU cache for repeated desktop memory queries."""

    def __init__(self, max_entries: int = 128, ttl_seconds: int = 120) -> None:
        self.max_entries = max(1, int(max_entries))
        self.ttl_seconds = max(1, int(ttl_seconds))
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()

    @property
    def size(self) -> int:
        self._purge_expired()
        return len(self._entries)

    def get(self, key: str) -> list[RAGSearchResult] | None:
        self._purge_expired()
        entry = self._entries.get(key)
        if entry is None:
            return None
        self._entries.move_to_end(key)
        return [self._copy_result(result) for result in entry.results]

    def set(self, key: str, results: list[RAGSearchResult]) -> None:
        self._entries[key] = CacheEntry(time.monotonic(), [self._copy_result(result) for result in results])
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, entry in self._entries.items() if now - entry.created_at > self.ttl_seconds]
        for key in expired:
            self._entries.pop(key, None)

    @staticmethod
    def _copy_result(result: RAGSearchResult) -> RAGSearchResult:
        return RAGSearchResult(result.memory, result.similarity, result.score, result.rank)
