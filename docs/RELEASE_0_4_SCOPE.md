# Fibi Companion 0.4: Reliable Daily Companion

## Release Goal

Ship a polished Windows desktop companion whose supported behavior is small,
predictable, private, and documented.

## Included

- Compact transparent Fibi Pet as the default surface.
- Separate on-demand Control Center.
- Reliable concise text chat.
- Manual Gemini or Ollama selection; no silent provider switching.
- Safe app, folder, URL, web-search, and registered-project opening.
- Basic registered-project file listing/search/read within approved roots.
- Simple reviewed memory viewer/editor/export/delete controls.
- Push-to-talk with visible microphone state.
- Edge TTS by default.
- Persisted settings, permission controls, health diagnostics, and logs.
- Clean Windows portable package and public setup/development docs.

## Experimental, Disabled By Default

- Wake word: requires real microphone validation per release environment.
- RVC voice conversion: optional, local, and expected to add latency.
- Advanced project patch/check workflows.
- Browser research helpers beyond opening and user-provided text.
- Automatic semantic memory extraction and FAISS retrieval.

## Excluded

- Unrestricted shell or arbitrary executable paths.
- Autonomous desktop control, messaging, purchases, deletion, or installation.
- Cloud microphone streaming or retained raw audio.
- Plugin marketplace or remote plugin installation.
- Automatic updates without signature verification.
- AGI, consciousness, self-modification, or cognitive identity claims.

## Release Gates

- Compile and full unit suite pass.
- Pet and Control Center GUI smoke pass.
- Supported actions have mocked tests and manual Windows QA.
- Missing optional dependencies degrade clearly without crashing.
- Clean environment install and portable build pass.
- Secret/release-content scans pass.
- No known orphan worker or dirty-shutdown bug.
- README, security, privacy, development, and release docs match the build.

## Support Statement

Windows is the only supported 0.4 platform. Linux and macOS are future targets,
not implied support. Experimental features receive best-effort diagnostics but
are not release blockers unless they affect supported defaults.
