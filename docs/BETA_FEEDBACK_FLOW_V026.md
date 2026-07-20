# Fibi v0.26 Beta Feedback Flow

Fibi keeps beta feedback local. She does not upload issues, logs, or support
bundles automatically.

## Quick Commands

- `/issue new <title | details>` saves a local issue.
- `/issue list` shows recent local issues.
- `/issue last` shows the newest issue.
- `/issue close <id>` closes an issue.
- `/issue reopen <id>` reopens an issue.
- `/issue export <id>` writes a safe Markdown issue export.
- `/issue export all` writes a JSON export of all issues.
- `/support bundle for issue <id>` creates a safe support bundle and links it.
- `/feedback new <note>` saves general beta feedback.
- `/feedback list` shows recent feedback.
- `/feedback export` writes a safe feedback JSON export.

Natural phrases like `report a bug`, `Fibi crashed`, `voice is broken`, and
`beta feedback` open or create the same local records.

## Where Files Go

- Issues: `data/issues/issues.jsonl`
- Feedback: `data/issues/feedback.jsonl`
- Exports and bundles: `data/reports/`

Packaged normal mode uses `%APPDATA%/Fibi Chubi/` instead of the source `data/`
folder. Portable mode uses `data/` beside the executable.

## Privacy Promise

Fibi never auto-sends reports. Support bundles exclude memory DBs, journal DBs,
project source, voice models, caches, `.env` files, raw dropped files, and
obvious secrets.

Send exported files manually only when you choose to.
