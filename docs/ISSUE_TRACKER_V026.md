# Fibi v0.26 Local Issue Tracker

The issue tracker is a local JSONL store for beta testing.

## Issue Fields

Each issue records:

- `issue_id`
- timestamps
- app version/build mode
- packaged/dev mode
- category
- severity
- title and description
- reproduction/expected/actual placeholders
- status
- tags
- linked support bundle path
- last route summary
- health snapshot summary

Categories include `crash`, `gui`, `voice`, `rvc`, `memory`, `project`,
`patch`, `check`, `session`, `packaging`, `performance`, and `other`.

Severity is `low`, `medium`, `high`, or `critical`.

Status is `open`, `investigating`, `fixed`, `wontfix`, or `closed`.

## Exporting

`/issue export <id>` writes Markdown under `data/reports/`.

`/support bundle for issue <id>` writes a masked zip support bundle and includes
`issue_metadata.json`. It still excludes private databases, source files, voice
models, caches, and secrets.
