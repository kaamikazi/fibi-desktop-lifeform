# ADR 0007: Use An Explicit Application Composition Root

Status: accepted

## Context

`FibiCore` constructed dozens of concrete engines while also coordinating
routing, commands, persistence, and product policy. The Pet and Control Center
need one shared runtime, but implicit construction made duplicate services and
worker ownership difficult to test.

## Decision

Normal startup uses `fibi.app.composition` as the single place that resolves
runtime configuration and constructs top-level services. A typed
`ApplicationServices` dataclass is injected into `FibiCore`, and
`ApplicationRuntime` owns idempotent startup and shutdown. Minimal
`typing.Protocol` contracts describe provider, memory, desktop-action, project,
STT, and TTS behavior without requiring inheritance.

The existing direct `FibiCore(...)` constructor remains a compatibility path.
Routing and command methods stay in Core during this migration step.

## Alternatives Considered

- A dependency-injection framework: rejected because it adds a dependency,
  hides straightforward Python construction, and raises contributor overhead.
- A global service locator: rejected because dependencies become invisible,
  tests leak process state, and lifecycle order is unpredictable.
- Split all of `FibiCore` now: rejected because its regression surface is too
  large for the first migration commit.
- Leave construction in Core: rejected because duplicate services and partial
  startup cleanup remain difficult to reason about.

## Consequences

Application startup has an explicit dependency graph and lifecycle owner. Test
doubles can replace boundary services, configuration has a secret-free repr,
and GUI smoke can detect duplicated primary services. The composition module is
intentionally verbose because ownership is visible rather than discovered at
runtime.

Some second-order routers and repositories are still built inside `FibiCore`.
They will move only when their capability boundary has focused regression tests.

## Migration Impact

`app.py` keeps its public command. `fibi.main` builds one runtime and gives its
core to the Pet; the Pet gives that same core to the Control Center. Existing
callers may continue passing individual constructor dependencies. Future work
should migrate one capability at a time, then deprecate redundant constructor
parameters after a documented compatibility window.

## Testing Impact

Tests cover protocol substitutability, one-time configuration resolution,
service identity, Pet/Control Center sharing, idempotent lifecycle behavior,
partial-build cleanup, secret-free diagnostics, and startup use of the
composition root. Provider, microphone, and desktop effects remain mocked or
inactive.
