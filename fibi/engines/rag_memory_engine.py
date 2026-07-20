"""Fibi engine wrapper around the local RAG memory service."""

from __future__ import annotations

from pathlib import Path

from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService
from fibi.rag.types import ConversationContext, RAGMemory, RAGSearchResult


class RAGMemoryEngine:
    """Small integration facade for other Fibi engines."""

    def __init__(self, database_path: Path | None = None, vector_dir: Path | None = None) -> None:
        config = RAGConfig()
        if database_path is not None:
            config.database_path = Path(database_path)
        if vector_dir is not None:
            config.vector_dir = Path(vector_dir)
        self.service = RAGMemoryService(config)

    def add(self, content: str, category: str = "fact", **kwargs) -> RAGMemory:
        return self.service.add_memory(content, category=category, **kwargs)

    def update(self, memory_id: int, **kwargs) -> RAGMemory | None:
        return self.service.update_memory(memory_id, **kwargs)

    def delete(self, memory_id: int) -> bool:
        return self.service.delete_memory(memory_id)

    def search(self, query: str, top_k: int = 6) -> list[RAGSearchResult]:
        return self.service.search_memories(query, top_k=top_k)

    def context_for(self, user_message: str, top_k: int = 6) -> ConversationContext:
        return self.service.retrieve_conversation_context(user_message, top_k=top_k)
