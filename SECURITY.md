# Security Policy

Fibi is designed as a local-first desktop companion. Please do not include secrets, passwords, API keys, tokens, private keys, cookies, or private user data in public bug reports or pull requests.

## Reporting Security Issues

Report suspected security issues privately through the project maintainer's preferred private channel. Do not open public issues for credential leaks, private memory exposure, or sensitive local-file handling problems.

When reporting an issue, include a short description, affected version, reproduction steps, and sanitized logs only. Replace any secret value with `[secret]`.

There is no guaranteed security response SLA for this personal beta project.

## Project Principles

- Local-first by default.
- No telemetry by default.
- Runtime memory and private data should stay out of source control.
- Secrets should never be committed.
- Support bundles and debug reports should mask or exclude sensitive data where designed.
