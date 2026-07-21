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

### Replaceable Language Providers

- Ollama remains the default local language provider.
- v0.30.1 adds optional, explicit-opt-in Gemini support through Google's current `google-genai` SDK.
- Provider changes do not move identity, memory, consent, permissions, workflows, actions, or safety into the model.
- Cloud context is minimized and previewable before use.
- Gemini failures can visibly fall back once to local Ollama.

### Demo UI Polish

- v0.30.2 gives the floating companion a responsive four-zone layout.
- Fibi is visually larger without modifying the expression PNG assets.
- The chat input expands while Mic and Send keep stable, non-overlapping sizes.
- Existing Memory, Workflows, Browser, Commands, Notebook, Health, Report, and
  Settings destinations remain available in a compact footer.
- A state-driven badge shows local, Gemini, or fallback mode without exposing
  credentials or provider context.

### Conversation and Gemini Hotfix

- v0.30.3 keeps exact greetings instant while routing meaningful questions,
  explanations, planning, and contextual conversation through the selected
  model provider.
- Local social replies rotate recent lines and escalate when the deterministic
  response set is exhausted.
- Development launches find the project-root `.env` independently of the
  shell's current directory. Packaged builds continue to rely on external
  configuration and never bundle `.env`.
- Settings now uses readable tabs, grouped provider controls, scrollable pages,
  and an explicit Edge-only or Edge-plus-RVC voice selector.

### Gemini Resilience

- v0.30.4 classifies provider failures without treating every error as
  permanent downtime.
- Gemini temporary service and network failures receive one bounded retry,
  followed by a short recoverable cooldown.
- Stable text-generation model candidates are discovered once per session and
  reused. A retry may use the next compatible stable candidate.
- Ollama is health-probed before fallback, so a stopped local service does not
  add a full generation timeout.
- `/provider status`, `/provider test`, and `/provider reset health` expose
  safe health, retry, fallback, and recovery diagnostics without prompts,
  responses, memories, or credentials.
- Current weather, news, prices, and sports scores require a connected
  live-data source; the language model is not presented as a live-data tool.

### Local Beta Packaging

- Windows portable build tooling exists.
- A verified portable ZIP and executable are produced locally for v0.30.4.
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
- [Optional Gemini Provider](docs/GEMINI_PROVIDER_V0301.md)
- [Cloud Context Privacy](docs/CLOUD_CONTEXT_PRIVACY_V0301.md)
- [Demo UI Polish](docs/DEMO_UI_POLISH_V0302.md)
- [Conversation and Gemini Hotfix](docs/CONVERSATION_GEMINI_HOTFIX_V0303.md)

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

### Optional Gemini Development Provider

Gemini is not enabled by default. Put the key manually in the ignored `.env`
file; never commit it or paste it into chat:

```dotenv
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
FIBI_PROVIDER=ollama
FIBI_GEMINI_MODEL=gemini-3.1-flash-lite
FIBI_GEMINI_TIMEOUT_SECONDS=8
FIBI_GEMINI_FALLBACK_TO_OLLAMA=false
FIBI_GEMINI_STREAMING=true
FIBI_GEMINI_GOOGLE_SEARCH=true
FIBI_CLOUD_CONTEXT_PREVIEW=true
```

Restart Fibi, then select the provider explicitly:

```text
/provider use gemini
/provider status
/provider context
```

Use `/provider use ollama` to return to local mode. Fibi defaults to
`gemini-3.1-flash-lite` with minimal thinking and streaming for short latency.
An empty model setting uses safe session-only model discovery and prefers that
model when available, then another stable Flash-class text model.

Google Search grounding is used only for live-data questions such as current
weather or news, and only after Gemini and cloud access have both been
explicitly enabled. Set `FIBI_GEMINI_GOOGLE_SEARCH=false` to keep those
questions blocked locally.

Provider selection is manual. Gemini errors never silently change the selected
provider. Automatic fallback is off by default and can only be enabled from
Settings; the saved choice remains in effect until the user changes it.
Temporary Gemini errors use one retry at most and report degraded state clearly.

RVC is also manual and persisted. Use `/voice rvc on`, `/voice rvc off`, or the
Settings checkbox. With RVC off, Fibi sends cleaned speech directly to Edge TTS.

```text
/provider status
/provider test
/provider reset health
```

Google AI subscriptions and Gemini API billing/quota may be separate. Fibi does
not enable billing or change billing settings. Review Google's current API
policies and limits before use.

### B. Portable Windows Beta

The v0.30.4 portable ZIP and executable are generated locally by the release tooling:

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
/provider status
/provider privacy
/voice rvc off
/voice status
```

For the larger command list, see [docs/COMMANDS_V029.md](docs/COMMANDS_V029.md).

## Testing and Verification

The current v0.30.4 validation includes:

- 214 passing tests with no automated Gemini API calls
- full mock-only provider resilience regression tests and GUI smoke
- v0.30.1 provider, v0.30.2 UI, v0.30.3 routing, and v0.30.4 resilience smoke tests
- Windows build verification, checksum generation, and ZIP privacy scan

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
- Optional Gemini mode requires network access, a user-managed API key, and available API quota.
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
