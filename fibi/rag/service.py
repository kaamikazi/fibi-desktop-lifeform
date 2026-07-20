"""Production-facing RAG memory service."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

import numpy as np

from fibi.rag.config import RAGConfig
from fibi.rag.embedding import EmbeddingProvider, build_embedding_provider
from fibi.rag.repository import RAGMemoryRepository
from fibi.rag.retrieval import QueryRewriter, RetrievalCache
from fibi.rag.types import ConversationContext, DuplicateCheck, RAGHealth, RAGMemory, RAGSearchResult
from fibi.rag.vector_store import FAISSVectorStore

LOGGER = logging.getLogger(__name__)


class RAGMemoryService:
    """High-level API for local long-term vector memory."""

    def __init__(
        self,
        config: RAGConfig | None = None,
        repository: RAGMemoryRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: FAISSVectorStore | None = None,
        query_rewriter: QueryRewriter | None = None,
        retrieval_cache: RetrievalCache | None = None,
    ) -> None:
        self.config = config or RAGConfig()
        self.repository = repository or RAGMemoryRepository(self.config.database_path)
        self.embedding_provider = embedding_provider or build_embedding_provider(
            self.config.embedding_backend,
            self.config.embedding_dimension,
            self.config.sentence_transformer_model,
        )
        self.vector_store = vector_store or FAISSVectorStore(
            self.config.index_path,
            self.config.id_map_path,
            self.embedding_provider.dimension,
            self.config.manifest_path,
        )
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.retrieval_cache = retrieval_cache or RetrievalCache(
            self.config.retrieval_cache_size,
            self.config.retrieval_cache_ttl_seconds,
        )
        if self.vector_store.vector_count != self.repository.count_active():
            self.rebuild_index()

    def add_memory(
        self,
        content: str,
        *,
        category: str = "fact",
        source: str = "conversation",
        source_id: str = "",
        source_uri: str = "",
        source_title: str = "",
        source_timestamp: str = "",
        importance: float = 0.5,
        confidence: float = 0.5,
        metadata: dict | None = None,
        provenance: dict | None = None,
        expires_at: str = "",
        allow_duplicate: bool = False,
    ) -> RAGMemory:
        duplicate = self.detect_duplicate(content)
        if duplicate.is_duplicate and not allow_duplicate and duplicate.existing_id is not None:
            LOGGER.info("RAG duplicate detected: existing=%s similarity=%.3f", duplicate.existing_id, duplicate.similarity)
            existing = self.repository.get(duplicate.existing_id)
            if existing is None:
                raise RuntimeError("duplicate memory disappeared during add")
            return existing
        memory = RAGMemory(
            id=None,
            category=category,
            content=content,
            source=source,
            source_id=source_id,
            source_uri=source_uri,
            source_title=source_title,
            source_timestamp=source_timestamp,
            importance=importance,
            confidence=confidence,
            metadata=metadata or {},
            provenance=provenance or {},
            expires_at=expires_at,
        )
        memory_id = self.repository.add(memory)
        created = self.repository.get(memory_id)
        if created is None:
            raise RuntimeError("failed to reload added memory")
        self.vector_store.add([memory_id], self.embedding_provider.embed([created.content]))
        self.retrieval_cache.clear()
        return created

    def update_memory(
        self,
        memory_id: int,
        *,
        content: str | None = None,
        category: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        metadata: dict | None = None,
        source: str | None = None,
        source_id: str | None = None,
        source_uri: str | None = None,
        source_title: str | None = None,
        source_timestamp: str | None = None,
        provenance: dict | None = None,
        expires_at: str | None = None,
    ) -> RAGMemory | None:
        updated = self.repository.update(
            memory_id,
            content=content,
            category=category,
            importance=importance,
            confidence=confidence,
            metadata=metadata,
            source=source,
            source_id=source_id,
            source_uri=source_uri,
            source_title=source_title,
            source_timestamp=source_timestamp,
            provenance=provenance,
            expires_at=expires_at,
        )
        if updated is not None:
            self.rebuild_index()
            self.retrieval_cache.clear()
        return updated

    def delete_memory(self, memory_id: int) -> bool:
        deleted = self.repository.soft_delete(memory_id)
        if deleted:
            self.rebuild_index()
            self.retrieval_cache.clear()
        return deleted

    def search_memories(
        self,
        query: str,
        *,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        categories: list[str] | None = None,
    ) -> list[RAGSearchResult]:
        cleaned = query.strip()
        if not cleaned:
            return []
        limit = top_k or self.config.default_top_k
        threshold = self.config.similarity_threshold if similarity_threshold is None else similarity_threshold
        cache_key = self._cache_key(cleaned, limit, threshold, categories)
        cached = self.retrieval_cache.get(cache_key)
        if cached is not None:
            return cached
        rewritten = self.query_rewriter.rewrite(cleaned)
        query_embedding = self.embedding_provider.embed([rewritten])
        raw_results = self.vector_store.search(query_embedding, max(limit * 3, limit))
        category_set = {category.lower() for category in categories} if categories else None
        combined: dict[int, RAGSearchResult] = {}
        for memory_id, similarity in raw_results:
            if similarity < threshold:
                continue
            memory = self.repository.get(memory_id)
            if memory is None:
                continue
            if category_set and memory.category not in category_set:
                continue
            score = self.score_memory(memory, similarity) * self.config.hybrid_vector_weight
            combined[memory_id] = RAGSearchResult(memory, similarity, score, 0)
        for memory, keyword_score in self.repository.search_lexical(rewritten, max(limit * 3, limit)):
            if memory.id is None:
                continue
            if category_set and memory.category not in category_set:
                continue
            extra = keyword_score * self.config.hybrid_keyword_weight
            existing = combined.get(memory.id)
            if existing is None:
                combined[memory.id] = RAGSearchResult(memory, 0.0, extra, 0)
            else:
                existing.score += extra
        results = list(combined.values())
        results.sort(key=lambda item: item.score, reverse=True)
        ranked = results[: max(1, limit)]
        for index, result in enumerate(ranked, start=1):
            result.rank = index
        self.repository.mark_accessed([result.memory.id for result in ranked if result.memory.id is not None])
        self.retrieval_cache.set(cache_key, ranked)
        return ranked

    def retrieve_top_k(self, query: str, top_k: int = 6) -> list[RAGSearchResult]:
        return self.search_memories(query, top_k=top_k)

    def retrieve_conversation_context(self, user_message: str, top_k: int | None = None) -> ConversationContext:
        results = self.search_memories(
            user_message,
            top_k=top_k or self.config.default_top_k,
            similarity_threshold=0.0,
        )
        lines: list[str] = []
        used = 0
        for result in results:
            source_label = self._source_label(result.memory)
            line = f"- {result.memory.category}{source_label}: {result.memory.content}"
            if used + len(line) > self.config.max_context_characters:
                break
            lines.append(line)
            used += len(line)
        return ConversationContext(user_message, results, "\n".join(lines))

    def detect_duplicate(self, content: str) -> DuplicateCheck:
        cleaned = " ".join(content.strip().split())
        if not cleaned:
            return DuplicateCheck(False, reason="empty")
        exact = self.repository.get_by_hash(self.repository.content_hash(cleaned))
        if exact is not None:
            return DuplicateCheck(True, exact.id, 1.0, "exact_hash")
        results = self.search_memories(
            cleaned,
            top_k=1,
            similarity_threshold=self.config.duplicate_threshold,
        )
        if results:
            top = results[0]
            return DuplicateCheck(True, top.memory.id, top.similarity, "embedding_similarity")
        return DuplicateCheck(False, None, 0.0, "none")

    def score_memory(self, memory: RAGMemory, similarity: float) -> float:
        recency = self._recency_score(memory.updated_at or memory.created_at)
        importance = max(0.0, min(1.0, memory.importance))
        confidence = max(0.0, min(1.0, memory.confidence))
        return (
            similarity * 0.62
            + importance * 0.18
            + confidence * 0.12
            + recency * 0.08
        )

    def rebuild_index(self) -> None:
        memories = self.repository.list_active()
        if not memories:
            self.vector_store.rebuild([], np.zeros((0, self.embedding_provider.dimension), dtype=np.float32))
            return
        embeddings = self.embedding_provider.embed([memory.content for memory in memories])
        ids = [int(memory.id) for memory in memories if memory.id is not None]
        self.vector_store.rebuild(ids, embeddings)
        self.retrieval_cache.clear()

    def expire_memories(self) -> int:
        expired = self.repository.expire_due_memories()
        if expired:
            self.rebuild_index()
            self.retrieval_cache.clear()
        return expired

    def health(self) -> RAGHealth:
        warnings: list[str] = []
        active = self.repository.count_active()
        vectors = self.vector_store.vector_count
        if active != vectors:
            warnings.append(f"active memory count {active} does not match vector count {vectors}")
        return RAGHealth(
            database_path=str(self.config.database_path),
            vector_index_path=str(self.config.index_path),
            active_memories=active,
            vector_count=vectors,
            cache_entries=self.retrieval_cache.size,
            embedding_backend=self.config.embedding_backend,
            last_index_version=self.vector_store.current_version(),
            healthy=not warnings,
            warnings=warnings,
        )

    def _recency_score(self, timestamp: str) -> float:
        if not timestamp:
            return 0.5
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return 0.5
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400)
        return math.exp(-age_days / max(1.0, self.config.recency_half_life_days))

    @staticmethod
    def _source_label(memory: RAGMemory) -> str:
        if memory.source_id:
            return f" [{memory.source}:{memory.source_id}]"
        if memory.source_title:
            return f" [{memory.source}:{memory.source_title}]"
        if memory.source:
            return f" [{memory.source}]"
        return ""

    @staticmethod
    def _cache_key(query: str, top_k: int, threshold: float, categories: list[str] | None) -> str:
        category_key = ",".join(sorted(category.lower() for category in categories or []))
        return f"{query.lower()}|{top_k}|{threshold:.4f}|{category_key}"
