"""Compatibility adapter from legacy MemoryEngine calls to RAG memory."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fibi.engines.types import Memory, MemoryCategory
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from fibi.rag.types import RAGMemory

LOGGER = logging.getLogger(__name__)


class LegacyMemoryAdapter:
    """Expose old MemoryEngine-style methods while writing through RAG."""

    def __init__(self, rag_memory: RAGMemoryServiceFacade | None = None, database_path: Path | None = None) -> None:
        self.rag_memory = rag_memory or RAGMemoryServiceFacade(database_path=database_path)
        self.database_path = self.rag_memory.service.config.database_path

    def save(
        self,
        category: MemoryCategory | str,
        content: str,
        importance: float = 0.5,
        source: str = "conversation",
        metadata: dict | None = None,
    ) -> int | None:
        LOGGER.warning("legacy_memory_adapter.save is deprecated; routing to RAG")
        memory = self.rag_memory.service.add_memory(
            content,
            category=MemoryCategory(category).value,
            importance=importance,
            confidence=importance,
            source=source,
            metadata=metadata or {},
            provenance={"compatibility_adapter": "LegacyMemoryAdapter"},
        )
        return memory.id

    def retrieve(
        self,
        query: str = "",
        categories: list[MemoryCategory | str] | None = None,
        limit: int = 6,
    ) -> list[Memory]:
        LOGGER.warning("legacy_memory_adapter.retrieve is deprecated; routing to RAG")
        filters = {"category": MemoryCategory(categories[0]).value} if categories else None
        results = self.rag_memory.retrieve_relevant(query or "memory", filters=filters, top_k=limit)
        return [self._to_legacy(result.memory) for result in results]

    def summarize(self, memories: list[Memory], max_characters: int = 700) -> str:
        lines: list[str] = []
        used = 0
        for memory in memories:
            line = f"- {memory.category.value}: {memory.content}"
            if used + len(line) > max_characters:
                break
            lines.append(line)
            used += len(line)
        return "\n".join(lines)

    def save_conversation(self, role: str, content: str, mood: str | None = None) -> None:
        if role not in {"user", "fibi"} or not content.strip():
            return
        self.rag_memory.service.add_memory(
            content,
            category="conversation",
            source=f"conversation:{role}",
            metadata={"role": role, "mood": mood or ""},
            provenance={"compatibility_adapter": "save_conversation"},
        )

    def learn_from_message(self, user_message: str) -> list[int]:
        patterns = [
            (MemoryCategory.FACT, r"\bmy name is\s+([^.!?]+)", 0.9),
            (MemoryCategory.PROJECT, r"\b(?:working on|building)\s+([^.!?]+)", 0.8),
            (MemoryCategory.GOAL, r"\b(?:i want to|my goal is)\s+([^.!?]+)", 0.8),
            (MemoryCategory.HABIT, r"\bi (?:usually|often|always)\s+([^.!?]+)", 0.7),
            (MemoryCategory.BELIEF, r"\bi believe\s+([^.!?]+)", 0.8),
        ]
        saved_ids: list[int] = []
        for category, pattern, importance in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if not match:
                continue
            memory_id = self.save(category, match.group(0).strip(), importance)
            if memory_id is not None:
                saved_ids.append(memory_id)
        return saved_ids

    @staticmethod
    def _to_legacy(memory: RAGMemory) -> Memory:
        category = memory.category if memory.category in {item.value for item in MemoryCategory} else MemoryCategory.EVENT.value
        return Memory(
            id=memory.id,
            category=MemoryCategory(category),
            content=memory.content,
            importance=memory.importance,
            source=memory.source,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            last_accessed_at=memory.last_accessed_at,
            access_count=memory.access_count,
            confidence=memory.confidence,
            emotional_weight=float(memory.metadata.get("emotional_weight", memory.importance)),
            metadata=memory.metadata,
        )
