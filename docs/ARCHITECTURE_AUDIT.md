# Fibi Companion Architecture Audit

Date: 2026-07-23

## Executive Summary

Fibi already has a usable Windows desktop-pet shell, manual Gemini/Ollama
selection, concise response enforcement, safe action confirmation, registered
project support, local memory review, push-to-talk, Edge TTS, diagnostics, and
substantial regression coverage. These are the product foundation.

The repository is not yet easy to maintain as an open-source product. The main
orchestrator (`fibi/engines/core.py`) is about 4,759 lines, the main UI module is
about 2,134 lines, and shared types are about 1,496 lines. Runtime assembly,
routing, command parsing, product behavior, persistence, and compatibility code
remain concentrated in `FibiCore`. Memory has legacy SQLite, memory-care,
structured extraction, and RAG paths active at once. Plugin support does not
exist. Windows assumptions are embedded in services rather than isolated behind
a platform boundary.

The recommended path is an incremental modular monolith: define service
contracts, add a composition root, move one capability at a time behind those
contracts, and retain compatibility adapters until callers migrate. Fibi 0.4
should be a reliable daily companion, not an intelligence research platform.

## Current Architecture Map

```text
app.py
  -> bootstrap dependency checks and logging
  -> fibi.main
      -> QApplication
      -> FibiPetWindow (default surface)
          -> lazily opens FibiWindow (Control Center)
          -> shared FibiCore + LifeEngine

FibiCore
  -> command/action/context/project/chat routers
  -> provider router -> Ollama / Gemini / legacy optional providers
  -> legacy MemoryEngine + MemoryCareEngine
  -> RAGMemoryServiceFacade -> SQLite + FAISS
  -> action intent + permission + confirmation + desktop execution
  -> project registry + scanner + reader + patch/check workflows
  -> voice settings + push-to-talk + TTS + optional RVC
  -> life/personality/ritual/opinion/inner-life systems
  -> settings, diagnostics, health, logging, and shutdown services
```

## Repository Responsibilities

| Path | Current responsibility | Assessment |
|---|---|---|
| `app.py`, `fibi/main.py`, `fibi/bootstrap.py` | Launch, dependency checks, Qt creation | Small and understandable; lifecycle assembly should move here. |
| `fibi/ui/` | Pet, full window, dialogs, avatar/expression rendering | Product surfaces work; main window module needs decomposition. |
| `fibi/engines/` | Nearly all policy, orchestration, persistence, actions, voice, projects | Largest source of coupling; split by stable service boundary gradually. |
| `fibi/providers/` | Gemini implementation and provider result/config types | Good direction; Ollama and other providers should use the same boundary. |
| `fibi/rag/` | SQLite/FAISS memory, ingestion, retrieval, evaluation | Technically separated but broader than required for default personal memory. |
| `fibi/voice/` | Edge synthesis/playback and compatibility listening | Keep infrastructure behind speech service contracts. |
| `fibi/control/` | Legacy direct app/browser/keyboard helpers | Unused and unsafe compared with active action services; deprecate. |
| `fibi/life/`, `fibi/brain/` | Compatibility personality/cleanup/screen helpers | Clarify supported pieces; pause speculative behavior. |
| `tests/` | 100 unit and versioned smoke modules | Broad regression safety; consolidate fixtures and add contract/platform layers. |
| `tools/`, `packaging/` | Build, release, migration, diagnostics | Useful but Windows/version hardcoded and not CI-backed. |
| `docs/` | Versioned feature, safety, QA, and RAG documentation | Rich history; needs current canonical docs and archive policy. |
| `config/`, `updates/` | Default settings and update metadata | Centralize schema/version ownership; updates remain unsigned/manual. |

There is no `plugins/`, public protocol package, CI configuration, or standard
Python project metadata (`pyproject.toml`) yet.

## What Works Reliably

- Root launcher, dependency diagnostics, runtime-path isolation, and GUI smoke.
- Tiny transparent Pet as the default surface and lazy Control Center reuse.
- Background model calls and TTS rather than blocking the Qt event loop.
- Manual Gemini/Ollama selection with explicit fallback configuration.
- Final response cleanup and hard concise-mode enforcement.
- Narrow action intent detection, allowlists, confirmations, and structured
  results for common Windows actions.
- Registered project roots, traversal checks, file-size/type limits, and secret
  sanitization.
- User-visible memory review and consent controls.
- Push-to-talk and Edge TTS as optional capabilities.
- Broad unit/smoke coverage with fake providers and fake action executors.
- Runtime data, databases, voice models, secrets, and build output ignored by
  Git and excluded by release verification.

## Partial Or Experimental Components

- Wake word: a continuous local runtime is under development but has not passed
  real microphone phrase validation. It must remain experimental and off.
- RVC: functional adapters and fallback exist, but latency, environment weight,
  backend variability, and model setup make it unsuitable as a default.
- RAG document ingestion: broad architecture exists, but personal-memory scale
  does not require FAISS for most users and mutation rebuilds remain costly.
- Workflows, patching, checks, browser research, inner life, dreams, opinions,
  habits, rituals, and relationship scoring have tests but collectively widen
  the product and maintenance surface beyond the 0.4 goal.
- Packaging is Windows-specific, version strings are repeated in tooling, and a
  clean-machine installation path is not continuously tested.

## Duplication

| Area | Duplicate paths | Consequence |
|---|---|---|
| Memory | `MemoryEngine`, `MemoryCareEngine`, `RAGMemoryServiceFacade`, `LegacyMemoryAdapter`, structured extraction | Reads/writes and deletion behavior are difficult to explain and migrate. |
| Providers | `ModelEngine`, `ModelRouter`, `brain/ai.py`, Gemini, NVIDIA, generic OpenAI-compatible code | Configuration, health, timeout, and fallback semantics are inconsistent. |
| UI state | Pet inherits the large window; dialogs, state transitions, and service calls live in one module | A Pet change risks the Control Center and vice versa. |
| Actions | Active safe action engine plus unused `fibi/control` and `setup_fibi.py` helpers | Old helpers include unrestricted process/keyboard behavior and confuse contributors. |
| Settings | JSON state, config JSON, module constants, environment variables, and multiple settings engines | There is no single precedence model or schema. |
| Documentation | Root architecture plus version-specific documents | Current behavior and historical behavior are easily confused. |

## Tight Coupling And Testability

- `FibiCore` constructs dozens of concrete services and also implements command
  handlers, routing policy, memory behavior, model context, and persistence.
- `FibiWindow` combines Pet-compatible widgets, Control Center dialogs, TTS,
  threading, wake state, tray behavior, actions, and settings.
- Several services import global runtime paths and create directories during
  construction, making pure unit tests harder.
- Provider and action injection exists in places, but there is no common service
  contract or composition-root policy.
- Thread ownership is distributed across warmup, ingestion, UI response, TTS,
  and voice code. A single lifecycle registry should own cancellation and join.
- Many broad smoke scripts duplicate setup fixtures and preserve historical API
  shapes, making architectural cleanup expensive.

## Fragility And Code Smells

- God classes/modules: `FibiCore`, `fibi_window.py`, and `engines/types.py`.
- Command routing uses long string/regex handlers and mutable orchestration
  fields, so route precedence is fragile.
- Broad exception handling often converts failures into cute text without a
  structured error category.
- Legacy compatibility is open-ended rather than governed by removal dates.
- `fibi/control/apps.py` can terminate processes and `fibi/control/keyboard.py`
  types globally; they are unused by the active safe action path and should be
  deprecated, then removed after a compatibility audit.
- Version and artifact names are hardcoded in packaging scripts.
- Optional dependencies are mixed into the main requirements file, increasing
  clean-install cost and failure surface.
- No static type-checking/lint configuration is enforced in CI.

## Performance Risks And Budgets

| Risk | Current concern | 0.4 budget |
|---|---|---|
| Startup | Core eagerly creates many services and RAG loads/reconciles FAISS | Pet visible under 3 seconds; defer nonessential services. |
| Idle | animation timers, idle checks, optional observation, and experimental workers | Below 1% average CPU on a typical laptop; no mic unless enabled. |
| UI | large module and cross-thread callbacks | Local interaction under 100 ms; no blocking I/O on Qt thread. |
| Providers | health/discovery/retry can multiply latency | One selected provider; bounded request; no silent switching. |
| Memory | FAISS startup/rebuild for small personal datasets | SQLite retrieval under 50 ms for 10k records. |
| TTS | Edge generation plus optional RVC conversion | Text immediate; Edge playback should begin within 2 seconds. |
| Shutdown | daemon threads can outlive service ownership | All owned workers signaled and joined within 2 seconds. |

## Security And Privacy Risks

- The active desktop action path is appropriately narrow, but unused legacy
  control helpers are unsafe public examples and should be marked deprecated.
- Plugin execution has no boundary because no plugin API or loader exists yet.
- Project registration trusts a root and stores previews; users need a clear
  rescan/revoke view and symlink policy.
- Browser notes may retain user-provided page excerpts; retention and deletion
  should be visible in the Control Center.
- API key loading is centralized enough for current providers, but contributor
  docs must consistently prohibit checked-in `.env` files and logs.
- The updater verifies metadata but is not a signed update channel. Automatic
  updates should stay disabled until signatures and rollback exist.
- Raw audio must remain memory-only and telemetry disabled by default.

## UX Problems

- The Pet/Control Center product split exists, but inheritance means the Pet
  still carries assumptions from the full window.
- Settings expose experimental and advanced systems near daily controls.
- Status and error copy can be cute before it is actionable.
- Commands are numerous and version-oriented, making discovery difficult.
- Memory behavior is hard to explain while two stores are active.
- Wake and RVC can look supported even when the local environment cannot pass a
  real health check.

## Open-Source Readiness Gaps

- No license: outside contributors cannot legally reuse or redistribute code.
  The maintainer must choose one; this audit does not choose it.
- No Code of Conduct before this audit, no issue/PR templates, no maintained
  changelog, and no CI workflow visible in the repository.
- Requirements are largely unpinned and optional capabilities are not split
  into extras.
- README is long, historical, and still leads with “digital lifeform” rather
  than a concise install/use path.
- Architecture docs describe many version layers but not a stable public API.
- No reproducible clean-Windows installation test or dependency lock.
- No plugin development guide because no safe plugin contract exists.

## Feature Decision Table

| Feature | Decision | Reason |
|---|---|---|
| Root startup and runtime paths | A: keep and stabilize | Required for every user. |
| Tiny Pet and Control Center | A | Correct product shape; split implementation ownership. |
| Text chat and concise pipeline | A | Primary daily value. |
| Manual Gemini/Ollama selection | A | Predictable and testable. |
| Safe app/folder/URL/project opening | A | Useful with narrow permissions. |
| Project registration/read/search | A | Valuable and bounded. |
| Memory viewer/editor/consent | A | Trust requires visibility. |
| Push-to-talk and Edge TTS | A | Optional and understandable. |
| SQLite personal memory | A | Sufficient at current scale. |
| FAISS semantic retrieval | B: keep but refactor | Optional optimization behind `MemoryService`. |
| Packaging and diagnostics | B | Needed, but hardcoded and Windows-only. |
| Wake word | C: pause/experimental | Real microphone validation is incomplete. |
| RVC | C | High latency and setup burden. |
| Advanced workflows/patch/check | C | Too broad for 0.4 daily companion. |
| Browser research automation | C | Keep manual URL/text helpers only. |
| Inner life, dreams, opinions, bond scoring | D: deprecate from active product plan | Adds cognitive framing and complexity without core utility. |
| NVIDIA/generic cloud providers | D | Not part of the supported two-provider release. |
| Legacy `fibi/control` helpers | D, then E | Unsafe and unused; remove after import audit. |
| Unrestricted shell/autonomous actions | E: remove/reject | Incompatible with product safety. |

## Recommended Target Architecture

Use an incremental modular monolith:

```text
app/            composition root, lifecycle, runtime
ui/             Pet, Control Center, dialogs, themes
core/           companion use cases, routes, responses, events
services/       provider, memory, speech, actions, projects
plugins/        versioned API, manifest validation, isolated loader
permissions/    capability grants and confirmation policy
diagnostics/    health snapshots and support bundles
platform/       Windows implementations; Linux/macOS stubs later
```

Do not move all files at once. Add contracts first, wrap existing engines, move
construction into a composition root, and migrate one route at a time. Existing
imports remain supported through adapters during a documented deprecation
window.

## Stable Interface Recommendations

```python
class LanguageProvider(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
    def health(self) -> ServiceHealth: ...
    def model_info(self) -> ModelInfo: ...
    def configuration_status(self) -> ConfigurationStatus: ...

class MemoryService(Protocol):
    def remember(self, request: RememberRequest) -> MemoryRecord: ...
    def recall(self, query: RecallQuery) -> list[MemoryMatch]: ...
    def update(self, request: UpdateMemoryRequest) -> MemoryRecord: ...
    def forget(self, memory_id: str) -> ForgetResult: ...
    def list(self, query: MemoryListQuery) -> list[MemoryRecord]: ...
    def consent_state(self) -> MemoryConsentState: ...

class SpeechToTextService(Protocol):
    def transcribe(self, audio: AudioBuffer, options: STTOptions) -> Transcript: ...
    def list_devices(self) -> list[AudioDevice]: ...
    def health(self) -> ServiceHealth: ...

class TextToSpeechService(Protocol):
    def speak(self, request: SpeechRequest) -> SpeechHandle: ...
    def stop(self, handle: SpeechHandle | None = None) -> None: ...
    def health(self) -> ServiceHealth: ...

class DesktopActionService(Protocol):
    def resolve(self, text: str) -> ActionRequest | None: ...
    def request_permission(self, action: ActionRequest) -> PermissionDecision: ...
    def execute(self, action: ApprovedAction) -> ActionResult: ...

class ProjectService(Protocol):
    def register(self, path: Path) -> Project: ...
    def list_files(self, project_id: str) -> list[ProjectFile]: ...
    def search(self, project_id: str, query: str) -> list[ProjectMatch]: ...
    def open_in_editor(self, project_id: str, editor: str) -> ActionResult: ...
```

Methods return structured results and stable error categories. UI copy is added
at the presentation layer, not inside services.

## Migration Order

1. Freeze 0.4 scope and mark wake/RVC/workflows experimental.
2. Introduce typed service protocols and a composition root without moving code.
3. Split Pet and Control Center presenters from shared widgets/services.
4. Consolidate provider configuration and remove automatic switching behavior.
5. Make one SQLite-backed memory service primary; adapt legacy callers.
6. Move Windows actions behind a platform adapter and delete unused controls.
7. Add plugin manifest validation only after service boundaries are stable.
8. Add clean-machine packaging CI, then consider Linux/macOS adapters.

## Immediate Engineering Task

Completed in the first 0.4 migration step: normal application startup now uses
the tested `fibi.app` composition root and one lifecycle-owned service graph.
Minimal protocols cover language providers, memory, desktop actions, projects,
STT, and TTS. `FibiCore` still supports its legacy constructor and still owns
several second-order routers and product policies; those are deliberate
remaining coupling points for incremental migration.

The next migration task is to extract provider selection and generation routing
behind a dedicated companion use case while preserving manual provider choice.
