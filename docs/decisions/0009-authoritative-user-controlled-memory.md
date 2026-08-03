# ADR 0009: Authoritative User-Controlled Memory

Status: accepted for staged implementation

## Context

Fibi currently has legacy memories, conversations, journals, summaries,
preferences, project affinity, inner-life state, RAG memories, temporary RAG
turns, project notes, exports, and a FAISS index. Some facts are dual-written;
others are derived or retained under different policies. Memory Viewer and
legacy notebook operations do not address every copy. Provider paths also
receive different logical memory context.

This fragmentation makes deletion, consent, retrieval quality, migration, and
contributor ownership difficult to reason about. A desktop companion needs
continuity, but it does not need an experimental cognitive architecture.

## Decision

Adopt one future authoritative `MemoryService` backed by transparent,
migration-safe SQLite for user-approved facts, preferences, project memories,
and selected summaries.

Keep these categories outside that service:

- notes, reminders, projects, and work sessions remain user-created information
  with their own owners;
- voice/theme/personality presentation and bounded relationship state remain
  companion configuration/state;
- recent conversation remains bounded temporary context;
- consent, permissions, actions, and diagnostics remain operational records;
- FTS, embeddings, FAISS, manifests, and caches remain disposable indexes.

The consent states are candidate, approved, rejected, and revoked. Sensitive
content requires explicit approval; prohibited secret material is rejected.
Ordinary model context includes only approved, active, normal-sensitivity
records.

A narrow Context Broker retrieves and filters memory, applies a hard budget and
secret sanitization, and passes one normalized logical context set to the
generation service. Providers never access memory repositories or define
consent. Gemini and Ollama differ only in transport formatting and explicit
provider privacy eligibility.

SQLite metadata/FTS, keywords, recency, importance, and category filtering are
the supported baseline. FAISS remains an optional secondary acceleration index
that references authoritative IDs and can be deleted/rebuilt without data loss.

Migration proceeds through inventory, read adapters, dual-read comparison,
controlled import, write cutover, optional index rebuild, and delayed legacy
retirement. Backups, transactions, source mapping, checksums, conflicts,
rollback, and user confirmation are mandatory before writes.

## Data-Loss Prevention

- No destructive in-place conversion or silent database merge.
- Legacy stores remain untouched through import and a release rollback window.
- Every import preserves source identity and validates counts/checksums.
- Ambiguous duplicates and contradictions become reviewable conflicts.
- Primary record deletion precedes derived-index invalidation; an index cannot
  override primary status.
- The UI cannot claim complete deletion while known mapped copies remain.

## Rejected Alternatives

- Make FAISS authoritative: rejected because vectors are opaque, model/version
  dependent, and difficult to edit, export, migrate, or delete reliably.
- Keep independent legacy and RAG authorities: rejected because dual writes and
  partial deletion remain unavoidable.
- Put all state in one generic memory table: rejected because user facts,
  configuration, temporary context, and audits have different consent and
  retention rules.
- Let each provider retrieve memory: rejected because privacy and behavior would
  vary by selected model.
- Automatically retain every conversation: rejected as unnecessary and
  inconsistent with explicit, understandable memory.
- Big-bang rewrite/migration: rejected due data-loss and compatibility risk.
- Begin Sovereign Brain or autobiographical cognition work: rejected as outside
  Fibi Companion 0.4 scope.

## Consequences

Users gain a coherent future model for review, consent, context, export, and
deletion. Providers and indexes become replaceable. Contributors get explicit
ownership and migration gates.

During migration, compatibility adapters and comparison tests add temporary
complexity. Legacy behavior remains until each stage passes. Some present risks,
including cross-store deletion and consent divergence, are documented but not
silently changed in this audit.

## Testing Expectations

- Synthetic inventory and migration dry run make no writes and reveal no text.
- Ownership checks reject provider/UI/index storage bypasses.
- Consent, sensitivity, disabled-memory, duplicate, contradiction, expiry,
  deletion, and unavailable-storage behavior have contract tests.
- Retrieval evaluation includes positive and negative relevance labels,
  Recall@K, MRR, Precision@K, latency, and false-positive reporting.
- Provider test doubles receive identical approved logical context IDs.
- Import requires backup, transaction rollback, idempotency, conflict, checksum,
  and restore tests before apply mode exists.

## Compatibility And Stability

The target API is `0.4-experimental`. This ADR authorizes staged boundaries and
read-only prototypes, not a current write cutover. Existing commands, viewer,
stores, and FAISS remain in place until their migration gates pass. A later ADR
is required before declaring the API stable or retiring legacy data.
