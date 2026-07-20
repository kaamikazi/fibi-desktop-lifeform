# Privacy

Fibi is a local-first desktop companion. Runtime memory, logs, settings, reports, voice cache, and generated local data are intended to stay on the user's machine by default.

## Memory

The user owns Fibi's notebook. Memories can be reviewed, searched, edited, deleted, paused, and exported through the memory review controls.

Secrets, passwords, API keys, raw private browser text, and project secrets should not be stored as memories.

## Cloud and Providers

Cloud providers are disabled by default. If a user configures a provider, only the context explicitly sent through that configured provider flow should leave the machine.

Users must review third-party provider policies separately before enabling external services.

Gemini is optional and must be explicitly selected. Fibi sends one sanitized
language prompt containing the current message, short personality instructions,
and at most two approved non-sensitive memory summaries when the user has
enabled memory hints. Raw databases, embeddings, browser secrets, project files,
logs, reports, clipboard contents, and credentials are excluded.

Use `/provider context` before enabling Gemini. See
`docs/CLOUD_CONTEXT_PRIVACY_V0301.md`.

## Telemetry

Fibi does not include telemetry by default.

## Support Bundles

Generated support bundles are designed to exclude private databases and mask secrets where possible. Users should still inspect any report before sharing it.

Provider reports expose only whether `GEMINI_API_KEY` is configured. They never
include the key, its prefix/suffix, `.env`, or raw provider prompts.
