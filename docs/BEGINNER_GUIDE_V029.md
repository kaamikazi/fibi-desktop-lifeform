# Fibi v0.29 Beginner Guide

Fibi is a tiny desktop lifeform. Talk to her like a small sleepy roommate, or
use slash commands when you want exact tools.

## Start Fibi

Development:

```powershell
python app.py
```

Packaged beta:

```powershell
"dist\Fibi Chubi\Fibi Chubi.exe"
```

## Try First

```text
hi
/what can you do
/commands
/help search browser
/memories
/memory consent
/permissions
/safety
```

## Memory Review

In v0.30 and newer, use `/memories`, `/memory search <term>`, `/memory health`,
and `/memory learning off` to review or pause Fibi's local notebook.

## Useful Workflows

Sessions guide one task:

```text
/session start help me fix the project
/session next
```

Recipes guide repeatable rituals:

```text
/workflow list
/workflow start Safe Release Build
/workflow next
```

## Browser Help

Fibi does not read pages by herself. Paste visible page text, then use:

```text
/browser summarize
```

Open URLs only with confirmation:

```text
/browser open https://example.com
browser confirm
```

## Report A Bug

```text
/issue new title | what happened
/support bundle for issue <id>
```

Support bundles are local and exclude memory databases, project source, voice
models, caches, and obvious secrets.

## Safety Basics

Cloud is off by default. Clipboard, screenshots, voice input, shutdown, and
autonomous actions are off unless explicitly enabled. Risky work asks first.

Fibi refuses hidden browsing, browser secrets, auto-sending, auto-buying,
auto-applying patches, destructive commands, and surprise uploads.
