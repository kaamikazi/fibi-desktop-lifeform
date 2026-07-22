# ADR 0002: Split Pet And Control Center Surfaces

Status: accepted

## Context

Daily companionship needs a tiny surface, while configuration and diagnostics
need normal desktop controls. The current Pet exists but inherits substantial
behavior from the large window module.

## Decision

Keep two surfaces sharing one application runtime: Fibi Pet is default and
minimal; Fibi Control Center opens on demand. They use separate presenters and
shared service contracts.

## Alternatives Considered

- One expandable window: rejected because it couples daily UI to administration.
- Separate processes: deferred; service sharing and lifecycle would be heavier.

## Consequences

UI state becomes easier to reason about, while runtime services remain singletons
owned by the application lifecycle.

## Migration Impact

Extract shared widgets and presenters incrementally. Preserve `FibiWindow` and
`FibiPetWindow` imports through adapters until callers migrate.

## Testing Impact

Add separate Pet and Control Center smoke tests plus an assertion that both use
the same provider, memory, action, and speech service instances.
