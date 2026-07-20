# Fibi

### A local-first desktop lifeform with user-owned memory and model-independent identity.

The model can change.  
Her identity and history remain.  
The user owns the notebook.

Fibi is a Python/PyQt6 Windows desktop companion that lives as a small floating presence on the user's desktop. She can chat, react, remember, speak when optional voice dependencies are available, guide safe workflows, and expose her memory and permissions instead of hiding them behind a black box.

Fibi is not trying to be a corporate assistant with a mascot attached. She is an experiment in building a persistent local character system where personality, memory, safety, and continuity are owned by the application and the user, not by whichever language model happens to answer a message.

## Why Fibi Exists

Most assistants place personality, memory, identity, and reasoning inside a single model session. When the provider changes, the prompt changes, or the session resets, continuity can disappear with it.

Fibi explores a different architecture: the language model is a replaceable language and reasoning cortex, while Fibi's identity, memory, consent rules, safety boundaries, rituals, moods, and desktop presence live in local deterministic systems.

The goal is not to claim consciousness or autonomy. The goal is a more durable desktop companion: familiar, reviewable, local-first, and controlled by the user.

## What Fibi Does

### Presence and Interaction

- Floating always-on-top PyQt6 desktop window.
- Draggable chibi character with mood expressions and idle motion.
- Chat bubble, text input, local reactions, and optional voice output.
- Push-to-talk voice input is supported when optional dependencies are available.
- Local mood, timing, attention, ritual, relationship, and reaction systems keep Fibi from feeling like a raw chatbot.

### User-Owned Memory

- Local RAG memory layer using SQLite metadata and FAISS vector search.
- Memory Review Center for inspecting, searching, approving, editing, pinning, archiving, exporting, and deleting memories.
- Memory learning can be paused.
- Sensitive-memory controls block secrets and require approval for sensitive personal memories.

### Safe Workflows and Project Help

- Workflow Recipes guide repeated tasks without bypassing confirmations.
- Project workspace tools can scan approved project folders, read safe files, suggest patches, run confirmed checks, analyze check failures, and create support bundles.
- Patch apply and project checks require explicit confirmation.

### Browser Assistance

- Safe browser helper for confirmed URL opening, saved URL notes, user-provided page summaries, and manual research workflows.
- No hidden browsing, scraping, auto-clicking, form filling, browser-history access, cookies, passwords, sending, or buying.

### Command Center and Permissions

- Command Center and capability registry show what Fibi can do.
- Permission and safety explainers make boundaries visible.
- Local commands handle status, safety, memory, workflows, browser help, project checks, voice, and release diagnostics.

### Local Beta Packaging

- Windows portable build tooling exists.
- A verified portable ZIP and executable were produced locally for v0.30.
- Generated binaries and `dist/` are intentionally not committed to this source repository.
- Inno Setup was not installed in the verified environment, so no installer EXE was produced.

## The Core Architecture

```text
User
  |
Fibi Desktop Presence
  |
Router / Orchestrator
  |-- Identity and personality
  |-- RAG memory and consent
  |-- Safety and permissions
  |-- Workflows and project tools
  `-- Replaceable language-model provider
```

The model provider can generate language and reasoning output, but it does not own Fibi's identity. Local systems control memory, permissions, continuity, action boundaries, refusals, and what context is allowed to reach a provider.

See [ARCHITECTURE.md](ARCHITECTURE.md) for deeper engine boundaries.

## User-Owned Memory

Fibi can remember, but the user owns the notebook.

v0.30 adds a Memory Review Center with controls to:

- review memories
- search memory
- approve pending memories
- edit memory text
- pin important memories
- archive memories
- export memory to local JSON and Markdown
- delete individual memories or staged categories
- pause and resume memory learning

Sensitive-memory protection blocks passwords, API keys, tokens, private keys, recovery codes, raw private browser text, raw project secrets, and similar secret-shaped content. Sensitive personal memories require approval by default.

Memory deletion writes a local audit record containing metadata and a text hash only, not the deleted memory text.

Memory databases, FAISS indexes, logs, reports, private browser notes, and runtime memory data are not included in the public repository.

Read more:

- [Memory Review Center](docs/MEMORY_REVIEW_CENTER_V030.md)
- [Memory Privacy](docs/MEMORY_PRIVACY_V030.md)
- [RAG Developer Guide](docs/RAG_DEVELOPER_GUIDE.md)
- [RAG Migration Guide](docs/RAG_MIGRATION_GUIDE.md)

## Safety Model

Fibi is local-first and permission-first.

Fibi does not:

- auto-run arbitrary commands
- auto-apply patches
- browse secretly
- access browser history, cookies, or passwords
- auto-click, auto-fill, or submit forms
- send messages automatically
- purchase anything
- upload private data silently
- store detected secrets as memory
- export raw memory databases or full project source in support bundles

Risky operations require explicit confirmation. Model output is never allowed to trigger desktop actions directly.

Read more:

- [Privacy](PRIVACY.md)
- [Security Policy](SECURITY.md)
- [Safety Model](docs/SAFETY_MODEL_V029.md)
- [Capabilities](docs/CAPABILITIES_V029.md)

## Built-In Guided Workflows

Workflow Recipes are named local guides. They can show steps, track progress, pause, resume, and point to existing safe commands. They do not bypass confirmations.

Built-in recipes:

- Debug Failed Project
- Safe Release Build
- Beta QA Pass
- Website Review / Outreach Research
- Bug Report Support Bundle
- Daily Fibi Startup Check

See [Workflow Recipes](docs/WORKFLOW_RECIPES_V028.md).

## Demo Highlights

A short judge-friendly demo can show:

1. Ask Fibi: `what do you remember?`
2. Open the Memory Review Center from the UI.
3. Approve, pin, archive, or delete a demo memory.
4. Start a safe workflow with `/workflow list` and `/workflow start <name>`.
5. Inspect `/permissions`, `/safety`, and `/refusals`.
6. Run `/health gui` to show local status, memory health, model state, and safety state.

No public demo video is claimed in this repository yet.

## Installation

### A. Development Mode

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Run a GUI smoke check:

```powershell
python app.py --gui-smoke
```

The default RAG memory path uses deterministic local hashing plus SQLite and FAISS. Optional heavier local embeddings can be installed separately:

```powershell
python -m pip install -r requirements-rag.txt
```

Optional local RVC voice-skin dependencies are separate and can be heavyweight:

```powershell
python -m pip install -r requirements-rvc.txt
```

Normal Fibi does not require RVC.

### B. Portable Windows Beta

The verified v0.30 portable ZIP and executable were generated locally by the release tooling:

```powershell
python tools\build_windows.py --clean --zip
python tools\verify_release.py --gui-smoke
python tools\make_checksums.py
```

Those generated files live under local `dist/` during release preparation, but `dist/` and generated binaries are intentionally not committed to this source repository.

A downloadable GitHub Release may be added later. This repository currently does not provide a committed installer or release binary.

Inno Setup is optional for installer generation. It was not installed in the verified build environment, so no installer EXE was produced.

## Useful Commands

Starter commands:

```text
/help
/capabilities
/permissions
/safety
/memories
/memory health
/workflow list
/workflow start <name>
/browser safety
/health gui
```

For the larger command list, see [docs/COMMANDS_V029.md](docs/COMMANDS_V029.md).

## Testing and Verification

Verified v0.30 results:

- 129 tests passed
- 3 warnings
- GUI smoke passed
- v0.29 and v0.30 smoke tests passed
- Windows build verification passed
- checksum generation passed
- ZIP privacy scan passed

Reproducible checks:

```powershell
python -m pytest -q
python app.py --gui-smoke
python tests\smoke_v029_command_center.py
python tests\smoke_v030_memory_review.py
```

During repository preparation, the literal all-tree `compileall` command timed out because ignored heavyweight local folders such as `.venv-rvc`, `build`, `dist`, `data`, and `voice_models` remained on disk. A source-only compile check excluding those ignored/generated folders passed.

## Repository and Privacy Notes

The public source repository intentionally excludes:

- runtime memory
- logs
- reports
- browser notes
- voice models
- generated audio
- databases
- build output
- executables
- release ZIPs
- environment secrets

The repository safety audit for v0.30 found no blocking secrets in tracked files. It passed with warnings for documented false positives and ignored large local artifacts.

## OpenAI Build Week Development

Fibi existed before the submission period. During the submission period, the project was substantially extended and hardened.

Verified additions and hardening include:

- Safe Browser Helper
- Workflow Recipes
- Command Center
- Capability Registry
- Permission and Safety Explainability
- Memory Review Center
- Memory Consent Controls
- Sensitive Memory Guard
- Windows beta release hardening
- expanded automated tests and privacy auditing

The public Git repository was initialized from the completed v0.30 working tree because earlier local Git history was unavailable. The repository therefore does not represent the complete historical commit timeline.

## Current Limitations

- Windows-first.
- Beta-quality.
- No installer EXE in the current verified environment.
- Optional voice and RVC setup can be heavyweight.
- Local model quality and speed depend on hardware.
- Legacy memory notebook remains for compatibility.
- Complete cross-model identity-continuity evaluation remains future research.

## Roadmap

- provider-independent language layer improvements
- continuity evaluation across model replacement
- stronger voice interaction
- better onboarding
- formal identity and memory evaluation
- optional signed update path

## License

License decision pending. Until a license is added, normal copyright restrictions apply.

## Closing

Fibi is not trying to make a model pretend it has a life.  
She is an experiment in giving a persistent local system continuity while keeping the user in control.
