"""FAISS vector index wrapper for RAG memories."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import time

import numpy as np

LOGGER = logging.getLogger(__name__)


class FAISSVectorStore:
    """Persisted cosine-similarity FAISS index with an external ID map."""

    def __init__(self, index_path: Path, id_map_path: Path, dimension: int, manifest_path: Path | None = None) -> None:
        self.index_path = Path(index_path)
        self.id_map_path = Path(id_map_path)
        self.manifest_path = Path(manifest_path) if manifest_path is not None else self.index_path.with_suffix(".manifest.json")
        self.dimension = int(dimension)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss = self._import_faiss()
        self.index = self._load_index()
        self.id_map = self._load_id_map()

    def rebuild(self, memory_ids: list[int], embeddings: np.ndarray) -> None:
        self.index = self._faiss.IndexFlatIP(self.dimension)
        if len(memory_ids):
            self._validate_embeddings(embeddings)
            self.index.add(embeddings.astype(np.float32))
        self.id_map = list(memory_ids)
        self.save("rebuild")
        LOGGER.info("Rebuilt FAISS index with %d memories", len(memory_ids))

    def add(self, memory_ids: list[int], embeddings: np.ndarray) -> None:
        if not memory_ids:
            return
        self._validate_embeddings(embeddings)
        if len(memory_ids) != embeddings.shape[0]:
            raise ValueError("memory id count must match embedding rows")
        self.index.add(embeddings.astype(np.float32))
        self.id_map.extend(int(value) for value in memory_ids)
        self.save("incremental_add")
        LOGGER.info("Incrementally added %d memories to FAISS index", len(memory_ids))

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        if self.index.ntotal == 0:
            return []
        vector = query_embedding.astype(np.float32)
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        self._validate_embeddings(vector)
        scores, positions = self.index.search(vector, max(1, min(top_k, self.index.ntotal)))
        results: list[tuple[int, float]] = []
        for position, score in zip(positions[0], scores[0]):
            if position < 0 or position >= len(self.id_map):
                continue
            results.append((int(self.id_map[int(position)]), float(score)))
        return results

    @property
    def vector_count(self) -> int:
        return int(self.index.ntotal)

    def save(self, operation: str = "save") -> None:
        self._faiss.write_index(self.index, str(self.index_path))
        self.id_map_path.write_text(json.dumps(self.id_map), encoding="utf-8")
        manifest = self._load_manifest()
        manifest["version"] = int(manifest.get("version", 0)) + 1
        manifest["dimension"] = self.dimension
        manifest["vector_count"] = int(self.index.ntotal)
        manifest["id_count"] = len(self.id_map)
        manifest["last_operation"] = operation
        manifest["updated_at_epoch"] = time()
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def current_version(self) -> int:
        return int(self._load_manifest().get("version", 0))

    def _load_index(self):
        if self.index_path.exists():
            index = self._faiss.read_index(str(self.index_path))
            if index.d != self.dimension:
                LOGGER.warning("FAISS dimension changed; rebuilding empty index")
                return self._faiss.IndexFlatIP(self.dimension)
            return index
        return self._faiss.IndexFlatIP(self.dimension)

    def _load_id_map(self) -> list[int]:
        try:
            raw = json.loads(self.id_map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [int(value) for value in raw if isinstance(value, int)]

    def _load_manifest(self) -> dict:
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _validate_embeddings(self, embeddings: np.ndarray) -> None:
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(f"expected embeddings shaped (*, {self.dimension})")

    @staticmethod
    def _import_faiss():
        try:
            import faiss
        except ImportError as error:
            raise RuntimeError("faiss-cpu is required for Fibi RAG memory") from error
        return faiss
