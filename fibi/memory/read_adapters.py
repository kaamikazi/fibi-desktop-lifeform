"""Read-only adapters over Fibi's existing legacy and RAG memory stores."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol

import numpy as np

from fibi.memory.policy import MemoryStatus, MetadataScalar
from fibi.memory.protocols import MemoryReadAdapter
from fibi.memory.query_models import (
    MemoryListFilter,
    MemoryQueryRequest,
    MemoryReadSource,
    MemoryRecordView,
    MemorySourceFailure,
    MemorySourceHealth,
    MemorySourceReadResult,
    MemorySourceReference,
    MemoryViewCategory,
)
from fibi.memory.read_policy import MemoryReadPolicy
from fibi.rag.service import RAGMemoryService
from fibi.rag.types import RAGMemory


class LegacyMemoryOwner(Protocol):
    database_path: Path


_CATEGORY_MAP = {
    "fact": MemoryViewCategory.FACT,
    "preference": MemoryViewCategory.PREFERENCE,
    "project": MemoryViewCategory.PROJECT,
    "summary": MemoryViewCategory.SUMMARY,
}


@contextmanager
def _read_only_connection(path: Path) -> Iterator[sqlite3.Connection]:
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True, timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    try:
        yield connection
    finally:
        connection.close()


def _category(raw: str) -> MemoryViewCategory:
    return _CATEGORY_MAP.get(raw.lower().strip(), MemoryViewCategory.UNKNOWN_LEGACY)


def _json_mapping(raw: object) -> dict[str, Any]:
    if not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _error_category(error: BaseException) -> str:
    if isinstance(error, (FileNotFoundError, sqlite3.OperationalError)):
        return "storage_unavailable"
    if isinstance(error, sqlite3.DatabaseError):
        return "storage_invalid"
    return "read_unavailable"


def _terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(re.findall(r"[a-zA-Z0-9_]{2,}", query.lower())))[:8]


class LegacyMemoryReadAdapter(MemoryReadAdapter):
    """Normalize legacy rows through query-only SQLite connections."""

    source = MemoryReadSource.LEGACY

    def __init__(self, owner: LegacyMemoryOwner, policy: MemoryReadPolicy) -> None:
        self._owner = owner
        self._database_path = Path(owner.database_path)
        self._policy = policy

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        if reference.source is not self.source or not self._database_path.is_file():
            return None
        try:
            memory_id = int(reference.source_record_id)
            with _read_only_connection(self._database_path) as connection:
                row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            return self._map(row) if row is not None else None
        except (ValueError, OSError, sqlite3.Error):
            return None

    def query(self, request: MemoryQueryRequest) -> MemorySourceReadResult:
        if request.sources and self.source not in request.sources:
            return MemorySourceReadResult(self.source)
        return self._read(request.query, request.categories, request.bounded_limit)

    def list(self, filters: MemoryListFilter) -> MemorySourceReadResult:
        if filters.sources and self.source not in filters.sources:
            return MemorySourceReadResult(self.source)
        return self._read("", filters.categories, filters.bounded_limit)

    def health(self) -> MemorySourceHealth:
        if not self._database_path.is_file():
            return MemorySourceHealth(self.source, False, error_category="storage_missing")
        try:
            with _read_only_connection(self._database_path) as connection:
                count = int(connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
            return MemorySourceHealth(self.source, True, record_count=count)
        except (OSError, sqlite3.Error) as error:
            return MemorySourceHealth(self.source, False, error_category=_error_category(error))

    def _read(
        self,
        query: str,
        categories: tuple[MemoryViewCategory, ...],
        limit: int,
    ) -> MemorySourceReadResult:
        if not self._database_path.is_file():
            return MemorySourceReadResult(
                self.source,
                failures=(MemorySourceFailure(self.source, "storage_missing"),),
            )
        query_terms = _terms(query)
        params: list[object] = []
        where = ""
        if query_terms:
            where = "WHERE (" + " OR ".join("LOWER(content) LIKE ?" for _ in query_terms) + ")"
            params.extend(f"%{term}%" for term in query_terms)
        params.append(min(400, max(limit * 4, limit)))
        try:
            with _read_only_connection(self._database_path) as connection:
                rows = connection.execute(
                    f"SELECT * FROM memories {where} "
                    "ORDER BY importance DESC, created_at DESC, id ASC LIMIT ?",
                    params,
                ).fetchall()
        except (OSError, sqlite3.Error) as error:
            return MemorySourceReadResult(
                self.source,
                failures=(MemorySourceFailure(self.source, _error_category(error)),),
            )
        records: list[MemoryRecordView] = []
        for row in rows:
            mapped = self._map(row, query_terms)
            if mapped is None or (categories and mapped.category not in categories):
                continue
            records.append(mapped)
        records.sort(key=_record_sort_key)
        return MemorySourceReadResult(self.source, tuple(records[:limit]))

    def _map(self, row: sqlite3.Row, query_terms: tuple[str, ...] = ()) -> MemoryRecordView | None:
        if _legacy_row_unavailable(row):
            return None
        metadata = _json_mapping(row["metadata_json"] if "metadata_json" in row.keys() else "{}")
        content = str(row["content"])
        origin_source = str(row["source"] if "source" in row.keys() else "legacy")
        decision = self._policy.evaluate(content, metadata, origin_source)
        if not decision.allowed:
            return None
        score = _lexical_score(content, query_terms) if query_terms else None
        return MemoryRecordView(
            source=self.source,
            source_record_id=str(row["id"]),
            category=_category(str(row["category"])),
            content=content,
            consent_status=decision.consent,
            sensitivity=decision.sensitivity,
            importance=_optional_float(row, "importance"),
            confidence=_optional_float(row, "confidence"),
            created_at=_optional_text(row, "created_at"),
            updated_at=_optional_text(row, "updated_at"),
            last_used_at=_optional_text(row, "last_accessed_at"),
            status=decision.status,
            retrieval_score=score,
            provenance={"adapter": "legacy", "origin_source": origin_source[:160]},
        )


class RAGMemoryReadAdapter(MemoryReadAdapter):
    """Read existing RAG rows without cache, access-count, or index mutation."""

    source = MemoryReadSource.RAG

    def __init__(self, service: RAGMemoryService | None, policy: MemoryReadPolicy) -> None:
        self._service = service
        self._database_path = Path(service.config.database_path) if service is not None else None
        self._policy = policy

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        if reference.source is not self.source or not self._available_path():
            return None
        try:
            memory_id = int(reference.source_record_id)
            with _read_only_connection(self._database_path) as connection:  # type: ignore[arg-type]
                row = connection.execute(
                    "SELECT * FROM rag_memories WHERE id = ? AND deleted = 0 "
                    "AND (expires_at = '' OR datetime(expires_at) > datetime('now'))",
                    (memory_id,),
                ).fetchone()
            return self._map(_rag_memory(row)) if row is not None else None
        except (ValueError, OSError, sqlite3.Error):
            return None

    def query(self, request: MemoryQueryRequest) -> MemorySourceReadResult:
        if request.sources and self.source not in request.sources:
            return MemorySourceReadResult(self.source)
        return self._read(request.query, request.categories, request.bounded_limit)

    def list(self, filters: MemoryListFilter) -> MemorySourceReadResult:
        if filters.sources and self.source not in filters.sources:
            return MemorySourceReadResult(self.source)
        return self._read("", filters.categories, filters.bounded_limit)

    def health(self) -> MemorySourceHealth:
        if not self._available_path():
            return MemorySourceHealth(self.source, False, error_category="storage_missing")
        try:
            with _read_only_connection(self._database_path) as connection:  # type: ignore[arg-type]
                count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM rag_memories WHERE deleted = 0 "
                        "AND (expires_at = '' OR datetime(expires_at) > datetime('now'))"
                    ).fetchone()[0]
                )
            vector_store = self._service.vector_store  # type: ignore[union-attr]
            backend = str(getattr(vector_store, "backend_name", "faiss"))
            return MemorySourceHealth(
                self.source,
                True,
                record_count=count,
                semantic_index_available=hasattr(vector_store, "search"),
                semantic_acceleration_available=backend == "faiss",
                semantic_backend=backend,
            )
        except (OSError, sqlite3.Error) as error:
            return MemorySourceHealth(self.source, False, error_category=_error_category(error))
        except Exception:
            return MemorySourceHealth(
                self.source,
                True,
                semantic_index_available=False,
                semantic_acceleration_available=False,
                error_category="semantic_unavailable",
            )

    def _read(
        self,
        query: str,
        categories: tuple[MemoryViewCategory, ...],
        limit: int,
    ) -> MemorySourceReadResult:
        if not self._available_path():
            return MemorySourceReadResult(
                self.source,
                failures=(MemorySourceFailure(self.source, "storage_missing"),),
            )
        try:
            memories, semantic_failed = self._read_candidates(query, limit)
        except (OSError, sqlite3.Error) as error:
            return MemorySourceReadResult(
                self.source,
                failures=(MemorySourceFailure(self.source, _error_category(error)),),
            )
        except Exception:
            return MemorySourceReadResult(
                self.source,
                failures=(MemorySourceFailure(self.source, "read_unavailable"),),
            )
        records: list[MemoryRecordView] = []
        for memory, score, similarity in memories:
            mapped = self._map(memory, score=score, similarity=similarity)
            if mapped is None or (categories and mapped.category not in categories):
                continue
            records.append(mapped)
        records.sort(key=_record_sort_key)
        ranked = tuple(
            replace(item, provenance={**item.provenance, "rank": rank})
            for rank, item in enumerate(records[:limit], start=1)
        )
        failures: tuple[MemorySourceFailure, ...] = ()
        if query.strip() and semantic_failed:
            failures = (MemorySourceFailure(self.source, "semantic_unavailable", degraded=True),)
        return MemorySourceReadResult(self.source, ranked, failures)

    def _read_candidates(
        self,
        query: str,
        limit: int,
    ) -> tuple[list[tuple[RAGMemory, float | None, float | None]], bool]:
        if not query.strip():
            with _read_only_connection(self._database_path) as connection:  # type: ignore[arg-type]
                rows = connection.execute(
                    "SELECT * FROM rag_memories WHERE deleted = 0 "
                    "AND (expires_at = '' OR datetime(expires_at) > datetime('now')) "
                    "ORDER BY importance DESC, updated_at DESC, id ASC LIMIT ?",
                    (limit * 4,),
                ).fetchall()
            return [(_rag_memory(row), None, None) for row in rows], False

        service = self._service
        assert service is not None
        cleaned = " ".join(query.split())
        rewritten = service.query_rewriter.rewrite(cleaned)
        query_terms = _terms(rewritten)
        candidate_limit = min(200, max(limit * 4, limit))
        vector_scores: dict[int, float] = {}
        query_embedding: np.ndarray | None = None
        semantic_failed = False
        try:
            query_embedding = service.embedding_provider.embed([rewritten])
            vector_scores = {
                int(memory_id): max(0.0, float(similarity))
                for memory_id, similarity in service.vector_store.search(query_embedding, candidate_limit)
            }
        except Exception:
            vector_scores = {}
            query_embedding = None
            semantic_failed = True

        with _read_only_connection(self._database_path) as connection:  # type: ignore[arg-type]
            rows_by_id: dict[int, sqlite3.Row] = {}
            if vector_scores:
                ids = sorted(vector_scores)
                placeholders = ",".join("?" for _ in ids)
                rows = connection.execute(
                    f"SELECT * FROM rag_memories WHERE id IN ({placeholders}) AND deleted = 0 "
                    "AND (expires_at = '' OR datetime(expires_at) > datetime('now'))",
                    ids,
                ).fetchall()
                for row in rows:
                    rows_by_id[int(row["id"])] = row
            lexical_rows = _rag_lexical_rows(connection, query_terms, candidate_limit)
            for row in lexical_rows:
                rows_by_id[int(row["id"])] = row

        ranked: list[tuple[RAGMemory, float, float]] = []
        for memory_id, row in rows_by_id.items():
            memory = _rag_memory(row)
            similarity = vector_scores.get(memory_id, 0.0)
            if memory_id not in vector_scores and query_embedding is not None:
                try:
                    embedded = service.embedding_provider.embed([memory.content])[0]
                    similarity = max(0.0, float(np.dot(query_embedding[0], embedded)))
                except Exception:
                    similarity = 0.0
            keyword = _lexical_score(f"{memory.content} {memory.category}", query_terms) or 0.0
            score = (
                service.score_memory(memory, similarity, cleaned) * service.config.hybrid_vector_weight
                + keyword * service.config.hybrid_keyword_weight
            )
            ranked.append((memory, score, similarity))
        ranked.sort(key=lambda item: (-item[1], int(item[0].id or 0)))
        return ranked[:candidate_limit], semantic_failed

    def _map(
        self,
        memory: RAGMemory,
        *,
        score: float | None = None,
        similarity: float | None = None,
    ) -> MemoryRecordView | None:
        metadata = memory.metadata if isinstance(memory.metadata, Mapping) else {}
        decision = self._policy.evaluate(memory.content, metadata, memory.source)
        if memory.deleted or not decision.allowed:
            return None
        status = decision.status or MemoryStatus.ACTIVE
        provenance: dict[str, MetadataScalar] = {
            "adapter": "rag",
            "origin_source": memory.source[:160],
            "origin_source_id": memory.source_id[:160],
        }
        if memory.source_timestamp:
            provenance["source_timestamp"] = memory.source_timestamp[:80]
        if similarity is not None:
            provenance["semantic_similarity"] = round(similarity, 6)
        return MemoryRecordView(
            source=self.source,
            source_record_id=str(memory.id),
            category=_category(memory.category),
            content=memory.content,
            consent_status=decision.consent,
            sensitivity=decision.sensitivity,
            importance=max(0.0, min(1.0, memory.importance)),
            confidence=max(0.0, min(1.0, memory.confidence)),
            created_at=memory.created_at or None,
            updated_at=memory.updated_at or None,
            last_used_at=memory.last_accessed_at or None,
            status=status,
            retrieval_score=max(0.0, score) if score is not None else None,
            provenance=provenance,
        )

    def _available_path(self) -> bool:
        return self._database_path is not None and self._database_path.is_file()

def _rag_lexical_rows(
    connection: sqlite3.Connection,
    query_terms: tuple[str, ...],
    limit: int,
) -> list[sqlite3.Row]:
    if not query_terms:
        return []
    clauses = " OR ".join("LOWER(content || ' ' || category || ' ' || source_title) LIKE ?" for _ in query_terms)
    return connection.execute(
        f"SELECT * FROM rag_memories WHERE deleted = 0 "
        "AND (expires_at = '' OR datetime(expires_at) > datetime('now')) "
        f"AND ({clauses}) ORDER BY importance DESC, updated_at DESC, id ASC LIMIT ?",
        [*(f"%{term}%" for term in query_terms), limit],
    ).fetchall()


def _legacy_row_unavailable(row: sqlite3.Row) -> bool:
    keys = set(row.keys())
    if "deleted" in keys and bool(row["deleted"]):
        return True
    if "status" in keys and str(row["status"]).lower() in {"deleted", "expired"}:
        return True
    if "expires_at" not in keys or row["expires_at"] in {None, ""}:
        return False
    try:
        expires_at = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at.astimezone(timezone.utc) <= datetime.now(timezone.utc)


def _rag_memory(row: sqlite3.Row) -> RAGMemory:
    return RAGMemory(
        id=int(row["id"]),
        category=str(row["category"]),
        content=str(row["content"]),
        source=str(row["source"]),
        source_id=str(row["source_id"]),
        source_uri="",
        source_title="",
        source_timestamp=str(row["source_timestamp"]),
        importance=float(row["importance"]),
        confidence=float(row["confidence"]),
        metadata=_json_mapping(row["metadata_json"]),
        provenance={},
        content_hash=str(row["content_hash"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        last_accessed_at=str(row["last_accessed_at"]),
        access_count=int(row["access_count"]),
        expires_at=str(row["expires_at"]),
        deleted=bool(row["deleted"]),
    )


def _lexical_score(content: str, query_terms: tuple[str, ...]) -> float | None:
    if not query_terms:
        return None
    lowered = content.lower()
    hits = sum(1 for term in query_terms if term in lowered)
    return hits / len(query_terms)


def _optional_float(row: sqlite3.Row, key: str) -> float | None:
    if key not in row.keys() or row[key] is None:
        return None
    return max(0.0, min(1.0, float(row[key])))


def _optional_text(row: sqlite3.Row, key: str) -> str | None:
    if key not in row.keys() or row[key] in {None, ""}:
        return None
    return str(row[key])


def _record_sort_key(record: MemoryRecordView) -> tuple[float, float, str, str]:
    score = record.retrieval_score if record.retrieval_score is not None else -math.inf
    importance = record.importance if record.importance is not None else 0.0
    return (-score, -importance, record.source.value, record.source_record_id)


__all__ = ["LegacyMemoryReadAdapter", "RAGMemoryReadAdapter"]
