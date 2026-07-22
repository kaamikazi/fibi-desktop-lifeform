# Contributing To Fibi Companion

Thank you for helping build a friendly, reliable desktop companion. Fibi values
clear behavior, privacy, accessibility, and maintainable code over feature
count. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md),
[SECURITY.md](SECURITY.md), and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
before contributing.

## Before Opening A Change

- Search existing issues and keep one change focused on one product problem.
- Discuss large architecture, persistence, permission, provider, or plugin API
  changes before implementation.
- Do not add AGI, consciousness, self-modification, unrestricted automation, or
  silent cloud behavior.
- Preserve compatibility unless the migration and deprecation path is approved.
- Do not include personal runtime data, `.env`, credentials, logs, databases,
  audio, screenshots, voice models, generated builds, or API responses.

## Development

Use Python 3.12 on Windows for the supported development path:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Run before requesting review:

```powershell
python -m compileall -q .
python -m pytest -q
python app.py --gui-smoke
```

Tests must not make paid API calls, require secrets, execute destructive actions,
or retain microphone audio. Inject fake providers, executors, clocks, and devices.

## Engineering Expectations

- Add type hints to public APIs and return structured results.
- Keep I/O, provider, TTS, and long-running work off the Qt thread.
- Route desktop effects through permissions and the action service.
- Keep provider, RVC, and wake settings manual.
- Keep permanent memory consent-aware and user-visible.
- Prefer a small adapter over a repository-wide rewrite.
- Add comments only where behavior is not self-explanatory.
- Update current documentation, not only version-history documents.

## Commits And Pull Requests

Use short imperative commits such as `fix: handle missing microphone device`.
Pull requests should state the problem, scope, test evidence, privacy/security
impact, screenshots for UI changes, and migration/compatibility impact.

## Architecture Decisions

Add an ADR under `docs/decisions/` for changes to public contracts, persistence,
permissions, supported platforms, provider behavior, or plugin boundaries. ADRs
include context, decision, alternatives, consequences, migration, and testing.

## License Notice

The repository currently has no selected license. Until the maintainer adds one,
normal copyright restrictions apply. Contributions should not copy code or
assets without compatible permission and provenance.
