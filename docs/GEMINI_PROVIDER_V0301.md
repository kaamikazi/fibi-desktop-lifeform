# Optional Gemini Provider (v0.30.1)

Gemini is an optional, replaceable language provider for development and demo
testing. Ollama remains Fibi's default local provider. Gemini never owns Fibi's
identity, personality, memory, consent, permissions, workflows, actions, or
response filtering.

## SDK

Fibi uses Google's current Google Gen AI SDK:

- Python package: `google-genai`
- import: `from google import genai`
- supported range: `google-genai>=1,<2`
- official documentation: https://ai.google.dev/gemini-api/docs/libraries

The SDK is imported lazily. Local Ollama mode can start when the SDK is absent.

## Configure Locally

Create or edit the ignored `.env` file in the project root:

```dotenv
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
FIBI_PROVIDER=ollama
FIBI_GEMINI_MODEL=gemini-3.1-flash-lite
FIBI_GEMINI_TIMEOUT_SECONDS=8
FIBI_GEMINI_FALLBACK_TO_OLLAMA=true
FIBI_GEMINI_STREAMING=true
FIBI_GEMINI_GOOGLE_SEARCH=true
FIBI_CLOUD_CONTEXT_PREVIEW=true
```

Never commit `.env` and never paste the key into Fibi chat, an issue, a support
bundle, or a public log.

`gemini-3.1-flash-lite` is the default low-latency model. Fibi uses minimal
thinking and streaming. An empty `FIBI_GEMINI_MODEL` makes Fibi list models
available to the configured key for the current session, keep only
text-generation models, prefer `gemini-3.1-flash-lite` when available, and
avoid preview/experimental models when a stable option exists. A configured
model is validated against that list before use.

Google Search grounding is request-scoped. It is attached only to live-data
questions after the user explicitly selects Gemini and enables cloud access.
Normal conversation does not invoke Search. Disable this capability with
`FIBI_GEMINI_GOOGLE_SEARCH=false`.

## Select and Inspect

```text
/provider status
/provider list
/provider models
/provider use gemini
/provider context
/provider privacy
/provider test
/provider benchmark
/provider use ollama
```

Selecting Gemini is explicit. If the key or SDK is missing, Fibi stays local and
explains how to finish local setup. `/provider test` sends only:

```text
Reply with GEMINI_PROVIDER_OK.
```

The manual benchmark sends one neutral test to each provider. It is a local
latency comparison, not a scientific benchmark.

## Fallback

When enabled, Fibi makes at most one Gemini generation attempt and one Ollama
fallback attempt. A fallback is visible in the reply. Authentication, quota,
rate-limit, timeout, network, missing-model, and malformed-response failures are
normalized into safe messages without credentials.

Turn fallback off with:

```dotenv
FIBI_GEMINI_FALLBACK_TO_OLLAMA=false
```

## Manual Integration Test

This command can consume API quota and is never run by automated tests:

```powershell
python tools\test_gemini_provider_manual.py --confirm-api-call
```

It sends one neutral prompt and prints only the selected model, latency, and
success/failure status.

## Billing and Limits

A Google AI product subscription and Gemini API billing/quota are separate
concerns. API availability and limits are controlled by the user's Google
project and current Google terms. Free-tier quota can be rate-limited. Fibi
does not enable billing or change billing settings.

Create and manage keys in Google AI Studio:
https://aistudio.google.com/app/apikey

Review current API pricing, limits, and policies before enabling Gemini:
https://ai.google.dev/gemini-api/docs
