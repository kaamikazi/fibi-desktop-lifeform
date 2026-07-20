# Conversation and Gemini Hotfix (v0.30.3)

Fibi v0.30.3 repairs conversation routing, provider configuration diagnostics,
Settings readability, and demo voice performance controls without changing
memory ownership, permission boundaries, or action safety.

## Conversation routing

Exact greetings and deterministic rituals remain instant and local. Questions
that require content, explanation, reasoning, recall, or project context now
prefer the model router. Exact short social check-ins may still receive a local
reply, but recent lines are excluded so the same canned response is not repeated.
When local classification is uncertain, the model route wins.

## Local environment loading

Development launches load `.env` from the repository root derived from Fibi's
source location, regardless of the shell's current working directory. Existing
process environment variables have priority. Packaged builds use externally
supplied environment variables or an explicit `FIBI_ENV_FILE`; `.env` is never
bundled.

The expected development path is:

```text
E:\Fibi chubi\.env
```

The file should contain a local `GEMINI_API_KEY` assignment. Never paste the key
into chat, reports, screenshots, or source control.

## Safe provider diagnostics

`/provider status` distinguishes the selected provider, active provider, model,
configuration state, visible fallback provider, context-preview state, and the
last sanitized provider error category. It reports only whether a key is
configured and never shows its value, length, prefix, or suffix.

`/provider test` remains explicit and uses one neutral request. Automated tests
use mocks and never call Gemini.

## Settings and voice

Settings tabs now retain readable contrast in active and inactive states.
Provider controls live in a dedicated Language Provider section, and each page
uses a scrollable layout for Windows display scaling.

Voice processing offers:

- Edge TTS only
- Edge TTS + RVC

RVC remains available but warns that CPU conversion can be slow. The demo-safe
default remains Edge TTS only. `/voice rvc off` disables conversion without
disabling normal TTS.
