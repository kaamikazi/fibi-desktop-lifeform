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

## Codex Cloud baseline (2026-10-14)

The cloud run used Linux x86_64 and Python 3.12.14 in a project-local virtual
environment. The backup category and RVC diagnostic failures are fixed with
focused regression coverage. The backup suite passed 50 tests; voice tests
passed 7; native action reliability passed 17; memory boundary checks passed
16; provider architecture checks passed 16. The broader native regression
batch passed 44 tests and failed only on the Linux project-workspace assertion
described below. Compileall, native assistant smoke, synthetic backup
rehearsal, boundary scanner, and offscreen GUI smoke also passed. The release
verifier could not complete because this source clone has no packaged
`dist/Fibi Chubi/Fibi Chubi.exe` release folder.

To reproduce the supported setup in this Linux image, create `.venv` with
Python 3.12, install the declared requirements with `/usr/bin/gcc` available
for the `pocketsphinx` source build, then install pytest and run:

```sh
python3.12 -m venv .venv
PIP_CACHE_DIR=/tmp/fibi-pip-cache CC=/usr/bin/gcc .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install pytest
FIBI_DATA_DIR=/tmp/fibi-cloud-pytest-data .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen FIBI_DATA_DIR=/tmp/fibi-cloud-gui-data .venv/bin/python app.py --gui-smoke
```

Full pytest first reported 497 passed and two failures: the native project
workspace test's Windows-backslash traversal assertion, and one occurrence of
the v0.12 pending-confirmation assertion. These initial findings were followed
up in the bounded continuation below. Two later full-suite runs reported
498 passed and only the project-workspace assertion. Instrumentation during a
later full run showed confirmation state written with a 30-second expiry,
preserved by the subsequent health-state write, and returned by
`pending()`; it did not reproduce or identify the first occurrence's cause.
The Linux project-workspace test constructs a Windows-style backslash path,
which Linux treats as a filename. The continuation below addresses portable
path parsing and diagnoses the confirmation race; this cloud run does not
validate Windows packaging or hardware behavior.

Protected wake-runtime and Control Center UI work remains local and outside
this publication. Provider and memory service contracts are unchanged.

## Bounded cloud continuation (2026-10-14)

Project reads now parse untrusted paths with both Windows and POSIX separator
rules before joining them to the approved root. POSIX and Windows parent
traversal, mixed separators, absolute paths, drive-relative paths, rooted
paths, and UNC paths are rejected before `FileReaderEngine` is called. Safe
internal Windows separators normalize to the scanned forward-slash entry;
reparse-point checks and canonical containment remain in place. The focused
path contract and existing v0.15 smoke passed 13 tests, including a reader spy
for rejected paths and safe in-bundle reads. The host test does not replace a
packaged Windows run. No out-of-bundle read was demonstrated on the original
Linux test path; the defect was inconsistent cross-platform path validation
and error behavior, while canonical containment and reparse checks remain the
read boundary.

The earlier v0.12 pending-confirmation miss is now reproducible: Fibi's
asynchronous startup warmup could call `LifeEngine.save_state()` after a
confirmation had been persisted. That method writes its startup snapshot and
removed the pending action. The `state_save` warmup task was redundant because
startup already persists synchronously in `_mark_running()`, so it has been
removed. A deferred warmup regression creates the pending action before
releasing persistence checks, then verifies the pending action survives,
confirmation is consumed once, and the destructive shutdown executor is not
called. The four focused regression modules passed 17 tests in both original
and reversed order; the v0.12 test passed in five fresh pytest processes.

Confirmation behavior itself remains unchanged: created and expiry timestamps
persist at second precision, the integer 30-second lifetime remains 30 seconds,
and the existing strict `now > expires_at` rule accepts the exact deadline.
Separate synthetic evidence confirms that other `LifeEngine.save_state()`
paths still use a cached shared-state snapshot and can delete a pending
confirmation or restore one after cancellation. Only the redundant warmup
writer was removed; shared state ownership remains a known runtime-lifecycle
debt. An Astra read-only review classified the remaining shared-state
lifecycle issue as blocking for a full cloud regression-ready claim. Synthetic
review evidence showed that a later `LifeEngine.set_repetition_state({})` save
can delete a pending confirmation, and that a stale `LifeEngine` instance can
restore its pending snapshot after `ActionConfirmationEngine.cancel()`. The
warmup race is fixed, but shared-state writer ownership needs a separately
scoped coordinated mutation design; a naive read-merge change would retain its
own delete/restore hazards.

Continuation validation on Linux x86_64 / Python 3.12.14 / PyQt6 6.11.0:
the full suite passed twice at 514 tests with 10 warnings per run. The expanded
native/action batch passed 60 tests, backup 50, voice 7 (two standard-library
audio deprecation warnings), memory boundary 16, and provider architecture 16.
Compileall, native assistant smoke, synthetic backup rehearsal, boundary
scanner, and offscreen GUI smoke passed. GUI smoke printed
`RUNTIME_SERVICES_OK` and `GUI_SMOKE_OK`; it only constructs the UI/runtime and
checks service identity, without opening a microphone or making provider
requests. Ignored runtime files created by the commands were removed. These
results do not validate Windows packaging or hardware behavior.

Immediate work: design coordinated ownership/mutation for shared runtime
state with explicit delete/consume semantics, then rerun the confirmation
lifecycle tests and clean-machine Windows validation.
