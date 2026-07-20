"""Primary Fibi memory interface backed by local RAG."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService
from fibi.rag.types import ConversationContext, RAGHealth, RAGMemory, RAGSearchResult

LOGGER = logging.getLogger(__name__)


class RAGMemoryServiceFacade:
    """Beginner-friendly primary memory API for Fibi engines."""

    def __init__(self, database_path: Path | None = None, vector_dir: Path | None = None) -> None:
        config = RAGConfig()
        if database_path is not None:
            config.database_path = Path(database_path)
        if vector_dir is not None:
            config.vector_dir = Path(vector_dir)
        self.service = RAGMemoryService(config)

    def remember_fact(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("fact", content, **kwargs)

    def remember_event(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("event", content, **kwargs)

    def remember_project(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("project", content, **kwargs)

    def remember_habit(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("habit", content, **kwargs)

    def remember_belief(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("belief", content, **kwargs)

    def remember_goal(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("goal", content, **kwargs)

    def remember_important_moment(self, content: str, **kwargs: Any) -> RAGMemory:
        return self._remember("important_moment", content, **kwargs)

    def retrieve_relevant(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[RAGSearchResult]:
        categories = None
        if filters and filters.get("category"):
            categories = [str(filters["category"])]
        return self.service.search_memories(query, top_k=top_k, categories=categories)

    def search_memories(self, query: str, category: str | None = None) -> list[RAGSearchResult]:
        filters = {"category": category} if category else None
        return self.retrieve_relevant(query, filters=filters)

    def summarize_memory_context(self, query: str) -> str:
        return self.service.retrieve_conversation_context(query).context_text

    def update_memory(self, memory_id: int, **kwargs: Any) -> RAGMemory | None:
        return self.service.update_memory(memory_id, **kwargs)

    def delete_memory(self, memory_id: int) -> bool:
        return self.service.delete_memory(memory_id)

    def expire_old_memories(self) -> int:
        return self.service.expire_memories()

    def health_check(self) -> RAGHealth:
        return self.service.health()

    def conversation_context(self, query: str, top_k: int = 5) -> ConversationContext:
        return self.service.retrieve_conversation_context(query, top_k=top_k)

    def _remember(self, category: str, content: str, **kwargs: Any) -> RAGMemory:
        LOGGER.info("rag_memory.remember", extra={"category": category, "source": kwargs.get("source", "conversation")})
        return self.service.add_memory(content, category=category, **kwargs)
