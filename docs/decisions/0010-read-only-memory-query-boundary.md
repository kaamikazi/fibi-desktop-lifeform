# ADR 0010: Read-Only Memory Query Boundary

- Status: accepted
- Date: 2026-08-03

## Context

Fibi has overlapping legacy and RAG memory reads while the final authoritative
SQLite ownership model is still blocked by backup, restore, consent,
conflict-resolution, and deletion requirements. Existing read methods also
update access metadata, so calling them would violate a read-only migration
stage.

## Decision

Introduce one runtime-owned `MemoryQueryService` with legacy and RAG read
adapters. The adapters reuse existing owners but query their SQLite files via
immutable, query-only connections. Results use an immutable normalized record
that preserves source IDs and bounded provenance.

Keep production retrieval unchanged. Add an off-by-default synthetic shadow
comparison and a disconnected, off-by-default Context Broker preview. Report
duplicate candidates but do not merge or discard them.

## Why No New Database

A normalized persistent store would imply authority and require a new write,
migration, consent, conflict, backup, and deletion lifecycle. None is approved
in Stage 1. The boundary is a projection only.

## Consequences

Future readers can depend on a storage-neutral contract, and architecture tests
can enforce source separation. Reads do not update access counters or caches.
The immutable SQLite snapshot is per request, so concurrently committed data is
observed on a later connection rather than mutating or locking the source.

Stage 1 does not improve current replies or retrieval because it is not wired
to provider context. Existing inconsistencies remain visible as separate source
records and failures.

## Rejected Alternatives

- Reusing current retrieve methods: rejected because they mutate access state
  or caches.
- Creating a canonical database now: rejected because it starts a write
  migration without safety prerequisites.
- Sending normalized candidates to providers: rejected because that is a
  production behavior change and belongs after Stage 2 validation.
- Silently merging duplicates: rejected because Stage 1 has no conflict or
  consent authority.

## Rollback

Remove the composition attachment and Stage 1 modules. Existing stores and
production retrieval remain untouched, so no data rollback is necessary.

## Stage 2 Criteria

Proceed only after source byte checks, privacy exclusions, provenance,
synthetic comparison stability, runtime identity, provider isolation, and the
full regression suite pass. Stage 2 must still be separately approved.
