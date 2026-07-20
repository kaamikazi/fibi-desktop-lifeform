"""Typed data objects for Fibi's local RAG memory system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RAGMemory:
    id: int | None
    category: str
    content: str
    source: str = "conversation"
    source_id: str = ""
    source_uri: str = ""
    source_title: str = ""
    source_timestamp: str = ""
    importance: float = 0.5
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    access_count: int = 0
    expires_at: str = ""
    deleted: bool = False


@dataclass(slots=True)
class RAGSearchResult:
    memory: RAGMemory
    similarity: float
    score: float
    rank: int


@dataclass(slots=True)
class DuplicateCheck:
    is_duplicate: bool
    existing_id: int | None = None
    similarity: float = 0.0
    reason: str = ""


@dataclass(slots=True)
class ConversationContext:
    query: str
    results: list[RAGSearchResult]
    context_text: str


@dataclass(slots=True)
class RAGEvaluationCase:
    query: str
    expected_source_ids: list[str]
    top_k: int = 3
    category: str | None = None


@dataclass(slots=True)
class RAGEvaluationResult:
    case: RAGEvaluationCase
    retrieved_source_ids: list[str]
    hit: bool
    reciprocal_rank: float
    precision_at_k: float = 0.0
    latency_ms: float = 0.0


@dataclass(slots=True)
class RAGEvaluationSummary:
    dataset_path: str
    case_count: int
    hit_count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    mean_precision_at_k: float
    mean_latency_ms: float
    p95_latency_ms: float
    empty_result_count: int
    false_positive_count: int = 0
    failures: list[str] = field(default_factory=list)
    results: list[RAGEvaluationResult] = field(default_factory=list)


@dataclass(slots=True)
class RAGHealth:
    database_path: str
    vector_index_path: str
    active_memories: int
    vector_count: int
    cache_entries: int
    embedding_backend: str
    last_index_version: int
    healthy: bool
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentIngestionResult:
    document_id: str
    source_path: str
    mime_type: str
    chunk_count: int
    indexed_count: int
    skipped_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
