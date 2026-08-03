"""FAISS vector index wrapper for RAG memories."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import time

import numpy as np

LOGGER = logging.getLogger(__name__)


class _NumpyInnerProductIndex:
    """Small FAISS-compatible index used when optional acceleration is absent."""

    def __init__(self, dimension: int, vectors: np.ndarray | None = None) -> None:
        self.d = int(dimension)
        self.vectors = (
            np.asarray(vectors, dtype=np.float32).reshape((-1, self.d))
            if vectors is not None
            else np.empty((0, self.d), dtype=np.float32)
        )

    @property
    def ntotal(self) -> int:
        return int(self.vectors.shape[0])

    def add(self, vectors: np.ndarray) -> None:
        incoming = np.asarray(vectors, dtype=np.float32).reshape((-1, self.d))
        self.vectors = np.concatenate((self.vectors, incoming), axis=0)

    def search(self, query: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        query_vectors = np.asarray(query, dtype=np.float32).reshape((-1, self.d))
        if self.ntotal == 0:
            shape = (query_vectors.shape[0], int(top_k))
            return np.full(shape, -np.inf, dtype=np.float32), np.full(shape, -1, dtype=np.int64)
        scores = query_vectors @ self.vectors.T
        positions = np.argsort(-scores, axis=1)[:, :top_k]
        ranked = np.take_along_axis(scores, positions, axis=1)
        return ranked.astype(np.float32), positions.astype(np.int64)


class _NumpyVectorBackend:
    """Persist the fallback index locally using NumPy's non-pickle format."""

    name = "numpy"

    @staticmethod
    def IndexFlatIP(dimension: int) -> _NumpyInnerProductIndex:
        return _NumpyInnerProductIndex(dimension)

    @staticmethod
    def write_index(index: _NumpyInnerProductIndex, path: str) -> None:
        with Path(path).open("wb") as stream:
            np.save(stream, index.vectors, allow_pickle=False)

    @staticmethod
    def read_index(path: str) -> _NumpyInnerProductIndex:
        with Path(path).open("rb") as stream:
            vectors = np.load(stream, allow_pickle=False)
        if vectors.ndim != 2:
            raise ValueError("fallback vector index must be two-dimensional")
        return _NumpyInnerProductIndex(int(vectors.shape[1]), vectors)


class FAISSVectorStore:
    """Persisted cosine-similarity FAISS index with an external ID map."""

    def __init__(self, index_path: Path, id_map_path: Path, dimension: int, manifest_path: Path | None = None) -> None:
        self.index_path = Path(index_path)
        self.id_map_path = Path(id_map_path)
        self.manifest_path = Path(manifest_path) if manifest_path is not None else self.index_path.with_suffix(".manifest.json")
        self.dimension = int(dimension)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss = self._import_faiss()
        self.backend_name = getattr(self._faiss, "name", "faiss")
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
            try:
                index = self._faiss.read_index(str(self.index_path))
            except Exception as error:
                LOGGER.warning(
                    "Vector index %s is incompatible with the %s backend; rebuilding: %s",
                    self.index_path.name,
                    self.backend_name,
                    type(error).__name__,
                )
                return self._faiss.IndexFlatIP(self.dimension)
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
            LOGGER.warning("FAISS unavailable; using the local NumPy vector fallback: %s", type(error).__name__)
            return _NumpyVectorBackend()
        return faiss
