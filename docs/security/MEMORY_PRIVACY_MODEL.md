# Memory Privacy Model

Status: target policy with current-system findings. Migration is not complete.

## Assets And Trust Boundaries

Protected assets include approved memory text, conversation context, project and
browser context, notes, settings, relationship presentation state, consent
history, exports, backups, embeddings, and source/provenance identifiers.

Trust boundaries are:

1. user and local Fibi UI;
2. memory/context use cases;
3. local persistent stores and derived indexes;
4. project/browser/clipboard/microphone inputs;
5. selected model provider, which may be local Ollama or explicit Gemini;
6. local exports, support bundles, backups, logs, and update packages.

Providers, UI widgets, search indexes, and language-model output are never
trusted as memory-policy authorities.

## Threats

| Threat | Current exposure | Required control |
| --- | --- | --- |
| Credential or `.env` ingestion | Document ingestion previously accepted arbitrary supported files | Reject secret-like paths and content before hashing, metadata, chunking, or embedding |
| Unapproved context sent to a provider | RAG retrieval and provider-specific filtering differ | One Context Broker enforces consent and sensitivity before provider selection |
| Hidden copy after deletion | Legacy, RAG, journal, summaries, exports, and caches have separate lifecycles | Stable source mapping, coordinated deletion attestation, visible export/archive limits |
| Sensitive export | RAG export opt-in previously bypassed full policy | Prohibited never exports; sensitive requires explicit opt-in and approval |
| Private logs or diagnostics | Most current diagnostics are content-free; journal stores user text | Separate operational diagnostics from conversation storage and bound retention |
| Index disclosure/corruption | Embeddings and IDs are local but unencrypted; FAISS rebuild behavior is broad | Treat index as sensitive derived data, ignore from Git, version and rebuild from filtered authority |
| Provider or UI direct storage access | Current providers do not own repositories; Core constructs RAG directly | Enforce dependency boundaries and composition-owned services |
| Consent flag divergence | Consent and privacy-learning state can disagree | One authoritative memory policy state and audited transitions |
| Migration loss or leak | Existing migration dry run can create files/reports | New dry-run query-only; backup, transaction, sanitized report, rollback before apply |
| Startup failure | RAG construction can depend on FAISS | Chat starts with memory unavailable/degraded; no new store initialized during read-only inspection |

## Consent Model

Consent statuses are `candidate`, `approved`, `rejected`, and `revoked`.
Record lifecycle status is separate: `active`, `superseded`, `archived`,
`deleted`, or `expired`.

- Explicit `remember` or a user save can create approved normal memory after
  validation.
- An inferred item is only a visible candidate. It does not enter model context
  until approved.
- Rejection prevents persistence as long-term memory or records only minimal
  content-free audit metadata if required.
- Revocation immediately excludes the record from retrieval and starts the
  configured deletion lifecycle.
- Disabled memory creates no candidate and no approved record. Recent context,
  if separately enabled, remains bounded and is not relabeled as memory.
- Consent is enforced by local policy code and never delegated to Gemini,
  Ollama, model output, or an embedding score.

Sensitivity levels are `normal`, `sensitive`, `restricted`, and `prohibited`.
Ordinary context accepts only approved, active, normal records. Sensitive or
restricted handling requires explicit user action and provider-specific privacy
policy. Prohibited content is never stored or exported.

## Never Save Automatically

- passwords, API keys, authentication tokens, cookies, recovery codes;
- private keys, certificates, `.env` content, credential stores;
- payment or complete financial details;
- health, intimate, or highly sensitive information without explicit approval;
- complete private file contents or unrelated project source/secrets;
- raw browser pages, clipboard contents, microphone audio, or transcripts as a
  side effect;
- entire conversations indefinitely by default;
- operational logs, permission audits, diagnostics, or inner-life state as user
  memory.

## Ingestion Controls

`DocumentIngestionService` now applies `IngestionPrivacyPolicy` before any file
content is fingerprinted or metadata is persisted. Secret-like basenames,
extensions, and key/certificate formats are rejected. Supported text is then
checked with `SecretSanitizer`; if sanitization would change it, the whole
document is rejected rather than partially indexed.

Future ingestion must also enforce user-approved roots, file size and page
limits, symlink/canonical-path checks, supported MIME verification, archive-bomb
protection, OCR provenance, cancellation, and explicit deletion of all chunks
and index entries.

## Context And Provider Controls

The future Context Broker will return bounded, sanitized summaries and stable
record IDs. Stage 1 provides only an off-by-default preview that receives
already-normalized candidates and is disconnected from provider generation.
It does not access repositories or record usage. The production broker must
exclude candidates, rejected/revoked/deleted/expired/archived records,
sensitive records under ordinary policy, and all operational/companion-state
data. It records only safe metadata such as category, record ID, rank, exclusion
reason, provider ID, latency, and token/byte count.

Gemini and Ollama must receive the same approved logical context set for the
same request. Gemini remains opt-in and receives no database, embedding,
browser secret, project source, log, or raw file. Provider errors never cause a
silent provider change or broader context retry.

## Logs, Diagnostics, And Crash Reports

Allowed: event names, counts, stable non-secret IDs, categories, durations,
error categories, schema/index versions, and booleans.

Forbidden: memory text, prompts, responses, transcripts, clipboard/browser
content, credentials, absolute private paths, raw exception payloads containing
input, and reversible embedding dumps.

Tracebacks must be reviewed at boundaries because SDK or filesystem exceptions
can contain paths or request snippets. Support bundles and crash reports remain
local, explicit, sanitized, and user-reviewed before sharing.

Stage 2 memory comparison uses a random per-call HMAC key for exact matching.
The key, content, fingerprints, source record IDs, and raw query never enter the
report. Reports contain aggregate counts and normalized error categories only
and are not persisted automatically. The committed dataset is fictional and
privacy-scanned. Local-data comparison remains unimplemented.

## Exports And Backups

Exports are user-initiated and default to approved normal active records.
Prohibited content is excluded under every option. Sensitive export requires
explicit opt-in and approved state. Export files display creation time, scope,
and exclusions and are never uploaded automatically.

Before any future migration write, Fibi must create and verify a local backup.
The backup contains private data and must be excluded from Git, release output,
support bundles, and ordinary diagnostics. Restore must be rehearsed before
write cutover.

The explicit backup foundation uses SQLite's online backup API, a strict
content-free manifest, private-output confirmation, and isolated restore
rehearsal. Derived indexes are omitted. Bundles remain private independent
copies and are never uploaded, auto-pruned, restored over live data, or created
during startup. See [Backup Privacy Model](BACKUP_PRIVACY_MODEL.md).

## Deletion Guarantee

The target delete transaction marks the authoritative record deleted and writes
a content-free event. Retrieval filters status from the primary query before
ranking. Caches invalidate immediately. Derived FTS/vector entries are removed
or a rebuild is queued. An index failure cannot return the record because the
primary status remains authoritative.

The UI may claim complete deletion only after it reports disposition for:

- authoritative record and provenance history;
- derived index and cache;
- known legacy source mapping during migration;
- user-created exports/backups, which require separate user-visible handling;
- summaries or journals that independently contain the same content.

Current Fibi does not yet meet this cross-store guarantee. This is a migration
gate, not a documentation-only promise.

## Temporary Context And Retention

Recent conversation must be a separate bounded store with an explicit TTL and
maximum turns/bytes. Expiration should be enforced on read and periodically on
write/startup. It cannot silently become a long-term fact. A user-selected
summary is a new candidate/approved record with its own provenance.

Exports, journals, summaries, action logs, and migration diagnostics require
documented retention controls before write cutover. Companion configuration may
persist but should not retain raw `last_user_message` indefinitely.

## Storage Or Index Unavailable

- Memory write fails closed with a clear local message; it does not write an
  alternate shadow file.
- Retrieval returns no context plus a content-free degraded diagnostic.
- Chat, actions, voice, and provider selection continue where otherwise safe.
- Missing/corrupt FAISS falls back to SQLite retrieval and can be rebuilt.
- Read-only inventory never initializes a missing database or index.
- Stage 1 reads use immutable query-only SQLite snapshots and do not update
  access counters, caches, WAL files, or derived indexes.
- Recovery requires explicit user action when corruption or migration conflict
  could affect data.

## Security Acceptance Tests

- Secret-looking paths and content produce no document, chunk, hash, or vector.
- Provider and UI architecture guards pass.
- Candidate/sensitive/deleted records are ineligible for ordinary context.
- Sensitive export requires approval and opt-in; prohibited content never
  exports.
- Dry run leaves database bytes and file inventory unchanged and emits no
  content.
- Synthetic deletion cannot be retrieved with or without semantic acceleration.
- Provider replacement changes no stored record.
- Runtime starts safely when optional semantic indexing is unavailable.
