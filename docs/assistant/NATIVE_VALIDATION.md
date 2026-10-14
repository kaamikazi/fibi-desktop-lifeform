# Native Action Publication Validation

Date: 2026-10-14 (Asia/Dhaka)

Base: `31a0d369a8ab6fdb32999a6064677cc7cac6859e`.

Validation used a separate snapshot made from committed HEAD plus only the
native-action, project-tool, test, and documentation changes. Protected
wake-runtime changes and Control Center UI changes were excluded, including
their hunks in shared Core/types files. Runtime test files and snapshots remain
ignored and are not part of the publication.

## Executed checks

Environment: Windows, Python 3.10.11, pytest 9.1.1.

| Command | Result |
| --- | --- |
| `python -m compileall -q fibi tests tools eval app.py` | Passed |
| `python -m pytest -q tests/test_native_action_reliability.py tests/test_v012_actions.py tests/test_v0307_concise_app_discovery.py tests/test_v015_project_workspace.py tests/test_v021_work_sessions.py` | 45 passed |
| `python -m pytest -q` | 488 passed, 2 failed, 8 warnings; 72.06 seconds |
| `python tests/smoke_native_assistant.py` | Passed with injected effects and temporary synthetic assets |
| `python app.py --gui-smoke` | `RUNTIME_SERVICES_OK`, `GUI_SMOKE_OK` |
| `python tools/check_memory_boundaries.py` | `MEMORY_BOUNDARIES_OK` |
| `python tools/verify_release.py` | Existing release-folder content check passed; this does not rebuild or validate a new binary |
| `git diff --check` | Passed |

The restricted sandbox initially prevented a SQLite backup test from writing
its temporary files. The full suite and GUI smoke were then run outside that
sandbox. No production database, real clipboard, real application, external
website, or live model provider was used by the native-action tests.

## Baseline failures

The following were also run against an unchanged snapshot of the base commit:

```text
python -m pytest -q tests/test_memory_backup_verifier.py::test_incomplete_bundle_and_symlink_artifact_are_rejected tests/test_v016_voice_skin.py
```

Both failed in that baseline run:

1. Unsafe backup symlink rejection returns `manifest_path_escape`, while the
   test expects `unsafe_link_or_reparse_point`. The verifier rejects the bundle.
2. Missing RVC backend detection returns unavailable without setting
   `last_rvc_error`, which the historical smoke test expects.

The maintainer explicitly approved publishing the scoped native-action changes
with these failures documented. No backup or RVC source was changed to suppress
the failures.

## Publication boundary

Excluded: `.env`, databases, indexes, private runtime data, audio/cache,
screenshots, builds, exports, backup bundles, the publication report, and
protected wake/UI work. A scoped credential-pattern and forbidden-artifact
scan found no credentials or private artifacts in the candidate files.

Only `main` is published with a normal push. Existing release tags are retained.
