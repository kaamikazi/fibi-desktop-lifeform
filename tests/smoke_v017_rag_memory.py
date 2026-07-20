"""Smoke test for Fibi v0.17 local RAG memory."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        service = RAGMemoryService(
            RAGConfig(
                database_path=root / "fibi_memory.db",
                vector_dir=root / "rag",
                embedding_backend="hashing",
                embedding_dimension=128,
                similarity_threshold=0.08,
                duplicate_threshold=0.88,
                default_top_k=3,
            )
        )

        project = service.add_memory(
            "Imran is building Fibi as a tiny desktop lifeform.",
            category="project",
            source="smoke",
            importance=0.9,
            confidence=0.9,
        )
        habit = service.add_memory("The user likes short sleepy replies.", category="habit", source="smoke")
        assert project.id is not None
        assert habit.id is not None

        duplicate = service.detect_duplicate("Imran is building Fibi as a tiny desktop lifeform.")
        assert duplicate.is_duplicate
        assert duplicate.existing_id == project.id

        top = service.retrieve_top_k("Fibi desktop creature", top_k=2)
        assert top
        assert top[0].memory.category == "project"

        context = service.retrieve_conversation_context("what do you know about Fibi?")
        assert "desktop lifeform" in context.context_text

        updated = service.update_memory(habit.id, content="The user likes cute sleepy local replies.")
        assert updated is not None
        assert "local replies" in updated.content

        assert service.delete_memory(project.id)
        remaining = service.search_memories("desktop lifeform", top_k=3, similarity_threshold=0.01)
        assert all(result.memory.id != project.id for result in remaining)

    print("Fibi v0.17 RAG memory smoke tests passed.")


if __name__ == "__main__":
    run()


