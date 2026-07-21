# Gemini Resilience Hotfix (v0.30.4)

Fibi treats Gemini as a replaceable language provider, not as identity,
memory, permissions, or action authority. This patch changes only provider
reliability and diagnostics.

## Request Policy

- Compatible text-generation models are discovered and ranked once per
  session.
- One request may make at most two Gemini generation attempts.
- Only temporary service failures and transient network failures are retried.
- The retry waits between 500 and 1500 milliseconds.
- When another stable Flash candidate exists, the retry uses that candidate;
  otherwise it retries the selected model.
- Authentication, rate-limit, malformed response, and unsupported-model
  failures are not retried automatically.

## Health Policy

Provider states are `healthy`, `degraded`, `rate_limited`,
`configuration_error`, `unavailable`, and `unknown`.

Temporary failures enter a 25-second session-only cooldown. A later request
may try Gemini after the cooldown. `/provider test` performs one neutral
context-free probe and bypasses transient cooldown once. `/provider reset
health` clears only transient state and cannot clear authentication failures.

## Fallback Policy

When Gemini is selected, Ollama fallback is attempted only when the user has
explicitly enabled automatic fallback in Settings and the local Ollama health
endpoint responds quickly. Automatic fallback is off by default.
When Ollama is stopped, Fibi skips generation and reports the provider outage
without waiting for the normal Ollama generation timeout.

## Privacy

Health logs include only attempt number, model ID, sanitized error category,
retry count, and duration. Prompts, responses, memories, API keys, browser
content, project files, and raw API payloads are not logged.

## Current Data

Gemini is not treated as a live-data source. Without a connected live-data
tool, Fibi clearly reports that current weather, news, prices, and sports
scores are unavailable.
