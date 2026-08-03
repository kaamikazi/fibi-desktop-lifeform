# Architecture Boundaries

These dependency rules keep user data and external effects behind explicit,
testable owners. They describe the target direction while compatibility paths
are retired in stages.

## Runtime Ownership

- `fibi.app.composition` constructs top-level services and owns their lifecycle.
- Pet and Control Center receive the same `ApplicationServices` instance.
- UI adapters call use cases; they do not open SQLite, write JSON records, or
  instantiate providers, memory repositories, action engines, STT, or TTS.
- `FibiCore` remains a compatibility orchestrator and should receive services
  rather than constructing second authorities.

## Memory Boundary

- Only the future authoritative `MemoryService` may create/update approved
  long-term memory.
- Notes, projects, conversations, companion state, permissions, task audits,
  and derived indexes each have separate owners.
- Provider adapters cannot import memory repositories or SQLite.
- Search indexes cannot write authoritative records or determine consent.
- UI cannot write raw memory rows; all mutation uses typed commands/results.
- Context Broker is the only path from approved memory to generation requests.
- Operational logs and companion inner-life data never become conversational
  memory merely because they are persistent.
- Secret-like paths and content are rejected before ingestion persistence.
- Deleted, expired, rejected, revoked, archived, or unapproved records cannot be
  returned as ordinary context.
- Stage 1 `MemoryQueryService` exposes no mutation operation and is constructed
  only by `fibi.app.composition`.
- Stage 1 adapters may read existing legacy/RAG storage but may not call
  ingestion, access-marking, update, delete, or index-rebuild methods.
- `ContextBrokerPreview` cannot import providers, RAG repositories, or SQLite;
  it receives already-normalized candidates and is disconnected by default.
- Companion state and operational audit owners cannot be registered as Stage 1
  memory sources.

`python tools/check_memory_boundaries.py` runs lightweight AST checks for the
enforceable import, construction, and mutation-call rules. Behavioral tests
cover policy, byte-stable reads, runtime identity, and retrieval rules.

## Provider Boundary

- Provider selection is manual and persisted by `ProviderSelectionService`.
- Provider adapters translate SDK requests/results only. They do not own Fibi's
  personality, memory policy, privacy policy, actions, or UI.
- Generation receives prepared text and approved normalized context, never
  repositories, API keys, database paths, embeddings, or service objects.
- Diagnostics retain IDs, categories, booleans, latency, and normalized errors,
  not prompts, responses, memory text, transcripts, or credentials.

## Desktop Effect Boundary

- All desktop actions pass through typed intent detection, permission policy,
  allowlists, confirmation where required, and the action engine.
- Model output cannot execute an effect directly.
- Tests inject process, browser, clipboard, filesystem, audio, and clock effects.

## Experimental Boundary

Wake word, RVC, semantic acceleration, and advanced workflows are optional and
must degrade without blocking supported startup. Sovereign Brain, Interpreter
Brain, autobiographical cognition, and similar cognitive systems are excluded
from the default runtime. Adding one requires a separate product decision and
ADR; it must consume approved interfaces rather than own user memory.

## Persistence Rules

- Runtime data stays under the configured data root and out of Git/releases.
- Schema changes are versioned, transactional, backup-aware, and reversible.
- Read-only diagnostics do not initialize missing stores or produce reports.
- Derived data is versioned and rebuildable from its authority.
- No UI success message may overstate cross-store deletion or migration.
