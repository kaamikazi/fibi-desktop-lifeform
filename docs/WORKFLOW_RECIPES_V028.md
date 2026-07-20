# Fibi v0.28 Workflow Recipes

Workflow recipes are named, repeatable rituals that help Fibi guide work safely.
They are not automation scripts. A recipe can show steps, track progress, pause,
resume, export a summary, and point to existing commands.

Fibi still does not secretly run commands, apply patches, scrape websites, send
messages, upload files, or buy things.

## Commands

```text
/workflow list
/workflow show <name>
/workflow start <name>
/workflow current
/workflow next
/workflow continue
/workflow pause
/workflow resume
/workflow cancel
/workflow history
/workflow export last
/workflow safety
/recipes
```

Natural prompts show a recipe summary first:

```text
start debug workflow
guide me through release
do beta QA
help me review this website
make a bug report workflow
daily startup check
```

After the summary, start explicitly with:

```text
/workflow start <recipe name>
```

## Built-In Recipes

- Debug Failed Project
- Safe Release Build
- Beta QA Pass
- Website Review / Outreach Research
- Bug Report Support Bundle
- Daily Fibi Startup Check

## Safety Rules

Recipes are guidance only.

- Patch steps point to the existing patch confirmation flow.
- Check steps point to the existing check confirmation flow.
- Browser steps point to browser helper commands and never fetch pages silently.
- Release build steps require explicit local commands and confirmation.
- Outreach steps can draft text, but never send it.
- Exports exclude secrets, raw logs, full source, memory databases, and raw page text.

## Example Debug Workflow

```text
/workflow start Debug Failed Project
/workflow next
/workflow next
```

Fibi will guide you through the active project, last check output, likely files,
safe fix suggestion, patch confirmation, and check rerun suggestion.

## Example Release Workflow

```text
/workflow start Safe Release Build
/workflow next
```

The recipe points to self-test, checks, build zip, release verification,
checksums, artifact paths, and export summary. It does not run the build by
itself.

## Browser Outreach Workflow

```text
/workflow start Website Review / Outreach Research
```

Fibi can save a URL note, ask you to paste visible public page text, summarize
that text, identify visible pain points, draft an outreach message for review,
and save an approved browser research note.

No hidden browsing. No scraping. No sending.

## Stored Files

```text
data/workflows/workflow_state.json
data/workflows/workflow_runs.jsonl
data/reports/workflow_run_<id>.md
data/reports/workflow_run_<id>.json
```

When a workflow completes, Fibi stores only a short memory event such as:

```text
Completed Safe Release Build workflow for Fibi v0.28.
```

She does not store raw logs, full code, or raw browser page text as workflow
memory.
