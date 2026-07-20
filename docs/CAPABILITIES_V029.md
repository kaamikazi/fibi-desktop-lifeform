# Fibi v0.29 Capabilities

The capability registry is a read-only map of what Fibi can do, what is enabled,
which commands belong to each area, and which safety boundaries apply.

Use:

```text
/capabilities
/capability browser
/capability patch
```

Capabilities include:

- Chat
- Memory
- Memory Review
- Memory Consent
- Sensitive Memory Guard
- RAG Memory
- Voice Output
- Voice Input
- RVC Voice Skin
- Desktop Actions
- Project Workspace
- Patch Apply
- Project Checks
- Check Failure Analysis
- Work Sessions
- Browser Helper
- Workflow Recipes
- Issue Tracker
- Feedback Capture
- Support Bundle
- Release Health
- Update Manifest
- Packaging/Build Tools
- Gemini Provider

Each capability records:

- capability id
- name and description
- category
- enabled/disabled state
- safety level
- confirmation requirements
- related commands
- setting keys
- blocked actions
- docs path
- runtime status summary

This registry is discovery metadata. It does not execute commands.

v0.30 adds dedicated memory review and consent capability cards. See
`docs/MEMORY_REVIEW_CENTER_V030.md` and `docs/MEMORY_PRIVACY_V030.md`.

v0.30.1 adds an optional Gemini Provider capability card. The provider is a
replaceable language cortex only; it cannot own memory, permissions, workflows,
browser access, or actions. See `docs/GEMINI_PROVIDER_V0301.md`.
