# Developing Fibi Companion

## Supported Development Environment

The current supported platform is Windows with Python 3.12. Cross-platform
contributions are welcome, but Linux and macOS behavior is not release-tested.

## Setup

```powershell
git clone <repository-url>
cd fibi-desktop-lifeform
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Copy the canonical [`.env.example`](../.env.example) to `.env` only when
configuring an optional cloud provider. Never commit `.env`, keys, tokens,
runtime data, logs, voice models, or user memory.

## Test Commands

```powershell
python -m compileall -q .
python -m pytest -q
python app.py --gui-smoke
python tools/verify_release.py --release-dir "dist/Fibi Chubi"
python tools/check_memory_boundaries.py
python tests/smoke_memory_stage1.py
python tests/smoke_memory_stage2.py
```

Tests must mock provider calls and destructive/visible desktop actions. Unit
tests must not require a microphone, network, paid API, browser session, or real
application launch.

## Code Organization

- Put product policy in core/use-case code, not widgets or providers.
- Return typed results and stable error categories from services.
- Inject external effects: clocks, processes, browsers, audio, filesystem, and
  provider clients.
- Keep the selected provider manual and deterministic.
- Route all desktop effects through permission and action services.
- Do not add permanent memory writes without consent and review behavior.
- Keep user-approved memory, user-created notes/projects, companion state,
  temporary context, audits, and derived indexes as separate data classes.
- Treat SQLite records as authoritative and FAISS/embeddings/caches as
  disposable derived data.
- Keep optional features import-safe when their dependency is absent.

## Adding A Language Provider

The provider API is experimental and currently versioned as
`0.4-experimental`. Implement the typed `LanguageProvider` protocol in
`fibi/services/providers/protocols.py`, give it a stable lowercase ID, normalize
all failures to `ProviderErrorCategory`, and register the adapter explicitly in
`fibi/services/providers/factory.py`. Do not add SDK types to Core or the UI.

Adapters receive a `GenerationRequest` containing prepared prompt text and
approved context only. They must never load or log secrets through diagnostics,
change provider selection, invoke desktop actions, or define Fibi's identity.
Use deterministic test doubles for provider tests; real Gemini and Ollama calls
are forbidden in the automated suite.

Provider status and UI code must use `ProviderRegistry` model metadata,
`ProviderSelectionService`, and `ProviderDiagnostics`. Status views must not
call `LanguageProvider.health()` because that may perform I/O; use the
registry's cached health snapshot. Provider comparisons must call
`CompanionGenerationService.benchmark`, which disables fallback, does not
record conversation diagnostics, and leaves persisted selection unchanged.

`ModelRouter` is compatibility-only. Do not add callers, fields, provider
construction, fallback branches, persistence, model discovery, or diagnostics
state to it. New tests should exercise normalized provider contracts unless
they specifically verify the documented facade behavior.

Manual selection and explicit fallback are separate settings. A failed request
must not mutate selection. New fallback categories require an ADR and tests for
privacy, visibility, and deterministic routing.

The normalized error categories are `not_configured`, `authentication_error`,
`quota_error`, `rate_limited`, `timeout`, `network_error`,
`temporary_unavailable`, `model_unavailable`, `invalid_request`,
`safety_block`, `empty_response`, `cancelled`, and
`provider_internal_error`. Adapter-specific error text must not escape this
boundary.

A minimal provider test double implements the five `LanguageProvider` members
and returns an immutable `GenerationResult`; inject it into a local
`ProviderRegistry`. Record calls on the double and assert provider IDs and
normalized result fields. Never monkeypatch a live SDK client or depend on a
developer's API key or running Ollama service.

## Change Workflow

1. Inspect existing behavior and dirty files.
2. Add or update focused tests.
3. Make the smallest compatible change.
4. Run focused tests, then the full suite and GUI smoke.
5. Review `git diff --check`, staged files, and a secret scan.
6. Document user-visible behavior and compatibility impact.

## Architecture Changes

Significant boundaries, persistence formats, permissions, provider behavior,
plugin APIs, and supported-platform decisions require an ADR in
`docs/decisions/`. Prefer compatibility adapters and staged migrations.

Memory changes must follow
[ADR 0009](decisions/0009-authoritative-user-controlled-memory.md) and the
[migration plan](architecture/MEMORY_MIGRATION_PLAN.md). Never run the legacy
RAG migration helper on real data. The currently supported audit command is a
read-only structural preflight:

```powershell
python -m fibi.tools.memory_migrate --dry-run
```

It prints counts and schemas only, does not initialize missing stores, and has
no apply mode. Memory tests use temporary directories and synthetic content.
They must not inspect a developer's `data/` directory.

Memory Stage 1 is documented in the
[read-boundary guide](architecture/MEMORY_STAGE_1_READ_BOUNDARY.md) and
[ADR 0010](decisions/0010-read-only-memory-query-boundary.md). New Stage 1
adapters must expose reads only, reuse an existing runtime owner, use immutable
query-only SQLite access, preserve source references, and emit content-free
failures. Run shadow comparison only through synthetic tests or:

```powershell
python tools/run_memory_shadow_fixture.py
```

Do not enable it at startup or point it at real user data.

Stage 2 comparison is explicit and synthetic-only:

```powershell
python -m fibi.tools.memory_compare --synthetic --no-save
```

The report goes to stdout and contains aggregates only. Local-data mode refuses
execution even with confirmation because complete live-store byte stability is
not yet guaranteed. Do not add a runtime hook, environment-triggered startup
path, report store, provider call, stable fingerprint, or automatic migration
decision. See [Stage 2 comparison](architecture/MEMORY_STAGE_2_COMPARISON.md),
[findings](architecture/MEMORY_STAGE_2_FINDINGS.md), and
[ADR 0011](decisions/0011-content-free-memory-comparison.md).

The backup foundation is explicit and private-output gated:

```powershell
python -m fibi.tools.memory_backup create --output <private-directory> --confirm-private-output
python -m fibi.tools.memory_backup verify <backup-bundle>
python -m fibi.tools.memory_backup rehearse-restore <backup-bundle> --confirm-private-output
```

Tests must construct synthetic SQLite databases beneath `tmp_path`; never run
these commands against a developer's real data. The subsystem must use
SQLite's backup API, verify untrusted manifests, omit derived indexes from
validity, and reject active/repository/bundle rehearsal destinations. There is
no live restore, automatic backup, retention, cloud transfer, or importer. See
[backup architecture](architecture/MEMORY_BACKUP_ARCHITECTURE.md),
[operations](operations/MEMORY_BACKUP_RECOVERY.md), and
[ADR 0012](decisions/0012-memory-backup-and-restore-rehearsal.md).

Before a future write migration can ship, it still needs one importer
transaction, source mapping, duplicate/conflict review, import-specific
fault-injected rollback tests, sanitized private evidence, coordinated deletion,
consent normalization, and explicit approval. Backup and restore rehearsal alone
do not authorize Stage 3.

Top-level dependencies are wired only in `fibi/app/composition.py`. Add a
minimal protocol in `fibi/app/contracts.py` when a consumer needs a replaceable
boundary, then add the concrete service to `ApplicationServices` and test its
identity and cleanup. Do not fetch services from globals or construct a second
provider, memory, action, project, STT, or TTS service in a UI adapter.

## Packaging

Windows packaging instructions live in `packaging/README.md`. Build output is
local and must not be committed. Release verification must reject `.env`, user
databases, logs, voice models, caches, and temporary audio.

## Optional Capabilities

RVC and wake word are experimental. Do not describe them as supported until the
target environment passes manual hardware tests. Edge TTS and push-to-talk are
the supported 0.4 voice direction.
