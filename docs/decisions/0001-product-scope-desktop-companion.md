# ADR 0001: Product Scope Is A Desktop Companion

Status: accepted

## Context

Fibi accumulated language about lifeforms, identity, inner life, autonomy, and
advanced intelligence. This obscures the installable product and expands the
maintenance surface.

## Decision

Fibi is an open-source desktop companion. Supported work prioritizes launch,
Pet UI, concise chat, safe actions, projects, reviewed memory, push-to-talk,
Control Center, and diagnostics. AGI, consciousness, self-modification, and
autonomous-agent positioning are outside product scope.

## Alternatives Considered

- Continue as a broad digital-life research project: rejected as difficult to
  explain, test, secure, and ship.
- Remove personality entirely: rejected because character is part of the UX.

## Consequences

Personality becomes presentation flavor and cannot override useful answers,
permissions, or user settings. Experimental cognition-oriented systems receive
no priority over release reliability.

## Migration Impact

Update active docs and UI labels first. Deprecate rather than immediately delete
experimental modules. Remove them only after usage and data migration review.

## Testing Impact

Release tests focus on supported user journeys. Experimental features are
isolated and cannot fail default startup.
