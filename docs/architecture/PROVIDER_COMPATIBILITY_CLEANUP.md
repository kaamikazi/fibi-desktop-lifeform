# Provider Compatibility Cleanup

This audit records the legacy provider surface reviewed against base commit
`74864536b0f1543196d79e58592dbc7b8e9d6dbf`. The migration preserves manual
Gemini/Ollama selection, explicit fallback policy, generation behavior, privacy
rules, and user-visible commands.

## Authoritative Ownership

| State or behavior | Owner |
|---|---|
| Registered provider IDs and normalized model metadata | `ProviderRegistry` |
| Manual selection, options, and persistence | `ProviderSelectionService` |
| Selected-provider generation, explicit fallback, tests, and isolated benchmarks | `CompanionGenerationService` |
| Selected/attempted/active provider, health, model, latency, retry, fallback, error, and grounding flags | `ProviderDiagnostics` |

The Pet and Control Center share these instances from `ApplicationRuntime`.
Prompts, replies, API keys, memory text, and provider SDK objects never enter
diagnostics or model metadata.

## Legacy Usage Inventory

| Call site | Classification | Previous behavior | Replacement / disposition | Risk and coverage |
|---|---|---|---|---|
| `fibi/app/composition.py:195` | Production runtime | Constructed `ModelRouter` before the provider subsystem and synchronized mode/fallback twice. | Keeps one facade for compatibility; the factory attaches the authoritative services. Duplicate synchronization removed. | Medium; composition identity, runtime lifecycle, GUI smoke. |
| `fibi/app/runtime.py:91` | Diagnostics | Verified the Pet/Core used the composition-owned legacy router. | Retained as an identity-only compatibility diagnostic beside registry, selection, generation, and diagnostics identity checks. | Low; runtime duplicate-service diagnostic. |
| `fibi/engines/core.py:332`, `fibi/engines/core.py:1305` | External/direct-constructor compatibility | Supported injected/replaced routers and rebuilt provider adapters. | Retained temporarily. Rebind delegates to the centralized factory and immediately attaches authoritative services. | Medium; old smoke suites and facade projection tests. |
| `fibi/engines/core.py:1248`, `fibi/engines/core.py:1575` | Command handling | Mixed service reads with Gemini fields, remote model discovery, legacy benchmark calls, and mirrored status. | Migrated to registry metadata, selection, generation, and diagnostics. | High; focused command, metadata, benchmark, privacy tests. |
| `fibi/engines/core.py:630`, `fibi/engines/core.py:1166` | Diagnostics | Read mutable `ModelRouter.last_*` fields and Gemini configuration directly. | Reads one `ProviderDiagnosticsSnapshot` and registry metadata. | High; diagnostics/facade identity tests. |
| `fibi/ui/fibi_window.py:672`, `fibi/ui/fibi_window.py:1718` | UI display | Read `model_router.selected_provider()` and `model_router.gemini.is_configured()`. | Reads Core projections backed by shared selection and registry services. | Medium; settings, Pet, and Control Center tests. |
| `fibi/services/providers/factory.py` result observer | Diagnostics | Copied every generation result into mutable router fields. | Removed. Diagnostics is written once by `CompanionGenerationService`; facade properties are read-only projections. | High; AST mirror guard and behavioral equality test. |
| `fibi/engines/model_router.py:143` | Test/external compatibility | Implemented a second complete provider/fallback path. | Deprecated forwarder to `CompanionGenerationService.generate`; unattached direct callers receive a non-persisting factory subsystem. | High; legacy route and policy regression suites. |
| `fibi/engines/model_router.py:204` | Test/external compatibility | Independently mutable status fields could drift from runtime services. | Read-only properties project the diagnostics snapshot. Bootstrap values exist only until factory attachment. | High; AST mutation guard and snapshot equality. |
| `fibi/engines/model_router.py` NVIDIA/generic-cloud constructor parameters | Obsolete experimental compatibility | Accepted old provider objects no longer present in production routing. | Retained as inert read-only constructor compatibility only; never registered or called. | Low now; removal tied to facade deletion. |
| `fibi/engines/__init__.py:32` | Public compatibility | Lazy public import for `ModelRouter`. | Retained for the deprecation window. | External import risk; import smoke remains required. |
| `tests/smoke_v009_hotfix.py`, `smoke_v010.py`, `smoke_v014_context.py`, `smoke_v0151_routing_tts.py`, `smoke_v0301_gemini_provider.py`, `smoke_v0304_provider_resilience.py` | Test compatibility | Construct or replace routers to isolate historical behavior. | Retained until those smoke fixtures inject provider services directly. | Medium; full suite required before deletion. |
| `tests/test_v0301_gemini_provider.py`, `test_v0303_routing_and_settings.py`, `test_v0304_provider_resilience.py`, `test_v0305_manual_quality.py`, `test_v0308_wake_memory.py`, `test_v0309_pet_shell.py` | Test compatibility | Assert legacy constructor, route, or projection behavior. | Behavioral coverage retained; authoritative tests added and obsolete health-probe expectation migrated. | Medium; full suite and deprecation warnings. |

No production UI or command handler now reads `model_router.gemini`,
`model_router.ollama`, adapter-private fields, or mutable router diagnostics.
No production generation call invokes `ModelRouter.route`.

## Command Consumer Flow

```text
FibiCore command parser
  -> ProviderSelectionService (status/use)
  -> ProviderRegistry (list/configured model/cached health)
  -> CompanionGenerationService (test/benchmark/context preview)
  -> ProviderDiagnostics (safe runtime status)
  -> local response presentation
```

`/provider test` uses only the selected provider, fallback disabled, no memory
or project context, and a neutral request. `/provider benchmark` explicitly
names Gemini and Ollama, uses normalized requests/results, does not update
conversation diagnostics, and cannot modify persisted selection. Ordinary
status never makes a provider request.

## Normalized Model Metadata

`ProviderModelMetadata` contains only provider/model IDs, display name,
configuration/availability booleans, Fibi capabilities, enabled capabilities,
configuration source, and a small allowlisted set of safe options. Gemini SDK
model objects and Ollama response structures cannot cross this boundary.
`/provider models` reports the explicitly configured model and never performs
remote discovery.

## ModelRouter Deprecation

The facade currently supports:

- old constructor injection used by historical tests;
- read-only `selected_provider`, fallback, and diagnostics projections;
- deprecated `route` and `context_preview` forwarding;
- Core's legacy replacement/rebind hook;
- the lazy `fibi.engines.ModelRouter` import.

It does not construct providers, discover models, implement fallback, persist
selection, inspect SDK errors, or own diagnostics. Deprecation warnings are
emitted for legacy generation and context-preview calls.

## Deletion Criteria

Delete `ModelRouter` only when all conditions are true:

1. `ApplicationServices` and runtime diagnostics no longer expose it.
2. `FibiCore` no longer accepts or detects router replacement.
3. Every listed smoke/unit fixture injects registry/selection/generation/
   diagnostics services directly.
4. The lazy `fibi.engines.ModelRouter` import has completed at least one public
   release of deprecation and downstream usage has been reviewed.
5. Full tests, GUI smoke, provider architecture guards, and release checks pass
   without the facade.

Earliest intended removal: Fibi 0.5.
