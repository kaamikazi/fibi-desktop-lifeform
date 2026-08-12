# ADR 0012: Memory Backup And Restore Rehearsal

- Status: accepted
- Date: 2026-08-13

## Context

Memory Migration Stages 1 and 2 established read-only normalized views and
content-free comparison, but any future write migration remains unsafe without
a consistent backup, independent restoration proof, and rollback evidence.
Fibi's legacy, RAG, document, journal, preference, opinion, and inner-life
tables currently share one WAL-capable SQLite database. Vector indexes are
derived, while consent and deletion evidence live in optional support files.

## Decision

Add an explicit `fibi.memory_backup` subsystem. Protect the shared memory
database with SQLite's online backup API. Optionally copy declared consent and
deletion-support files with size/time stability and checksum verification.
Exclude derived indexes and all unrelated runtime files.

Create transparent directory bundles with a strict
`fibi.memory-backup.v1` manifest. Verify every bundle as untrusted input. Permit
restoration only into a guarded isolated rehearsal directory and write
content-free rollback evidence. Provide no live restore or migration importer.

Do not construct or run backup services during normal application startup.
Require explicit private-output confirmation for creation and rehearsal.

## Consequences

Fibi can now prove on synthetic databases that committed WAL state can be
captured consistently, a bundle can be independently verified, and protected
state can be reconstructed without touching the source. Backups remain private
copies that require user-managed storage and retention.

Directory finalization uses a same-parent rename after staging verification.
This is the strongest practical Windows behavior used here, but not a claim of
cross-volume transactional atomicity. Brief scanner locks receive a bounded
retry, and cleanup only removes directories proven to belong to the current
invocation. Fault tests cover interruption, disk failure, corruption,
malformed/tampered manifests, path abuse, cancellation, and restore failure.

## Rejected Alternatives

- Copy the live database with `shutil.copy`: rejected because WAL and active
  transactions can produce an inconsistent snapshot.
- Include FAISS/NumPy as required authority: rejected because indexes are
  disposable and may be stale.
- SQL dumps: rejected because they expose content and add conversion risk.
- ZIP/proprietary archive: rejected at this stage in favor of a transparent
  inspectable directory.
- Automatic startup/scheduled backups: rejected as a separate retention and
  product-policy decision.
- Live in-place restore: rejected until shutdown, replacement, validation,
  rollback, and user-confirmation semantics are independently approved.

## Rollback

Remove the backup package, CLI, tests, architecture checks, and documentation.
Normal memory behavior is unaffected because it never imports the subsystem.
Do not delete any backup bundle already created by a user.

## Stage 3 Status

Still blocked. Backup/rehearsal satisfies one prerequisite only. Transactional
import, conflict review, provenance mapping, consent normalization,
coordinated deletion, failed-import rollback, migration validation, private
evidence, and separate approval remain required.
