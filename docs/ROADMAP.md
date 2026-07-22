# Fibi Companion Roadmap

## Milestone 0: Foundation Freeze

Complexity: small. Establish product scope, architecture decisions, contributor
docs, experimental labels, and a documented test matrix. Do not add features.

## Milestone 1: Runtime Boundaries

Complexity: medium.

- Add a composition root and lifecycle-owned worker registry.
- Define provider, memory, speech, action, and project protocols.
- Wrap current engines with compatibility adapters.
- Split shared types by domain without breaking import aliases.
- Establish structured service errors and health snapshots.

Exit: `FibiCore` no longer constructs every concrete dependency.

## Milestone 2: Reliable 0.4 Product Path

Complexity: medium.

- Separate Pet and Control Center presenters.
- Keep text/model/TTS work off the UI thread.
- Make selected-provider behavior contract-tested.
- Consolidate common safe actions behind a Windows platform adapter.
- Make push-to-talk and Edge TTS the supported voice path.
- Label wake word, RVC, and workflows experimental.

Exit: supported daily flows pass clean-machine and GUI integration tests.

## Milestone 3: Trustworthy Memory

Complexity: medium-high.

- Make one SQLite repository authoritative.
- Limit permanent categories to facts, preferences, projects, and approved
  summaries.
- Migrate legacy records with dry-run, backup, and rollback support.
- Keep semantic retrieval optional and benchmarked against keyword retrieval.
- Remove legacy writes after two compatible releases.

Exit: one explainable CRUD/consent path powers chat and the memory viewer.

## Milestone 4: Open-Source Release Engineering

Complexity: medium.

- Maintainer selects a license.
- Add CI for compile, unit, GUI smoke, release-content, and clean install.
- Split required and optional dependencies; pin reproducible release inputs.
- Add issue/PR templates, changelog, release checklist, and support policy.
- Publish signed checksums; keep automatic updates off until signing exists.

Exit: another Windows machine can build and run the same release from docs.

## Milestone 5: Plugin Preview

Complexity: high.

- Implement manifest parser, compatibility checks, capability grants, and error
  isolation for developer-installed local plugins.
- Support commands, menu items, tools, and settings sections only.
- Do not ship a marketplace or remote installation.

Exit: a sample plugin works without importing internal engines.

## Milestone 6: Cross-Platform Preparation

Complexity: high.

- Move app discovery, launch, clipboard, autostart, notifications, and active
  window observation behind platform interfaces.
- Add Linux/macOS no-op or explicit-unavailable adapters first.
- Add platform CI before promising support.

## Deferred Research

Wake word hardening, RVC acceleration, broad browser automation, advanced
workflows, multimodal RAG, and elaborate “inner life” systems remain outside the
0.4 critical path. They advance only with measured user value and maintenance
capacity.
