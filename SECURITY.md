# Security Policy

## Supported Version

Fibi is beta software. Security fixes target the latest commit on `main` and the
latest published release candidate. Older local builds may not receive fixes.

## Reporting A Vulnerability

Do not open a public issue for vulnerabilities involving credentials, arbitrary
code execution, permission bypass, unsafe file access, plugin loading, update
integrity, memory disclosure, or microphone recording. Contact the maintainer
privately through the repository owner's published GitHub contact channel. Do
not include real secrets or private user data; provide minimal reproduction steps.

The project currently offers no paid bug bounty or guaranteed response time.
Maintainers should acknowledge credible reports, reproduce safely, prepare a
fix, and coordinate disclosure before publishing technical details.

## Security Boundaries

- Model output is untrusted text and cannot directly execute desktop actions.
- Desktop actions require typed resolution, allowlists, permissions, and
  confirmation where appropriate. Unrestricted shell access is unsupported.
- Projects are limited to user-registered roots with traversal and secret-file
  checks.
- Cloud providers receive only explicitly prepared text context. Background
  microphone audio is never sent to a model.
- Raw audio is not retained. Wake mode is off by default and experimental.
- RVC is local and optional; model files are not part of the source release.
- Plugins are not currently supported. Do not load third-party Python code as a
  plugin until the versioned permission API exists.
- No external telemetry is enabled by default.

## Secret Handling

Use an ignored `.env` or operating-system environment variables for optional
provider credentials. Never commit API keys, tokens, authorization headers,
private keys, recovery codes, credentials, `.env`, runtime logs, support
bundles, browser content, memory databases, or model outputs containing secrets.

Before release, review staged files and run the repository secret/release-content
checks. If a secret is committed, revoke it immediately; deleting the file in a
later commit is not sufficient.

## Safe Development

- Tests use fake providers and action executors.
- Release builds exclude runtime data, logs, databases, caches, temporary audio,
  `.env`, voice models, and reports.
- Dependency updates require source/reputation review and regression tests.
- Automatic updates remain disabled until artifacts are signed and rollback is
  designed.
- Security-sensitive errors must be actionable without logging private payloads.

## Known Limitations

Fibi is Windows-first beta software, not a security boundary against a malicious
local user or malicious installed Python package. Python plugins, if introduced,
will require explicit trust unless isolated in a separate OS-sandboxed process.
