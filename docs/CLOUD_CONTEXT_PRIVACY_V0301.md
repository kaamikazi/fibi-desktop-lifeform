# Cloud Context Privacy (v0.30.1)

Gemini receives a prepared language prompt, not Fibi's local runtime.

## Included

- the current user message, sanitized and length-limited
- short local Fibi personality instructions
- current mood
- a coarse time-of-day label when allowed
- at most two approved, non-sensitive memory summaries only when the user has
  selected the `memory_hint` cloud context level

## Excluded

- the raw SQLite memory database
- FAISS indexes and embeddings
- unapproved or sensitive memories
- full conversation archives
- browser history, cookies, passwords, and private page text
- clipboard contents and screenshots
- project source files and project trees
- `.env`, credentials, keys, and authorization headers
- logs, reports, support bundles, and issue attachments
- workflow execution authority, permissions, and action confirmations

The provider cannot write memories, approve memories, change permissions, run
actions, apply patches, browse, or confirm workflows. Those remain local.

## Preview

Use:

```text
/provider context
/provider privacy
/provider context preview on
/provider context preview off
```

The preview shows categories and counts. It does not echo full memory text,
prompts, credentials, or private files.

The first successful `/provider use gemini` selection shows the preview before
ordinary Gemini chat routing begins.

## Logging and Reports

Cloud prompts and full responses are not written to provider logs. Errors are
reduced to safe categories. Support bundles contain only:

```text
GEMINI_API_KEY_CONFIGURED=true/false
```

They do not include `.env`, a key prefix/suffix, raw provider requests, or raw
provider responses. Users should still inspect every support bundle before
sharing it.
