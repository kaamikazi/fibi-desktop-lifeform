# Developing Fibi Companion

## Supported Development Environment

The current supported platform is Windows with Python 3.12. Cross-platform
contributions are welcome, but Linux and macOS behavior is not release-tested.

## Setup

```powershell
git clone <repository-url>
cd fibi-desktop-lifeform
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Copy the canonical [`.env.example`](../.env.example) to `.env` only when
configuring an optional cloud provider. Never commit `.env`, keys, tokens,
runtime data, logs, voice models, or user memory.

## Test Commands

```powershell
python -m compileall -q .
python -m pytest -q
python app.py --gui-smoke
python tools/verify_release.py --release-dir "dist/Fibi Chubi"
```

Tests must mock provider calls and destructive/visible desktop actions. Unit
tests must not require a microphone, network, paid API, browser session, or real
application launch.

## Code Organization

- Put product policy in core/use-case code, not widgets or providers.
- Return typed results and stable error categories from services.
- Inject external effects: clocks, processes, browsers, audio, filesystem, and
  provider clients.
- Keep the selected provider manual and deterministic.
- Route all desktop effects through permission and action services.
- Do not add permanent memory writes without consent and review behavior.
- Keep optional features import-safe when their dependency is absent.

## Change Workflow

1. Inspect existing behavior and dirty files.
2. Add or update focused tests.
3. Make the smallest compatible change.
4. Run focused tests, then the full suite and GUI smoke.
5. Review `git diff --check`, staged files, and a secret scan.
6. Document user-visible behavior and compatibility impact.

## Architecture Changes

Significant boundaries, persistence formats, permissions, provider behavior,
plugin APIs, and supported-platform decisions require an ADR in
`docs/decisions/`. Prefer compatibility adapters and staged migrations.

Top-level dependencies are wired only in `fibi/app/composition.py`. Add a
minimal protocol in `fibi/app/contracts.py` when a consumer needs a replaceable
boundary, then add the concrete service to `ApplicationServices` and test its
identity and cleanup. Do not fetch services from globals or construct a second
provider, memory, action, project, STT, or TTS service in a UI adapter.

## Packaging

Windows packaging instructions live in `packaging/README.md`. Build output is
local and must not be committed. Release verification must reject `.env`, user
databases, logs, voice models, caches, and temporary audio.

## Optional Capabilities

RVC and wake word are experimental. Do not describe them as supported until the
target environment passes manual hardware tests. Edge TTS and push-to-talk are
the supported 0.4 voice direction.
