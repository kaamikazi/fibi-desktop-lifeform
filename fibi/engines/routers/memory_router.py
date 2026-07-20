"""Primary memory router backed by the RAG memory service."""

from __future__ import annotations

from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from fibi.rag.types import ConversationContext, RAGMemory, RAGSearchResult


class MemoryRouter:
    """Route new memory reads/writes through RAG."""

    def __init__(self, rag_memory: RAGMemoryServiceFacade | None = None) -> None:
        self.rag_memory = rag_memory or RAGMemoryServiceFacade()

    def retrieve_relevant(self, query: str, top_k: int = 5) -> list[RAGSearchResult]:
        return self.rag_memory.retrieve_relevant(query, top_k=top_k)

    def summarize_memory_context(self, query: str) -> str:
        return self.rag_memory.summarize_memory_context(query)

    def remember_fact(self, content: str, **kwargs) -> RAGMemory:
        return self.rag_memory.remember_fact(content, **kwargs)

    def conversation_context(self, query: str, top_k: int = 5) -> ConversationContext:
        return self.rag_memory.service.retrieve_conversation_context(query, top_k=top_k)
