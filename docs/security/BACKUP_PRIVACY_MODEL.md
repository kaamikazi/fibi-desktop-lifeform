# Backup Privacy Model

Memory backups contain private user data even though CLI output and manifests
are content-free. Treat every bundle and retained rehearsal as sensitive local
material.

## Allowed Public Metadata

- backup format and evidence schema versions;
- random backup ID and UTC creation time;
- Fibi version;
- logical asset IDs and safe `data/...` labels;
- classification, strategy, required/optional status;
- artifact-relative paths inside the bundle;
- sizes, SHA-256 checksums, SQLite `user_version`, schema fingerprints, and
  table-name sets;
- integrity, manifest, cancellation, and normalized error status.

## Forbidden Output

- memory rows or text, conversation/journal values, preferences, project names;
- usernames, home folders, absolute paths, database names supplied by users;
- environment values, credentials, cookies, keys, tokens, prompts, provider
  context, embeddings, or raw exceptions;
- backup contents in logs, support bundles, telemetry, network requests, or
  release artifacts.

CLI result models deliberately exclude bundle paths. The user supplies or
chooses the private destination, while routine output reports only status and
an opaque backup ID. Logs contain operation names, aggregate counts, and
normalized categories only.

## Destination And Trust

Creation requires `--confirm-private-output`. The default lives beneath the
ignored runtime data root in `private_memory_backups`; explicit destinations
inside the repository are rejected unless they are that dedicated ignored
runtime subtree. Existing directories are not overwritten.

Bundles are untrusted when read. Verification rejects malformed or unsupported
manifests, duplicate IDs/paths, traversal, absolute paths, sensitive path names,
symlinks/junctions/reparse points, unexpected files, missing assets, checksum or
size mismatch, invalid SQLite, and structural mismatch.

## Copies And Deletion

A backup is an independent private copy. Deleting a live memory cannot silently
delete retained backups. Fibi must not claim complete erasure without explaining
backup/export disposition. This task adds no rotation or automatic deletion,
because Fibi must never delete the user's only backup by policy accident.

Future retention controls require explicit product design, user visibility,
minimum-backup safeguards, deletion attestation, and separate approval. Cloud
backup, synchronization, upload, and support-bundle inclusion are prohibited.
