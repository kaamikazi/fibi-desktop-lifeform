# Fibi RAG Developer Guide

Fibi's RAG stack is local-first and split by responsibility:

- `RAGMemoryRepository`: SQLite metadata, document rows, chunk rows, events.
- `EmbeddingProvider`: local text-to-vector strategies.
- `FAISSVectorStore`: persisted vector index, id map, version manifest.
- `QueryRewriter`: deterministic local query expansion.
- `RetrievalCache`: short-lived in-process retrieval cache.
- `DocumentIngestionService`: file extraction, chunking, memory creation.
- `BackgroundIndexingQueue`: non-blocking document indexing worker.
- `evaluation.py` and `eval/benchmark.py`: local quality/performance checks.

## Supported Ingestion

Native:

- `.txt`
- `.md`
- `.markdown`
- `.docx`

Optional local dependencies:

- `.pdf` via `pypdf` or `PyPDF2` if installed.

Future-ready placeholders:

- images for OCR
- audio for transcription
- video for transcription

Placeholders record metadata and skipped reasons. They do not fake extraction.

## Retrieval

Retrieval combines:

1. Local query rewriting.
2. FAISS vector search.
3. SQLite lexical search.
4. Hybrid weighted ranking.
5. Source/provenance labels.
6. Cache storage for repeated queries.

Tune weights in `RAGConfig`:

- `hybrid_vector_weight`
- `hybrid_keyword_weight`
- `similarity_threshold`
- `default_top_k`

## NeMo Retriever Boundary

Use NeMo Retriever when a local `retriever` CLI/service is installed and the
task is multimodal document-corpus retrieval. Fibi's built-in RAG is for local
personal memories and lightweight document chunks. Do not claim NeMo usage
unless the CLI/service is actually invoked.

## Evaluation

The local eval layout follows NVIDIA `rag-eval` shape:

```text
eval/
  corpus/
  train.json
  benchmark.py
```

Run:

```powershell
python eval\benchmark.py --dataset eval
```

Metrics:

- Recall@K
- MRR
- Precision@K
- mean/p95 latency
- embedding benchmark time
- retrieval benchmark time
- false-positive count
- failure list

## Health

Call `RAGMemoryService.health()` to verify:

- database path
- vector index path
- active memories
- vector count
- cache entries
- embedding backend
- index version
- warnings
