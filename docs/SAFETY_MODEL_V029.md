# Fibi v0.29 Safety Model

Fibi is local-first and permission-first.

## Defaults

- Cloud model access is off by default.
- Clipboard observation is off by default.
- Screenshot actions are off by default.
- Voice input is off by default.
- Shutdown actions are off by default.
- Autonomous actions are off.
- Memory learning can be paused with `/memory learning off`.
- Sensitive memories require approval by default.

## Refusals

Fibi refuses:

- hidden browsing
- browser history/cookie/password access
- website scraping without provided text
- auto-clicking, auto-sending, auto-buying
- arbitrary terminal commands
- destructive file operations
- surprise uploads
- auto-applying patches
- exporting memory databases or full project source in support bundles
- storing passwords, API keys, tokens, private keys, recovery codes, raw private
  page text, or raw project secrets

## Confirmations

Confirmation is required for risky areas:

- browser URL opening
- patch apply
- project checks
- project file reads
- voice skin activation
- screenshots
- shutdown actions
- memory edits and deletes
- broad memory category deletes
- release/build-style steps

## Help Commands

```text
/safety
/privacy
/refusals
/confirmations
/permissions
/memory safety
/memory consent
```

These commands are read-only. They do not change settings.

Memory exports are local and exclude secrets, raw private page text, raw project
source, deleted memories, archived memories by default, and internal embeddings.
