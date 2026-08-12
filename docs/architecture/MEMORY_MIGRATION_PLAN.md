# Memory Migration Plan

Status: Stage 2 synthetic comparison implemented. Real data migration remains blocked.

## Safety Principles

- Dry run is the default and prints only paths relative to `data/`, schemas,
  counts, classifications, and blockers.
- No write stage begins without a verified point-in-time backup and restore
  rehearsal.
- Legacy sources remain untouched through import and a documented rollback
  window.
- Every imported row has a source store, source table, source ID, checksum, and
  migration run ID.
- Content, prompts, secrets, and private paths never enter default reports.
- Primary SQLite transactions commit before derived index changes.
- Any ambiguity becomes a conflict for user review, not a silent merge.

The safe command available now is:

```powershell
python -m fibi.tools.memory_migrate --dry-run
```

It is a Stage 0 structural preflight only. `--apply` is intentionally rejected.
The older `tools/migrate_legacy_memory_to_rag.py` must not be used on real data:
its nominal dry run constructs services that may initialize schema/index files
and it always writes a report.

## Stage 0: Inventory And Backup Design

**Entry:** Current application and data location identified; Fibi is stopped for
any future backup operation.

**Work:** Run the read-only inventory, enumerate schemas/counts, create synthetic
fixtures, document backup targets and expected checksums. Future backup code
must copy SQLite with the SQLite backup API, then copy state/index/export files
to a timestamped local directory outside the live data root.

**Exit:** Every known store is classified; backup manifest and restore rehearsal
specification are reviewed; no source content was changed.

**Tests:** Missing paths, Windows paths with spaces, query-only SQLite, no report
content, no created files, apply rejection.

**Validation:** File inventory before/after is equal; database hash is unchanged.

**Rollback:** None required because no writes occur.

**User impact:** None.

**Failure:** Return a sanitized blocker and do not initialize missing stores.

## Stage 1: Normalized Read Model

**Entry:** ADR 0009 accepted; target schema and `MemoryService` read protocol are
reviewed.

**Work:** Inject one read-only service through the composition root. Add legacy
and RAG adapters that normalize into target records without writing them. Add a
synthetic-only shadow comparison and a disconnected Context Broker preview;
both default off.

**Exit:** Core, Memory Viewer, and commands can be characterized through the
read contract; production writes remain unchanged.

**Tests:** Contract tests for category/status/consent/provenance, provider
independence, unavailable storage, and shared runtime identity.

**Validation:** Synthetic byte-stability, privacy, provenance, runtime identity,
and architecture checks pass; no provider or UI imports a repository. Real
source reconciliation is deliberately deferred because Stage 1 does not inspect
or print production user memory.

**Rollback:** Remove the composition attachment and adapter modules. No data
rollback is needed.

**User impact:** None unless an opt-in diagnostic comparison is displayed.

**Failure:** Continue current reads and report content-free diagnostics.

## Stage 2: Dual-Read Comparison

**Entry:** Stage 1 contracts stable; synthetic quality suite passes.

**Work:** Explicitly execute query-only source and normalized retrieval over a
fictional 20-case dataset. Match exact content with ephemeral salted HMACs and
record aggregate distributions, overlap, ranking, exclusions, metadata gaps,
latency, and normalized errors. Never record memory text in diagnostics.

**Exit:** Synthetic overlap, retention, contradiction, irrelevant retrieval,
sensitive/lifecycle exclusion, unavailable-index, source failure, timeout, and
byte-stability tests pass. Local-data evidence is still absent.

**Tests:** Exact fact, preference, project, contradiction, duplicate, irrelevant,
sensitive, deleted, no-index, and provider replacement cases.

**Validation:** No comparison is constructed during normal runtime; no provider
receives comparison context; temporary databases, indexes, manifests, access
counters, timestamps, and file inventory remain unchanged.

**Rollback:** Turn off comparison. Existing path remains authoritative.

**User impact:** None.

**Failure:** Do not progress. Reports are not persisted by default.

## Stage 3: Controlled Import

**Entry:** Backup and restore rehearsal passed; importer has dry-run, conflict
report, transaction, fault injection, and rollback tests; user explicitly
confirms the migration.

**Work:** Stop writes, acquire a migration lock, verify source checksums, create
the backup, import into new versioned tables in one transaction, preserve source
mapping, classify duplicates/conflicts, and verify counts/checksums. Originals
remain untouched.

**Exit:** Imported plus duplicate plus conflict plus excluded counts reconcile
exactly to eligible source counts; no prohibited content exists; user can review
conflicts and restore the backup.

**Tests:** Backup required, duplicate handling, conflict reporting, interrupted
transaction rollback, disk-full simulation, idempotent rerun, sanitized report,
and schema-version compatibility.

**Validation:** Independent read-only verifier compares source mappings,
checksums, status, and provenance. Optional index remains off.

**Rollback:** Drop only the unactivated versioned target tables after verification
or restore the complete backup. Never alter source stores.

**User impact:** Explicit maintenance dialog and migration summary.

**Failure:** Roll back the transaction, preserve sources/backup, mark run failed,
and keep current application path.

## Stage 4: Write Cutover

**Entry:** Stage 3 verified; conflict policy completed; delete/export/viewer
operations work against target records; rollback release tested.

**Work:** Enable the authoritative service as the only writer for new approved
memory. Mark legacy stores read-only. Stop automatic compatibility dual writes.
Temporary conversation and companion state remain in their own services.

**Exit:** Every write has one stable ID and provenance event; commands and UI
resolve the same record; deletion attestation covers primary and derived copies.

**Tests:** Concurrent writes, disabled memory, explicit consent, sensitive
approval, contradiction, edit/delete/export, restart, unavailable storage, and
old-version rollback behavior.

**Validation:** Runtime telemetry is local and content-free; no legacy row count
changes during target writes.

**Rollback:** Switch reads/writes to the compatibility adapter only under the
documented version gate; preserve target records for forward recovery.

**User impact:** One normalized Memory Viewer and command identity, with release
notes explaining the migration.

**Failure:** Fail closed for memory writes while chat continues without memory.

## Stage 5: Optional Index Rebuild

**Entry:** Authoritative records stable; metadata/FTS retrieval quality baseline
recorded; semantic benefit is measurable.

**Work:** Build a versioned FAISS index from approved active normal records only.
Use a temporary path, validate IDs/counts/manifest, then replace atomically.

**Exit:** Index can be deleted and rebuilt without record loss; unavailable or
corrupt index falls back to deterministic SQLite retrieval.

**Tests:** Missing dependency, incompatible dimension/version, corrupt files,
incremental events, delete/update/expiry, restart, and rebuild interruption.

**Validation:** Quality and latency benchmark compared against no-index baseline.

**Rollback:** Delete/quarantine derived index and disable semantic acceleration.

**User impact:** Optional setting/health status only; no change to memory data.

**Failure:** Degraded search, never failed startup or lost memory.

## Stage 6: Legacy Retirement

**Entry:** At least one public migration release and rollback window completed;
backup/export restored successfully; no unresolved conflicts; user confirms.

**Work:** Remove runtime reads from legacy tables. Keep a documented archive or
user-controlled export. Physical removal requires a separate migration and ADR.

**Exit:** Source code, commands, UI, docs, and tests have one authority. Legacy
data disposition is visible and reversible according to policy.

**Tests:** Upgrade from every supported legacy version, downgrade/restore,
fresh install, deleted-memory absence, packaging, and release-content scan.

**Validation:** Independent counts/checksums, index consistency, export import,
and user-visible deletion report.

**Rollback:** Restore backup and previous compatible release within the stated
window.

**User impact:** Explicit release notice; no silent deletion.

**Failure:** Keep legacy archives and compatibility reader. Do not retire.

## Future Migration Report Schema

Reports may contain only:

- tool/schema version and migration run ID;
- relative source identifiers and table names;
- source/imported/duplicate/conflict/excluded counts;
- content checksums that cannot reconstruct content;
- backup manifest path relative to the chosen backup root;
- transaction result, index status, and sanitized error categories;
- start/end timestamps and validation status.

Reports must not contain memory text, absolute user paths, credentials, prompts,
browser content, raw logs, or provider responses.

## Exact Next Phase

Keep Stage 3 blocked. The next product task is a separately reviewed backup and
restore subsystem with SQLite backup API coverage, manifest verification,
restore rehearsal, fault injection, private-output policy, and no importer.
Do not import, rewrite, merge, approve, delete, or retire records.
