# ADR 0008: Extract Provider Selection And Generation

Status: accepted

## Context

`FibiCore` and `ModelRouter` jointly owned manual selection, SDK calls,
fallback, health fields, user-facing errors, and diagnostics. That coupling made
provider behavior difficult to test without constructing Core and made it easy
for new call sites to bypass privacy or silently change providers.

## Decision

Introduce a typed provider subsystem under `fibi.services.providers`:

- `ProviderRegistry` owns the controlled set of stable provider IDs.
- `ProviderSelectionService` owns persisted, manual selection.
- `CompanionGenerationService` owns one generation attempt and explicit-only
  fallback policy.
- Gemini and Ollama adapters translate existing clients into one
  `LanguageProvider` protocol.
- `ProviderDiagnostics` stores content-free operational metadata.
- `ProviderErrorPresenter` maps a closed error taxonomy to safe messages.

Core still owns prompt preparation, personality, memory approval, privacy,
routing, response cleanup, and presentation. It delegates only provider choice
and text generation. The composition root creates one provider subsystem shared
by the Pet and Control Center.

Provider diagnostics subscribe to manual selection changes, so safe status
metadata reflects the current configured choice even before the next model
request. This synchronization records IDs and configuration booleans only.

## Manual Selection And Fallback

Generation always begins with the manually selected provider. A failure never
changes that selection. Automatic fallback is off by default. If the user
explicitly enables it, fallback is limited to timeout, network, temporary
availability, and internal provider failures; authentication, quota, safety,
invalid request, model, cancellation, and configuration errors do not fall
back. Successful fallback is visible in the returned text and diagnostics.

## Privacy Boundary

Core passes only the current user text, a prepared prompt, and approved context
summaries. Each request includes the provider IDs allowed by current privacy
settings. Diagnostics retain no prompt, response, transcript, memory content,
or credential. Provider adapters do not execute actions.

## Compatibility

`ModelRouter` remains temporarily as an adapter source and mirrored status
facade. Direct `FibiCore` construction and tests that replace `model_router`
trigger a compatibility rebind. New production generation paths must use
`CompanionGenerationService`; removal of the facade requires a later migration.

The contract version is `0.4-experimental`. It is internal, not yet available
to plugins, and may change before a stable provider extension API.

## Alternatives Considered

- Keep expanding `ModelRouter`: rejected because selection, generation, policy,
  and diagnostics remain inseparable.
- Put provider selection in the UI: rejected because Pet, Control Center, and
  commands must share one authoritative state.
- Silent automatic failover: rejected because destination, privacy, cost, and
  latency would become unpredictable.
- Replace existing provider clients: rejected as a high-risk rewrite with no
  user value for this migration.

## Consequences

Provider behavior has small typed contracts, deterministic tests, and one
composition-owned lifecycle. Existing clients and commands remain compatible.
There is temporary duplication in mirrored legacy status fields until all old
views move to `ProviderDiagnostics`.

## Testing Impact

Tests use in-memory provider doubles and cover registration, persistence,
manual Gemini/Ollama routing, explicit fallback, normalized errors, secret-free
diagnostics, Core delegation, and shared runtime identity. Automated tests make
no real provider requests. Lightweight AST checks also prevent Core and UI from
importing provider SDKs, keep adapters independent of PyQt and memory storage,
centralize provider-service construction in the factory, and prevent adapters
from changing manual selection.
