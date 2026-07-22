# Fibi Companion Architecture

This document describes the intended maintainable product architecture. The
current detailed audit is in [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md).
Historical implementation detail remains in the root `ARCHITECTURE.md` until
compatibility migration is complete.

## Runtime Shape

Fibi is a modular desktop application, not an autonomous agent platform.

```mermaid
flowchart TD
    Launcher["app.py / bootstrap"] --> Runtime["Application runtime"]
    Runtime --> Pet["Fibi Pet"]
    Runtime --> Center["Control Center"]
    Pet --> Companion["Companion use cases"]
    Center --> Companion
    Companion --> Generation["CompanionGenerationService"]
    Generation --> Selection["ProviderSelectionService"]
    Generation --> Registry["ProviderRegistry"]
    Registry --> Gemini["Gemini adapter"]
    Registry --> Ollama["Ollama adapter"]
    Companion --> Memory["MemoryService"]
    Companion --> Speech["Speech services"]
    Companion --> Actions["DesktopActionService"]
    Companion --> Projects["ProjectService"]
    Actions --> Permissions["Permissions"]
    Actions --> Platform["Platform adapter"]
```

## Ownership Rules

- `app`: constructs services and owns startup/shutdown.
- `ui`: renders state and emits user intents; it does not implement business
  policy or directly open files/processes.
- `core`: coordinates use cases, routing, responses, and application events.
- `services`: implements provider, memory, speech, action, and project contracts.
- `permissions`: classifies capabilities and confirmation requirements.
- `diagnostics`: reports health without exposing private payloads.
- `platform`: contains OS-specific integration.
- `plugins`: validates and hosts capability-limited extensions.

## Current Compatibility Map

| Target boundary | Current implementation |
|---|---|
| App/runtime | `app.py`, `bootstrap.py`, `main.py`, `FibiCore.__init__` |
| Pet | `ui/fibi_pet_window.py` plus inherited `FibiWindow` behavior |
| Control Center | dialogs and window behavior in `ui/fibi_window.py` |
| Companion/router | `engines/core.py`, `engines/routers/` |
| Providers | `services/providers/` with compatibility adapters over `model_engine.py` and `providers/gemini_provider.py` |
| Memory | `memory_engine.py`, `memory_care_engine.py`, `rag/` |
| Speech | `speech_recognition_engine.py`, `voice/`, wake/RVC engines |
| Actions | action intent, permission, confirmation, app index, desktop action engines |
| Projects | project workspace/scanner/file reader/edit/check engines |
| Platform | currently embedded in action, app-index, observation, and autostart engines |

## Dependency Direction

UI depends on core contracts. Core depends on service protocols. Concrete
services depend on repositories and platform adapters. Infrastructure must not
import UI. Provider output never executes actions directly. Model text is data,
not authority.

## Lifecycle

`fibi.app.composition` is the application composition root. It resolves runtime
paths and the optional environment file once, constructs an explicit
`ApplicationServices` graph, and injects that graph into `FibiCore`.
`ApplicationRuntime` owns the graph and provides idempotent `start()` and
`shutdown()` operations. The Pet receives its core from this runtime, and the
Control Center opened by the Pet reuses the same core. GUI smoke verifies the
provider registry, memory, TTS, action, project, and STT identities.

## Provider Boundary

`fibi.services.providers` is the experimental 0.4 provider API. Core prepares a
`GenerationRequest`; the generation service resolves the manually selected
provider, calls its adapter, and returns a normalized `GenerationResult`.
Provider adapters own SDK-specific translation only. They do not own Fibi's
personality, memory policy, privacy policy, routing, or UI.

Provider IDs are stable lowercase strings: `gemini` and `ollama`. Selection is
persisted by `ProviderSelectionService` and never changes because generation
failed. Automatic fallback is disabled by default. When the user explicitly
enables fallback, only eligible temporary failures may use the configured
fallback, the response says which provider answered, and the selected provider
remains unchanged.

The request contains prepared text and already-approved context summaries; it
never contains API keys or service objects. `ProviderDiagnostics` retains only
safe metadata such as IDs, model, latency, retry count, error category, and
fallback/search flags. Prompts and responses are deliberately not retained.

`ModelRouter` remains a compatibility facade while old status views and tests
are migrated. New generation code must depend on the provider service rather
than calling that router directly.

The existing UI submission worker remains responsible for executing
`FibiCore.respond` away from the Qt thread and suppressing stale results. The
provider subsystem is synchronous by design and creates no executor per
request; runtime shutdown therefore continues to own the established worker
lifecycle.

Feature workers remain opt-in. Wake-word work must not start unless the saved
setting enables it. Core shutdown currently closes legacy resources; the
runtime guards that call so it occurs once and also performs best-effort cleanup
after partial construction.

## Composition Guidance

Contributors adding a top-level service should define only the small structural
protocol its consumers need, construct the concrete adapter in
`fibi/app/composition.py`, add it as a typed `ApplicationServices` field, and
cover identity and cleanup behavior. Do not introduce a global service locator:
hidden dependencies and process-wide state make tests and lifecycle behavior
unpredictable. A DI framework was also rejected because this graph is explicit,
small enough to wire in Python, and should remain approachable to contributors.

Direct `FibiCore(...)` construction remains supported as a compatibility path.
It will be narrowed gradually as each capability moves behind a tested service
boundary; the core is not being split in one high-risk rewrite.

## Data And Privacy

- Writable data lives under the configured runtime-data directory.
- SQLite is the authoritative store for supported personal memory.
- Secrets come from explicit environment/config loading and are never logged.
- Raw audio is not retained.
- No telemetry is sent by default.
- Project and plugin access is capability-limited and user-approved.

## Migration Strategy

1. Add protocols in a stable public package.
2. Introduce a composition root that constructs existing engines.
3. Add adapters and contract tests around current implementations.
4. Move route handlers out of `FibiCore` by product capability.
5. Split Pet/Control Center presenters while sharing services.
6. Consolidate memory and provider paths.
7. Introduce platform adapters.
8. Remove deprecated imports only after a documented compatibility window.

No big-bang directory move is planned.
