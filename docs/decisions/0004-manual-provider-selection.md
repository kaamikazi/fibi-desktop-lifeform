# ADR 0004: Provider Selection Is Manual

Status: accepted

## Context

Automatic provider switching makes privacy, cost, latency, and failure behavior
unpredictable. Fibi currently supports Gemini and Ollama with saved selection.

## Decision

The user manually selects Gemini or Ollama. A provider failure returns a clear
error and leaves selection unchanged. Automatic fallback is off by default and
is not part of the 0.4 supported path.

## Alternatives Considered

- Fastest-provider race: rejected for cost/privacy unpredictability.
- Silent fallback: rejected because it changes data destination.
- One provider only: rejected because local and optional cloud use are valuable.

## Consequences

Failures are more visible, but behavior is honest and reproducible. Providers
implement one common contract and do not own Fibi personality or permissions.

## Migration Impact

Consolidate provider settings and health behind `LanguageProvider`; retain
existing commands and settings labels as adapters.

## Testing Impact

Contract tests assert no provider change, no unexpected network call, bounded
timeouts, clear health, and identical response-pipeline behavior.
