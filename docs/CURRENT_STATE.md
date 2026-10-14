# Fibi Current State

Updated: 2026-10-14

Current release target: the reliable Fibi 0.4 companion path; the existing
v0.30 Build Week release tag remains unchanged.

Fibi is a local-first Windows desktop companion with a compact pet surface and
a separate Control Center. `FibiCore` is still the compatibility orchestrator,
while `fibi.app.composition` constructs one shared service graph for the Pet
and Control Center.

## Runtime boundaries

- Provider selection is manual. Ollama and Gemini adapters receive prepared
  prompts and cannot execute desktop actions.
- Approved long-term memory is owned by the existing SQLite/RAG services and
  protected by consent, sensitivity, and secret guards.
- Desktop effects use typed intents, `PermissionEngine`, allowlists,
  confirmation where required, and `DesktopActionEngine`.
- Wake word, RVC, workflows, and semantic acceleration remain optional and
  degrade without blocking normal startup.
- Backup creation and restore rehearsal remain explicit CLI-only operations.

## Native assistant path

The deterministic path is:

```text
user text -> ActionIntentDetector -> PermissionEngine
          -> confirmation (when required) -> DesktopActionEngine
          -> DesktopActionResult -> concise response / Pet status
```

Common app resolution is centralized in `AppIndexEngine`. Project file search,
notes, and supervised work sessions reuse `ProjectWorkspaceEngine` and
`WorkSessionEngine`; they do not create a second memory or project database.
See `docs/assistant/NATIVE_CAPABILITIES.md`.

## Supported model-independent actions

Fibi can deterministically open known applications and approved folders/files,
open registered project folders or registered projects in VS Code, open
allowlisted HTTP/HTTPS URLs, copy explicit non-secret text, adjust volume when
the optional keyboard dependency exists, answer local date/time questions,
search bounded safe files in registered projects, save/list explicit project
notes, and start/inspect/stop a supervised work session. Destructive effects,
unrestricted shell, private reads, installation, and autonomous interaction
remain blocked.

Native action results expose normalized status, permission state, stable error
codes/categories, safe metadata, and conservative reversibility. Core action
responses and journal targets redact private absolute paths. Project scanning
rejects link/reparse chains and is bounded by scan depth, file count, result
count, and timeout.

## Validation baseline

The isolated native-action publication snapshot passed 45 focused tests,
compileall, native smoke, GUI smoke (including shared runtime identity), and
memory-boundary checks. Full pytest reported 488 passed and two failures that
also reproduce on the unchanged committed baseline: the backup symlink error
category and the optional RVC missing-backend diagnostic. The maintainer
explicitly approved publication with those baseline failures documented.
See [native validation](assistant/NATIVE_VALIDATION.md) for commands and scope.

Protected wake-runtime and Control Center UI work remains local and outside
this publication. Provider and memory service contracts are unchanged.
Immediate work: resolve the two baseline failures, then continue runtime
boundary reduction and clean-machine native-action validation.
