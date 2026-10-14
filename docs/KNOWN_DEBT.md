# Known Debt

This list is intentionally short and current. It is not a new roadmap or a
second source of architectural authority.

## Native actions

- `FibiCore` still owns compatibility routing and constructs some legacy
  engines when used outside the composition root. The shared composition path
  is the supported runtime; further constructor reduction belongs to Milestone
  1.
- Windows launch, Start Menu shortcut resolution, clipboard, and media keys
  still use platform adapters embedded in legacy-compatible engines. Extracting
  a platform port is planned for cross-platform preparation.
- Native file search currently operates on the current registered project and
  scanned safe previews. It is deliberately not a whole-disk index; a future
  iteration can add an explicit approved-folder search surface without
  changing the current ownership boundary.
- Native notes are explicit project notes with recent-list support, but there
  is no dedicated edit/delete notes UI yet. They remain separate from
  long-term memory; project-note compatibility behavior should be reviewed
  again when the legacy project commands are retired.
- Clean-machine Windows validation is still needed for Start Menu shortcut
  target resolution, default-app opening, VS Code launch, and reparse-point
  behavior. Automated coverage uses injected effects and temporary roots.
- The cloud source clone did not include `dist/Fibi Chubi/Fibi Chubi.exe`, so
  release verification and clean packaged-runtime validation remain
  outstanding.
- Action results now have stable status and error-code fields, but the journal
  still stores its existing summary string. A future migration can persist
  structured result metadata without changing the current journal owner.

## Product architecture

- The legacy memory writer and the authoritative memory/RAG read boundary
  coexist during the documented migration foundation. Stage 3 remains blocked;
  migration, backup, and rollback policy are not silently inferred.
- Wake word, RVC, and optional advanced workflows need more clean-machine and
  device-matrix validation before they become default capabilities.
- GUI integration tests depend on installed PyQt6 and a display/offscreen Qt
  setup. Headless compile and pure engine tests remain available without Qt.
- Windows-only filesystem behavior, including native junction/reparse-point
  handling still needs a Windows run. Project file reads now parse Windows and
  POSIX separators consistently on every host, with focused traversal,
  containment, symlink, and no-outside-read regression tests; the Linux tests
  do not validate packaged Windows behavior.
- `fibi_state.json` still has multiple engines sharing the same JSON document.
  `LifeEngine.save_state()` writes a cached snapshot, so a later save can
  remove an independently persisted pending confirmation, and a stale save
  from an earlier `LifeEngine` can restore one after cancellation. The
  redundant asynchronous warmup state-save was removed after a deterministic
  race reproduction; other shared-state writer paths remain unresolved. Do not
  treat the warmup fix as a full state-ownership repair. Astra's synthetic
  review reproduced deletion with `create pending ->
  LifeEngine.set_repetition_state({})`, and resurrection with `create pending
  -> construct second LifeEngine -> cancel -> second LifeEngine.save_state()`.
  A restored pending confirmation can be consumed again before its expiry if
  the exact phrase is supplied, although existing permission checks still
  block destructive shutdown execution. Coordinated mutation and delete
  semantics need a separately scoped design; a naive read-merge is not safe.

## Release engineering

- CI and reproducible dependency pinning are still Milestone 4 work.
- The repository has no license-selection decision; maintainers must choose one
  explicitly before distribution.

## Cloud regression validation (2026-10-14)

- Fixed backup artifact link classification before canonical path resolution.
  Regression tests cover file links, linked ancestors, containment, ordinary
  artifacts, and a hash spy that proves an outside target is not read.
- Fixed unavailable RVC backend diagnostics and stale-error clearing, with
  tests for missing interpreter/package, safe probe failure, and available
  backend. Base voice fallback remains synthetic in tests.
- The first full cloud pytest run reported 497 passed and two failed. The
  v0.12 confirmation assertion passed in two subsequent full runs; instrumented
  state writes showed the pending action persisted and remained unexpired, but
  did not explain the first failure. Keep this occurrence unresolved until it
  is diagnosed.
- `test_v015_project_workspace` fails on Linux because it asserts that a
  hardcoded Windows backslash path is traversal. It needs a Windows validation
  run or a separately scoped cross-platform test correction.

Full-suite evidence: first run 497 passed / 2 failed; later runs 498 passed /
1 failed (the Linux/Windows-path mismatch). No failures were skipped or altered.
