# ADR 0003: Prefer Simple User-Owned Memory

Status: accepted

## Context

Fibi currently has legacy SQLite memory, memory-care commands, structured
extraction, RAG/FAISS, journals, patterns, preferences, opinions, dreams, and
relationship state. Users need understandable recall, not a cognitive model.

## Decision

The supported memory model contains user facts, preferences, projects, and
approved discussion summaries in one authoritative SQLite repository. Records
are visible, editable, deletable, exportable, and consent-aware. Keyword and
metadata retrieval is baseline; semantic retrieval is optional.

## Alternatives Considered

- Make FAISS/RAG mandatory: rejected for current personal-memory scale and
  operational complexity.
- Save every conversation: rejected for privacy and retrieval quality.
- Keep all cognitive stores active: rejected as difficult to explain and test.

## Consequences

Some ambient personality features lose automatic context. Trust, predictable
deletion, and maintainability improve.

## Migration Impact

Choose one schema, dry-run legacy migration, back up before applying, expose
counts/conflicts, and retain a read adapter for a documented release window.

## Testing Impact

Contract tests cover CRUD, consent, duplicate handling, export, deletion, and
retrieval ranking. Migration tests prove idempotence and rollback safety.
