"""Local embedding providers.

The default provider is deterministic feature hashing. It is not cloud-backed,
does not download anything, and is stable enough for tests and offline use.
If sentence-transformers is installed and explicitly configured, Fibi can use
that local model too.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod

import numpy as np

LOGGER = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Interface for local embedding providers."""

    dimension: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalized float32 embeddings."""


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding model using signed feature hashing."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = max(64, int(dimension))

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in self._tokens(text):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dimension
                vectors[row, bucket] += 1.0
            norm = float(np.linalg.norm(vectors[row]))
            if norm > 0:
                vectors[row] /= norm
        return vectors

    @staticmethod
    def _tokens(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9_]{2,}", text.lower())
        bigrams = [f"{words[index]}_{words[index + 1]}" for index in range(max(0, len(words) - 1))]
        return words + bigrams


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Optional local sentence-transformers provider."""

    def __init__(self, model_name: str, dimension: int = 384) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("sentence-transformers is not installed") from error
        self.model = SentenceTransformer(model_name)
        self.dimension = int(dimension)

    def embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embeddings, dtype=np.float32)


def build_embedding_provider(backend: str, dimension: int, model_name: str) -> EmbeddingProvider:
    if backend == "sentence_transformers":
        LOGGER.info("Using local sentence-transformers embeddings: %s", model_name)
        return SentenceTransformerEmbeddingProvider(model_name, dimension)
    if backend != "hashing":
        LOGGER.warning("Unknown embedding backend %s; using hashing", backend)
    LOGGER.info("Using local hashing embeddings")
    return HashingEmbeddingProvider(dimension)
