# ADR 0013: Stabilize Native Actions Without a Second Command System

Status: accepted

## Decision

Native desktop and productivity actions continue to use the existing typed
intent, permission, confirmation, and executor pipeline. The executor keeps
the v0.12 positional `DesktopActionResult` contract and adds normalized status,
permission state, stable error codes, and safe metadata.

The action surface may reuse existing project and work-session owners through
injected callbacks. It must not create a second project store, memory store,
provider path, or shell runner.

## Safety rules

- App discovery is centralized and ordered: explicit registry, alias registry,
  Start Menu, known install locations, then `PATH`.
- User text cannot name an arbitrary executable or provide shell arguments.
- File actions are restricted to canonical allowlisted roots and reject
  symlink/junction/reparse chains.
- Search returns bounded safe relative paths, not raw private file content.
- Native failures expose stable categories rather than exception text.

## Consequences

This improves deterministic reliability while preserving existing UI, provider,
memory, and permission ownership. A future platform adapter can replace the
Windows effect callbacks without changing the intent or result contract.
