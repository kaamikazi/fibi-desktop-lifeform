# Fibi Companion

Fibi is an open-source Windows desktop companion: a small chibi character for
concise chat, safe desktop shortcuts, registered-project help, user-reviewed
memory, and optional voice.

Fibi is beta software. It is not AGI, an autonomous agent, a self-modifying
system, or an unrestricted computer controller.

## Product Shape

- **Fibi Pet** is the default daily interface: a tiny transparent, draggable
  character with a temporary speech bubble and quick menu.
- **Fibi Control Center** opens on demand for providers, memory, projects,
  permissions, actions, voice, settings, and diagnostics.
- Both surfaces share one runtime and the same provider, memory, action, speech,
  and permission services.

## Supported Capabilities

- Concise text chat through manually selected Ollama or Gemini.
- Safe opening of allowlisted apps, folders, URLs, and registered projects.
- Project file listing, search, and approved text-file context.
- Visible, editable, deletable, exportable, consent-aware local memory.
- Push-to-talk and Edge TTS when their optional dependencies are available.
- Persisted settings, permission explanations, health checks, and local logs.
- Local-first storage with no external telemetry by default.

Wake word, RVC voice conversion, advanced workflows, broad browser automation,
and semantic memory/RAG are experimental. They are disabled by default or kept
outside the supported 0.4 product path.

## Requirements

- Windows 10 or 11
- Python 3.12
- Ollama for local model use, or a Gemini API key for optional cloud use
- A microphone only for push-to-talk or experimental wake-word testing

Linux and macOS are future targets and are not currently release-tested.

## Install From Source

```powershell
git clone https://github.com/kaamikazi/fibi-desktop-lifeform.git
cd fibi-desktop-lifeform
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

For local Ollama chat:

```powershell
ollama pull qwen2.5:1.5b
ollama serve
```

Select Ollama or Gemini manually from Settings or with:

```text
/provider use ollama
/provider use gemini
```

For Gemini, copy [`.env.example`](.env.example) to an ignored project-root
`.env` and replace its placeholder, or set `GEMINI_API_KEY` in your user
environment. Never commit `.env` or credentials. Provider failures do not
silently change the selected provider.

## Daily Use

- Click or right-click Fibi for Talk, Provider, Memory, Actions, Settings,
  Control Center, Hide, and Exit.
- Double-click to open the transient text/push-to-talk panel.
- Drag the Pet to save its desktop position.
- Register projects and application paths in the Control Center.
- Review or delete saved memory from the Memory view.

Examples:

```text
Open Chrome
Open Downloads
Open my Fibi project in VS Code
What do you remember about my project?
/status
/provider status
/permissions
/memory stats
```

## Safety And Privacy

- Model output cannot directly execute desktop actions.
- Actions use typed intents, allowlists, permission checks, and confirmation for
  sensitive operations.
- Unrestricted shell commands, deletion, software installation, sending, and
  purchasing are not supported.
- Project reads stay inside user-registered roots and exclude secret-like files.
- Raw microphone audio is not retained or sent to Gemini.
- Personal databases, logs, caches, voice models, builds, and `.env` files are
  excluded from source releases.
- No telemetry is enabled by default.

See [SECURITY.md](SECURITY.md) and [PRIVACY.md](PRIVACY.md).

## Voice

Push-to-talk and Edge TTS are the supported voice direction for Fibi 0.4.
Wake-word mode is experimental and must not be considered reliable until the
target machine passes real microphone diagnostics. RVC is optional, local, and
can add significant latency.

```text
/voice status
/wake status
/wake devices
/voice rvc off
```

## Memory

The product direction is intentionally simple: retain user-approved facts,
preferences, projects, and selected discussion summaries. Users can inspect,
edit, delete, and export these records. SQLite is the dependable baseline;
semantic retrieval is an optional implementation detail, not a requirement for
small memory collections.

The current beta still contains legacy and RAG compatibility stores. A
cross-store migration has not occurred, and FAISS remains experimental derived
data rather than an authoritative copy. The staged plan preserves legacy data,
requires backups and rollback before any write migration, and keeps providers
outside the memory repository boundary. See the
[memory audit](docs/architecture/MEMORY_SYSTEM_AUDIT.md),
[target architecture](docs/architecture/MEMORY_TARGET_ARCHITECTURE.md),
[migration plan](docs/architecture/MEMORY_MIGRATION_PLAN.md), and
[privacy model](docs/security/MEMORY_PRIVACY_MODEL.md).

```text
/memory remember <fact>
/memory recall <topic>
/memory forget <topic>
/memory recent
/memory stats
```

Contributors may run the content-free structural preflight against a chosen
synthetic or local data directory. It is read-only and has no apply mode:

```powershell
python -m fibi.tools.memory_migrate --dry-run
```

## Development

```powershell
python -m compileall -q .
python -m pytest -q
python app.py --gui-smoke
```

Tests must mock providers and desktop effects. They must not require paid APIs,
real destructive actions, or retained microphone audio.

Contributor documentation:

- [Development guide](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Architecture boundaries](docs/architecture/BOUNDARIES.md)
- [Architecture audit](docs/ARCHITECTURE_AUDIT.md)
- [Product direction](docs/PRODUCT_DIRECTION.md)
- [Roadmap](docs/ROADMAP.md)
- [Fibi 0.4 scope](docs/RELEASE_0_4_SCOPE.md)
- [Plugin API draft](docs/PLUGIN_API_DRAFT.md)
- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## Packaging

Windows packaging remains local:

```powershell
python tools/build_windows.py --clean --zip
python tools/verify_release.py
```

Build output belongs under ignored `build/` and `dist/` directories. See
[packaging/README.md](packaging/README.md).

## Current Limitations

- Windows-only supported release path.
- Beta-quality packaging and diagnostics.
- Large unpinned dependency set; optional dependencies are not yet split.
- Core orchestration and UI modules require staged decomposition.
- Legacy and RAG memory paths coexist during compatibility migration.
- No plugin loader or stable plugin API implementation yet.
- No selected license yet.

## License

A license has not been selected. Until the maintainer adds one, normal copyright
restrictions apply. This is an open-source readiness blocker and must be resolved
by the repository owner before a public reusable release.
