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
- The packaged release folder passes static verification, but its `--gui-smoke`
  run exceeded the verifier's 30-second timeout in this environment; clean
  packaged-runtime validation remains outstanding.
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
- The current validation shell has no usable `pytest` installation and the
  bundled interpreter lacks `google.genai`; full pytest and provider-dependent
  Core smoke results therefore require the supported project environment.

## Release engineering

- CI and reproducible dependency pinning are still Milestone 4 work.
- The repository has no license-selection decision; maintainers must choose one
  explicitly before distribution.

## Confirmed baseline test failures (2026-10-14)

- `test_incomplete_bundle_and_symlink_artifact_are_rejected` expects
  `unsafe_link_or_reparse_point`, but the backup verifier returns
  `manifest_path_escape`. The unsafe bundle is rejected; error-category
  precedence needs a separate backup review.
- The v0.16 RVC smoke expects `last_rvc_error` to be populated by a missing
  backend availability check. The current implementation returns unavailable
  without populating that field. Resolve this in the optional voice subsystem.

Both failures reproduced on the committed baseline and on the native-action
publication snapshot. They were not hidden, skipped, or counted as passes.
