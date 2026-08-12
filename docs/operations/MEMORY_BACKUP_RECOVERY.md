# Memory Backup And Recovery Operations

## Supported Commands

Backups are explicit and local. Stop Fibi when practical for the clearest
operational boundary, although SQLite's online backup API supports an active
database.

```powershell
python -m fibi.tools.memory_backup create `
  --output "D:\Private Fibi Backups" `
  --confirm-private-output

python -m fibi.tools.memory_backup verify `
  "D:\Private Fibi Backups\fibi-memory-backup-..."

python -m fibi.tools.memory_backup inspect `
  "D:\Private Fibi Backups\fibi-memory-backup-..."

python -m fibi.tools.memory_backup rehearse-restore `
  "D:\Private Fibi Backups\fibi-memory-backup-..." `
  --confirm-private-output
```

Add `--full-integrity-check` when a slower full SQLite integrity pass is
appropriate. Rehearsal cleans its temporary copy by default. Supply an isolated
`--destination` plus `--keep` only when private manual inspection is intended.

## Output

Commands return one content-free JSON object. Successful creation reports the
backup ID, asset counts, integrity, and manifest validity. It does not echo the
private destination or memory contents. Record the destination separately.

## Failure Recovery

- `required_asset_missing`: confirm the configured data root and do not begin
  migration.
- `sqlite_unavailable_or_invalid` or `sqlite_integrity_failed`: preserve the
  source, stop write operations, and investigate storage health.
- `checksum_mismatch`, `asset_size_mismatch`, or structural mismatch: treat the
  bundle as untrusted; do not rehearse or migrate from it.
- `backup_incomplete`: do not rename or edit it into apparent validity. Create
  a new backup after resolving the underlying problem.
- destination/path/link errors: choose a local private directory outside the
  repository, active data root, and existing bundle.

No automatic upload, retention, pruning, overwrite, live restore, or importer
is available. Do not manually replace `fibi_memory.db` from a backup while Fibi
is running; live recovery requires a separately designed and approved process.

## Synthetic Validation

```powershell
python tests\smoke_memory_backup_restore.py
```

The smoke creates a fictional temporary SQLite database, backs it up, verifies
it, rehearses restoration, checks structural validity and source immutability,
then removes the temporary tree. It never opens the real Fibi database.

## Retention

Keep multiple known-good backups on local storage appropriate to the user's
privacy requirements. Fibi does not yet automate retention or deletion. Never
delete the only verified backup. A future policy must be user-controlled and
must account for exports, sensitive data, and deletion guarantees.
