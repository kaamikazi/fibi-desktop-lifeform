# ADR 0006: Plugins Use A Versioned Capability API

Status: accepted as design; implementation deferred

## Context

Fibi has no plugin system. Passing internal runtime objects to extensions would
freeze unstable internals and bypass permissions.

## Decision

Future plugins use validated manifests, an API version, declared permissions,
and capability-limited registration interfaces for commands, tools, menus,
settings, and integrations. Plugins never receive `FibiCore`, API keys, raw
database connections, or arbitrary process/filesystem access.

## Alternatives Considered

- Import a Python module and pass Core: rejected as unversioned and unsafe.
- Full process sandbox immediately: deferred due complexity.
- Marketplace-first design: rejected before a stable local contract exists.

## Consequences

The first API is deliberately small. Python code is not a security sandbox, so
local installation risk must be documented and stronger process isolation may
follow later.

## Migration Impact

Stabilize service contracts first. Then add manifest validation, a local loader,
permission grants, error isolation, and one example plugin.

## Testing Impact

Add manifest schema, API compatibility, permission denial, activation failure,
cleanup, timeout, and internal-import conformance tests.
