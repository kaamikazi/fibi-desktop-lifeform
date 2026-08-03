"""Local document ingestion for Fibi RAG.

The ingestion layer is intentionally local and dependency-light. NeMo Retriever
can be integrated later behind the same boundary when its CLI is installed; this
module provides the strongest built-in alternative without pretending to use
external NVIDIA services.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import threading
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Protocol

from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService
from fibi.rag.types import DocumentIngestionResult

LOGGER = logging.getLogger(__name__)

TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
BLOCKED_SECRET_NAMES = {
    ".env",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}
BLOCKED_SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".token", ".secret"}


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    text: str
    chunk_index: int
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    text: str
    mime_type: str
    metadata: dict
    skipped_reason: str = ""


class DocumentExtractor(Protocol):
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract local text and metadata from a file."""


class PlainTextExtractor:
    def extract(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        return ExtractedDocument(text, mimetypes.guess_type(path.name)[0] or "text/plain", {"extension": path.suffix})


class DocxExtractor:
    def extract(self, path: Path) -> ExtractedDocument:
        paragraphs: list[str] = []
        with zipfile.ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                paragraphs.append(node.text)
        return ExtractedDocument("\n".join(paragraphs), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", {"extension": ".docx"})


class PdfExtractor:
    def extract(self, path: Path) -> ExtractedDocument:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            try:
                from PyPDF2 import PdfReader  # type: ignore
            except ImportError:
                return ExtractedDocument("", "application/pdf", {"extension": ".pdf"}, "pdf extractor not installed")
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return ExtractedDocument("\n".join(pages), "application/pdf", {"extension": ".pdf", "page_count": len(pages)})


class FutureMediaExtractor:
    def __init__(self, media_type: str) -> None:
        self.media_type = media_type

    def extract(self, path: Path) -> ExtractedDocument:
        return ExtractedDocument(
            "",
            mimetypes.guess_type(path.name)[0] or self.media_type,
            {"extension": path.suffix, "future_ready": True},
            f"{self.media_type} extraction not enabled locally",
        )


class DocumentExtractorFactory:
    """Factory for local file extractors."""

    def extractor_for(self, path: Path) -> DocumentExtractor:
        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            return PlainTextExtractor()
        if suffix == ".docx":
            return DocxExtractor()
        if suffix == ".pdf":
            return PdfExtractor()
        if suffix in IMAGE_SUFFIXES:
            return FutureMediaExtractor("image/ocr")
        if suffix in AUDIO_SUFFIXES:
            return FutureMediaExtractor("audio/transcription")
        if suffix in VIDEO_SUFFIXES:
            return FutureMediaExtractor("video/transcription")
        return FutureMediaExtractor("unsupported")


class IngestionPrivacyPolicy:
    """Reject secret-bearing paths and content before metadata is persisted."""

    def __init__(self, sanitizer: SecretSanitizer | None = None) -> None:
        self.sanitizer = sanitizer or SecretSanitizer()

    @staticmethod
    def blocked_path(path: Path) -> bool:
        name = path.name.lower()
        if name in BLOCKED_SECRET_NAMES or name.startswith(".env."):
            return True
        return path.suffix.lower() in BLOCKED_SECRET_SUFFIXES

    def blocked_content(self, text: str) -> bool:
        return bool(text) and self.sanitizer.sanitize(text) != text


class Chunker:
    """Character-window chunking with overlap."""

    def __init__(self, chunk_size: int, overlap: int) -> None:
        self.chunk_size = max(100, int(chunk_size))
        self.overlap = max(0, min(int(overlap), self.chunk_size // 2))

    def chunk(self, text: str) -> list[DocumentChunk]:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not cleaned:
            return []
        chunks: list[DocumentChunk] = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + self.chunk_size)
            chunks.append(DocumentChunk(cleaned[start:end], len(chunks), start, end))
            if end >= len(cleaned):
                break
            start = max(end - self.overlap, start + 1)
        return chunks


class DocumentIngestionService:
    """Ingest local documents into the RAG memory service."""

    def __init__(
        self,
        rag: RAGMemoryService,
        config: RAGConfig | None = None,
        extractor_factory: DocumentExtractorFactory | None = None,
        chunker: Chunker | None = None,
        privacy_policy: IngestionPrivacyPolicy | None = None,
    ) -> None:
        self.rag = rag
        self.config = config or rag.config
        self.extractor_factory = extractor_factory or DocumentExtractorFactory()
        self.chunker = chunker or Chunker(self.config.chunk_size_chars, self.config.chunk_overlap_chars)
        self.privacy_policy = privacy_policy or IngestionPrivacyPolicy()

    def ingest_file(self, path: Path) -> DocumentIngestionResult:
        source_path = Path(path)
        if self.privacy_policy.blocked_path(source_path):
            LOGGER.warning("Blocked sensitive document path from RAG ingestion: %s", source_path.name)
            return DocumentIngestionResult("", "[blocked sensitive path]", "", 0, 0, "blocked sensitive path")
        source_hash = _file_hash(source_path)
        document_id = f"doc:{source_hash[:24]}"
        extractor = self.extractor_factory.extractor_for(source_path)
        extracted = extractor.extract(source_path)
        if self.privacy_policy.blocked_content(extracted.text):
            LOGGER.warning("Blocked secret-bearing document content from RAG ingestion")
            return DocumentIngestionResult("", "[blocked secret-bearing document]", extracted.mime_type, 0, 0, "blocked secret-bearing content")
        metadata = {
            **extracted.metadata,
            "file_name": source_path.name,
            "file_size": source_path.stat().st_size,
            "source_hash": source_hash,
        }
        self.rag.repository.upsert_document(
            document_id=document_id,
            source_path=str(source_path),
            source_hash=source_hash,
            mime_type=extracted.mime_type,
            metadata=metadata,
            status="skipped" if extracted.skipped_reason else "indexed",
        )
        if extracted.skipped_reason:
            LOGGER.info("Skipped document ingestion for %s: %s", source_path, extracted.skipped_reason)
            return DocumentIngestionResult(document_id, str(source_path), extracted.mime_type, 0, 0, extracted.skipped_reason, metadata)

        chunks = self.chunker.chunk(extracted.text)
        indexed = 0
        for chunk in chunks:
            memory = self.rag.add_memory(
                chunk.text,
                category="document",
                source="document",
                source_id=f"{document_id}#chunk-{chunk.chunk_index}",
                source_uri=str(source_path),
                source_title=source_path.name,
                importance=0.55,
                confidence=0.82,
                metadata={**metadata, "chunk_index": chunk.chunk_index},
                provenance={"document_id": document_id, "start_char": chunk.start_char, "end_char": chunk.end_char},
            )
            if memory.id is not None:
                self.rag.repository.add_document_chunk(
                    document_id=document_id,
                    memory_id=memory.id,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    content_hash=self.rag.repository.content_hash(chunk.text),
                )
                indexed += 1
        return DocumentIngestionResult(document_id, str(source_path), extracted.mime_type, len(chunks), indexed, "", metadata)


class BackgroundIndexingQueue:
    """Simple background document indexing worker."""

    def __init__(self, ingestion: DocumentIngestionService) -> None:
        self.ingestion = ingestion
        self.queue: Queue[Path | None] = Queue()
        self.results: list[DocumentIngestionResult] = []
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="fibi-rag-indexer", daemon=True)
        self._thread.start()

    def enqueue(self, path: Path) -> None:
        self.start()
        self.queue.put(Path(path))

    def stop(self) -> None:
        self.queue.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while True:
            path = self.queue.get()
            if path is None:
                return
            try:
                self.results.append(self.ingestion.ingest_file(path))
            except Exception as error:  # pragma: no cover - defensive logging path
                LOGGER.exception("Background RAG indexing failed for %s: %s", path, error)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
