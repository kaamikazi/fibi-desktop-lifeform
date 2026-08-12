# ADR 0011: Content-Free Memory Comparison

- Status: accepted
- Date: 2026-08-13

## Context

Stage 1 introduced a read-only normalized projection over legacy and RAG
memory. The project needs evidence about overlap, ranking, metadata, lifecycle,
privacy, and source availability before considering a write migration. Normal
retrieval methods may mutate access state, and diagnostics must not leak user
content or create a new persistent store.

## Decision

Extend the Stage 1 shadow module with an explicitly enabled,
runtime-independent `MemoryComparisonService`. Compare query-only source
adapters and the normalized query service, use random per-call HMAC keys for
ephemeral exact matching, and return versioned aggregate reports only.

Do not construct comparison services in normal runtime composition. Provide a
fictional 20-case CLI suite and refuse local-data execution until all live
stores and auxiliary files can be proven byte-stable. Persist no report by
default.

## Consequences

Synthetic CI can characterize overlap, ranking, privacy exclusions, metadata
gaps, degraded indexes, timeout, and source failure without provider or user
data access. Comparison latency varies by environment. Synthetic conclusions
cannot establish the state or quality of real memory.

The temporary timeout worker bounds report waiting but cannot forcibly stop a
running native call. That limitation is a reason to block local-data mode, not
to weaken read-only guarantees.

## Rejected Alternatives

- Stable unsalted hashes: rejected because they permit cross-run correlation.
- Persisted comparison mappings: rejected because they create a sensitive new
  store.
- Startup or chat shadow reads: rejected because they alter normal behavior and
  can add latency or access side effects.
- Production retrieval methods: rejected because they may update access state.
- Automatic migration threshold: rejected because metrics require human and
  privacy review.
- Implementing local-data mode immediately: rejected because complete
  byte-stability and safe quiescence are not yet guaranteed.

## Rollback

Remove the comparison contracts, dataset, CLI, service extension, tests, and
documentation. Existing Stage 1 reads and all production memory behavior remain
unchanged; no data rollback is needed.

## Stage 3 Status

Blocked pending backup/restore, transactional import, conflict review, source
mapping, rollback, deletion consistency, consolidated consent semantics, and
separately approved private evidence.
