"""Configuration for the local RAG memory system."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fibi.paths import data_path


@dataclass(slots=True)
class RAGConfig:
    """RAG settings with conservative local-first defaults."""

    database_path: Path = data_path("fibi_memory.db")
    vector_dir: Path = data_path("rag")
    index_name: str = "fibi_rag.faiss"
    id_map_name: str = "fibi_rag_ids.json"
    manifest_name: str = "fibi_rag_manifest.json"
    embedding_backend: str = "hashing"
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    similarity_threshold: float = 0.35
    duplicate_threshold: float = 0.92
    hybrid_vector_weight: float = 0.72
    hybrid_keyword_weight: float = 0.28
    default_top_k: int = 6
    max_context_characters: int = 1200
    recency_half_life_days: float = 45.0
    retrieval_cache_size: int = 128
    retrieval_cache_ttl_seconds: int = 120
    chunk_size_chars: int = 900
    chunk_overlap_chars: int = 120

    @property
    def index_path(self) -> Path:
        return self.vector_dir / self.index_name

    @property
    def id_map_path(self) -> Path:
        return self.vector_dir / self.id_map_name

    @property
    def manifest_path(self) -> Path:
        return self.vector_dir / self.manifest_name
