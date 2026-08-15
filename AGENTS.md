# Fibi Contributor Rules

Fibi is a local-first desktop companion. Read `docs/ARCHITECTURE.md`,
`docs/architecture/BOUNDARIES.md`, and the relevant ADRs before editing a
cross-cutting area.

- Work in bounded milestones and preserve unrelated dirty work.
- Keep provider selection, memory ownership, permissions, and personality
  boundaries intact. Do not silently redesign them.
- Keep UI thin, use the composition root for shared services, and avoid giant
  rewrites or new global service state.
- Treat SQLite authority, consent, deletion, exports, and derived indexes as
  separate concerns. Do not add memory writers or merge stores casually.
- Keep provider adapters independent of memory repositories and actions.
- Route desktop actions through existing allowlists and confirmations. Never
  bypass permissions or add unrestricted shell access.
- Backup creation, verification, and restore rehearsal are explicit CLI-only
  operations. Never implement live restore, import, startup backups, or cloud
  upload without a separately approved design.
- Never stage `.env`, databases, runtime data, exports, backups, caches, build
  output, private reports, or another contributor's protected work.
- Add focused synthetic tests for behavior and boundary tests for architecture.
  Run compile, relevant tests, full pytest, and GUI smoke when appropriate.
- Report exact commands and results. Surface architecture, security,
  data-integrity, or migration-policy conflicts instead of improvising around
  them.
