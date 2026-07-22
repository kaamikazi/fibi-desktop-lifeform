# ADR 0005: Desktop Actions Are Narrow And Permissioned

Status: accepted

## Context

Desktop control is useful but can expose files, secrets, accounts, and system
state. Legacy helpers include global keyboard and process termination functions,
while the active action engine has safer allowlists and confirmations.

## Decision

Support only typed actions resolved from direct user input: open allowlisted app,
folder, URL, web search, copy text, open a registered project, and search files
inside approved roots. Every action passes resolution, permission, optional
confirmation, execution, and structured result stages. No unrestricted shell.

## Alternatives Considered

- Let model output invoke tools: rejected as unsafe.
- General shell with confirmations: rejected because command review is fragile.
- Remove actions: rejected because narrow actions provide daily value.

## Consequences

Coverage is intentionally limited. Platform-specific execution moves behind an
adapter and user-facing errors remain actionable.

## Migration Impact

Wrap `DesktopActionEngine`, isolate Windows code, mark `fibi/control` deprecated,
then remove it after import and packaging checks.

## Testing Impact

Use fake executors. Test allowlists, traversal, confirmations, cancellation,
error categories, and that model-generated text cannot execute actions.
