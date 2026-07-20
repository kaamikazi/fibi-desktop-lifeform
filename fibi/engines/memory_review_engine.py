"""User-facing review layer over Fibi's local RAG memory notebook."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
from fibi.engines.types import (
    MemoryApprovalResult,
    MemoryDeleteRequest,
    MemoryEditRequest,
    MemoryExportRequest,
    MemoryReviewItem,
    MemorySearchResult,
)
from fibi.paths import data_dir
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from fibi.rag.types import RAGMemory

LOGGER = logging.getLogger(__name__)


class MemoryReviewEngine:
    """Review, edit, delete, and export memories without duplicating storage."""

    REVIEW_KEY = "review"

    def __init__(
        self,
        rag_memory: RAGMemoryServiceFacade,
        *,
        guard: SensitiveMemoryGuard | None = None,
        deletion_log_path: Path | None = None,
    ) -> None:
        self.rag_memory = rag_memory
        self.guard = guard or SensitiveMemoryGuard()
        self.deletion_log_path = Path(deletion_log_path or (data_dir() / "memory" / "memory_deletion_log.jsonl"))
        self.deletion_log_path.parent.mkdir(parents=True, exist_ok=True)

    def list_memories(
        self,
        *,
        category: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[MemoryReviewItem]:
        memories = self._all_memories(include_deleted=False)
        items = [self._to_item(memory) for memory in memories]
        if category:
            items = [item for item in items if item.category == category]
        if not include_archived:
            items = [item for item in items if not item.archived]
        items = [item for item in items if item.user_visible]
        items.sort(key=lambda item: (not item.pinned, item.archived, item.updated_at), reverse=False)
        return items[: max(1, min(limit, 200))]

    def search_memories(self, query: str, *, top_k: int = 10) -> list[MemorySearchResult]:
        text = query.strip()
        if not text:
            return []
        results = self.rag_memory.service.search_memories(text, top_k=top_k, similarity_threshold=0.0)
        review_results: list[MemorySearchResult] = []
        for result in results:
            item = self._to_item(result.memory)
            if item.archived or not item.user_visible:
                continue
            review_results.append(MemorySearchResult(item, result.score, result.similarity, result.rank))
        return review_results

    def get_memory(self, memory_id: int, *, include_deleted: bool = False) -> MemoryReviewItem | None:
        memory = self.rag_memory.service.repository.get(memory_id, include_deleted=include_deleted)
        return self._to_item(memory) if memory else None

    def approve_memory(self, memory_id: int) -> MemoryApprovalResult:
        return self._update_review(memory_id, {"approved": True, "sensitive_requires_approval": False}, "approved memory crumb.")

    def pin_memory(self, memory_id: int, pinned: bool = True) -> MemoryApprovalResult:
        return self._update_review(memory_id, {"pinned": bool(pinned)}, "pinned memory crumb." if pinned else "unpinned memory crumb.")

    def archive_memory(self, memory_id: int, archived: bool = True) -> MemoryApprovalResult:
        return self._update_review(memory_id, {"archived": bool(archived)}, "archived memory crumb." if archived else "unarchived memory crumb.")

    def edit_memory(self, request: MemoryEditRequest) -> MemoryApprovalResult:
        if not request.user_confirmed:
            return MemoryApprovalResult(False, request.memory_id, "edit needs confirm.", True)
        risk = self.guard.assess(request.new_text, source="memory_edit", user_requested=True)
        if risk.blocked:
            return MemoryApprovalResult(False, request.memory_id, risk.safe_summary or "secret crumb. not keeping.")
        existing = self.rag_memory.service.repository.get(request.memory_id)
        if existing is None:
            return MemoryApprovalResult(False, request.memory_id, "memory crumb not found.")
        metadata = dict(existing.metadata)
        review = self._review_metadata(existing)
        review["approved"] = not risk.requires_approval
        review["sensitive_flag"] = risk.sensitive_flag
        review["sensitive_requires_approval"] = risk.requires_approval
        review["edited_by_user"] = True
        metadata[self.REVIEW_KEY] = review
        try:
            updated = self.rag_memory.service.update_memory(
                request.memory_id,
                content=request.new_text,
                confidence=max(0.1, min(1.0, existing.confidence * 0.95)),
                metadata=metadata,
            )
        except Exception as exc:
            LOGGER.exception("memory_review.edit_failed")
            return MemoryApprovalResult(False, request.memory_id, f"edit failed: {exc}")
        if updated is None:
            return MemoryApprovalResult(False, request.memory_id, "memory crumb not found.")
        return MemoryApprovalResult(True, request.memory_id, "edited memory crumb.")

    def delete_memory(self, request: MemoryDeleteRequest) -> MemoryApprovalResult:
        if request.memory_id is None:
            return MemoryApprovalResult(False, None, "which memory crumb?")
        if not request.user_confirmed:
            return MemoryApprovalResult(False, request.memory_id, "delete needs confirm.", True)
        memory = self.rag_memory.service.repository.get(request.memory_id)
        if memory is None:
            return MemoryApprovalResult(False, request.memory_id, "memory crumb not found.")
        ok = self.rag_memory.delete_memory(request.memory_id)
        if ok:
            self._audit_delete(memory, request.reason, request.user_confirmed)
        return MemoryApprovalResult(ok, request.memory_id, "forgot one memory crumb." if ok else "memory crumb not found.")

    def delete_by_category(self, request: MemoryDeleteRequest) -> MemoryApprovalResult:
        if not request.user_confirmed:
            return MemoryApprovalResult(False, None, "category delete needs confirm.", True)
        category = request.category.strip().lower()
        if not category:
            return MemoryApprovalResult(False, None, "which memory category?")
        matches = [item for item in self.list_memories(category=category, include_archived=True, limit=200)]
        count = 0
        for item in matches:
            memory = self.rag_memory.service.repository.get(item.memory_id)
            if memory and self.rag_memory.delete_memory(item.memory_id):
                self._audit_delete(memory, request.reason or f"delete_category:{category}", True)
                count += 1
        return MemoryApprovalResult(True, None, f"forgot {count} {category} memory crumbs.")

    def export_memories(self, request: MemoryExportRequest | None = None) -> tuple[Path, Path]:
        request = request or MemoryExportRequest()
        selected = set(request.memory_ids)
        items = self.list_memories(include_archived=request.include_archived, limit=500)
        if selected:
            items = [item for item in items if item.memory_id in selected]
        safe_items = [
            item for item in items
            if not item.deletion_status == "deleted"
            and (request.include_sensitive or self.guard.can_export(item.text, item.sensitive_flag))
        ]
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        out_dir = data_dir() / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"memory_export_{stamp}.json"
        md_path = out_dir / f"memory_export_{stamp}.md"
        payload = {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "excluded": ["secrets", "raw private page text", "raw project source", "internal embeddings"],
            "memory_count": len(safe_items),
            "memories": [asdict(item) for item in safe_items],
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = ["# Fibi Memory Export", "", f"Created: {payload['created_at']}", "", "Excluded: secrets, raw private page text, raw project source, internal embeddings.", ""]
        for item in safe_items:
            lines.append(f"## {item.memory_id}: {item.category}")
            lines.append(item.summary or item.text)
            lines.append(f"source: {item.source}; confidence: {item.confidence:.2f}; approved: {item.approved}")
            lines.append("")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, md_path

    def summarize_categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.list_memories(include_archived=True, limit=500):
            counts[item.category] = counts.get(item.category, 0) + 1
        return counts

    def health(self, *, learning_status: str = "") -> dict[str, Any]:
        items = self.list_memories(include_archived=True, limit=1000)
        rag = self.rag_memory.health_check()
        pending = [item for item in items if item.sensitive_flag and not item.approved]
        approved = [item for item in items if item.approved]
        manifest = self._read_vector_manifest()
        return {
            "total_memories": len(items),
            "approved_count": len(approved),
            "pending_sensitive_count": len(pending),
            "vector_index_status": "ok" if rag.healthy else "needs rebuild",
            "vector_count": rag.vector_count,
            "last_indexing_time": manifest.get("updated_at_epoch", ""),
            "retrieval_cache_status": f"{rag.cache_entries} entries",
            "storage_path": rag.database_path,
            "learning_status": learning_status,
            "warnings": rag.warnings,
        }

    def format_list(self, items: list[MemoryReviewItem]) -> str:
        if not items:
            return "tiny memory pile is empty."
        return "\n".join(
            f"{item.memory_id}: {item.category} - {item.summary[:100]}"
            + (" [pinned]" if item.pinned else "")
            + (" [pending]" if item.sensitive_flag and not item.approved else "")
            for item in items[:10]
        )

    def format_search(self, results: list[MemorySearchResult]) -> str:
        if not results:
            return "no crumbs matched."
        return "\n".join(
            f"{result.item.memory_id}: {result.item.category} - {result.item.summary[:100]} (score {result.score:.2f})"
            for result in results[:10]
        )

    def format_item(self, item: MemoryReviewItem | None) -> str:
        if item is None:
            return "memory crumb not found."
        return (
            f"memory {item.memory_id}\n"
            f"category: {item.category}\n"
            f"source: {item.source}\n"
            f"confidence: {item.confidence:.2f}\n"
            f"approved: {item.approved}\n"
            f"pinned: {item.pinned}\n"
            f"archived: {item.archived}\n"
            f"sensitive: {item.sensitive_flag or 'no'}\n"
            f"text: {item.text}"
        )

    def format_health(self, learning_status: str = "") -> str:
        health = self.health(learning_status=learning_status)
        return (
            "memory health:\n"
            f"total: {health['total_memories']}\n"
            f"approved: {health['approved_count']}\n"
            f"pending/sensitive: {health['pending_sensitive_count']}\n"
            f"vector index: {health['vector_index_status']} ({health['vector_count']} vectors)\n"
            f"last indexing: {health['last_indexing_time'] or 'unknown'}\n"
            f"cache: {health['retrieval_cache_status']}\n"
            f"storage: {health['storage_path']}\n"
            f"learning: {health['learning_status'] or 'unknown'}"
        )

    def _update_review(self, memory_id: int, values: dict[str, Any], message: str) -> MemoryApprovalResult:
        memory = self.rag_memory.service.repository.get(memory_id)
        if memory is None:
            return MemoryApprovalResult(False, memory_id, "memory crumb not found.")
        metadata = dict(memory.metadata)
        review = self._review_metadata(memory)
        review.update(values)
        metadata[self.REVIEW_KEY] = review
        updated = self.rag_memory.service.update_memory(memory_id, metadata=metadata)
        return MemoryApprovalResult(updated is not None, memory_id, message if updated else "memory crumb not found.")

    def _to_item(self, memory: RAGMemory) -> MemoryReviewItem:
        review = self._review_metadata(memory)
        risk = self.guard.assess(memory.content, source=memory.source)
        text = risk.masked_preview if risk.blocked else memory.content
        summary = str(review.get("summary") or text[:220])
        tags = review.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        return MemoryReviewItem(
            memory_id=int(memory.id or 0),
            source=memory.source,
            category=memory.category,
            text=text,
            summary=summary,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            confidence=memory.confidence,
            approved=bool(review.get("approved", True)),
            pinned=bool(review.get("pinned", False)),
            archived=bool(review.get("archived", False)),
            sensitive_flag=str(review.get("sensitive_flag", "")),
            source_event_id=memory.source_id,
            provenance=memory.provenance,
            tags=[str(tag) for tag in tags],
            user_visible=bool(review.get("user_visible", True)),
            deletion_status="deleted" if memory.deleted else str(review.get("deletion_status", "active")),
        )

    def _review_metadata(self, memory: RAGMemory) -> dict[str, Any]:
        review = memory.metadata.get(self.REVIEW_KEY, {})
        if not isinstance(review, dict):
            review = {}
        risk = self.guard.assess(memory.content, source=memory.source)
        default_approved = not risk.requires_approval
        return {
            "approved": bool(review.get("approved", default_approved)),
            "pinned": bool(review.get("pinned", False)),
            "archived": bool(review.get("archived", False)),
            "sensitive_flag": str(review.get("sensitive_flag", risk.sensitive_flag)),
            "sensitive_requires_approval": bool(review.get("sensitive_requires_approval", risk.requires_approval)),
            "user_visible": bool(review.get("user_visible", True)),
            "deletion_status": str(review.get("deletion_status", "active")),
            "summary": str(review.get("summary", risk.safe_summary or memory.content[:220])),
            "tags": review.get("tags", []),
        }

    def _all_memories(self, *, include_deleted: bool) -> list[RAGMemory]:
        clause = "" if include_deleted else "WHERE deleted = 0"
        with self.rag_memory.service.repository.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM rag_memories {clause} ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [self.rag_memory.service.repository._row_to_memory(row) for row in rows]

    def _audit_delete(self, memory: RAGMemory, reason: str, user_confirmed: bool) -> None:
        record = {
            "memory_id": memory.id,
            "deleted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "category": memory.category,
            "reason": reason,
            "user_confirmed": bool(user_confirmed),
            "text_hash": hashlib.sha256(memory.content.encode("utf-8")).hexdigest(),
        }
        with self.deletion_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def _read_vector_manifest(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.rag_memory.service.vector_store.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}
