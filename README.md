# Fibi v0.30

Fibi is a tiny chibi desktop lifeform for Windows. She floats on the desktop,
blinks when artwork is available, breathes softly, chats in a bubble, speaks
with optional TTS, and keeps a small local inner world.

The core is being decomposed into routers and services so FibiCore can stay an
orchestrator instead of a God Object. Fibi v0.17 adds command, action, chat,
context, project, memory, voice, and response-pipeline router boundaries while
preserving the existing UI, life, RVC, action, model, and memory behavior. See
`ARCHITECTURE.md` for ownership and privacy boundaries.

## Fibi v0.30 Memory Review Center

v0.30 adds user-owned memory review and consent controls. Fibi can remember,
but the notebook is visible, searchable, editable, exportable, and pausable.

Memory commands:

- `/memories`
- `/memory search <term>`
- `/memory show <id>`
- `/memory approve <id>`
- `/memory pin <id>`
- `/memory archive <id>`
- `/memory edit <id> <new text>`
- `/memory delete <id>`
- `/memory delete category <category>`
- `/memory export`
- `/memory health`
- `/memory consent`
- `/memory learning off`
- `/memory safety`

Natural prompts:

- `what do you remember?`
- `search your memory for Fibi`
- `pause memory`
- `resume memory`
- `export my memories`
- `is memory safe?`

Release artifacts:

```text
dist/Fibi_Chubi_v0.30.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.30.0.exe
dist/release_manifest_v0.30.0.json
dist/checksums_v0.30.0.txt
```

Docs:

- `docs/MEMORY_REVIEW_CENTER_V030.md`
- `docs/MEMORY_PRIVACY_V030.md`

## Fibi v0.29 Command Center

v0.29 adds a command map for Fibi's growing powers: capability registry,
searchable commands, safety explanations, permission overview, and a small GUI
Command Center.

Discovery commands:

- `/help`
- `/help commands`
- `/help search <term>`
- `/commands`
- `/commands <category>`
- `/capabilities`
- `/capability <name>`
- `/permissions`
- `/safety`
- `/refusals`
- `/confirmations`
- `/beginner guide`

Natural prompts:

- `what can you do?`
- `show commands`
- `help me use Fibi`
- `what is safe?`
- `what needs confirmation?`
- `what can you not do?`

Release artifacts:

```text
dist/Fibi_Chubi_v0.30.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.30.0.exe
dist/release_manifest_v0.30.0.json
dist/checksums_v0.30.0.txt
```

Docs:

- `docs/BEGINNER_GUIDE_V029.md`
- `docs/CAPABILITIES_V029.md`
- `docs/COMMANDS_V029.md`
- `docs/SAFETY_MODEL_V029.md`

## Fibi v0.28 Workflow Recipes

v0.28 adds safe workflow recipes: named, repeatable rituals that guide work
step by step without becoming autopilot.

Recipe commands:

- `/workflow list`
- `/workflow show <name>`
- `/workflow start <name>`
- `/workflow current`
- `/workflow next`
- `/workflow pause`
- `/workflow resume`
- `/workflow cancel`
- `/workflow history`
- `/workflow export last`
- `/workflow safety`
- `/recipes`

Built-in recipes:

- Debug Failed Project
- Safe Release Build
- Beta QA Pass
- Website Review / Outreach Research
- Bug Report Support Bundle
- Daily Fibi Startup Check

Recipes guide existing safe systems for patches, checks, browser notes, issue
reports, support bundles, and release builds. They do not auto-run commands,
auto-apply patches, scrape pages, send messages, upload files, or buy things.

Release artifacts:

```text
dist/Fibi_Chubi_v0.28.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.28.0.exe
dist/release_manifest_v0.28.0.json
dist/checksums_v0.28.0.txt
```

Docs:

- `docs/WORKFLOW_RECIPES_V028.md`

## Fibi v0.27 Safe Browser Helper Mode

v0.27 lets Fibi help with browser-based work without becoming sneaky. She can
save URL notes, open a URL only after confirmation, summarize user-provided page
text, and make manual browser checklists.

Browser commands:

- `/browser start <goal>`
- `/browser open <url>`
- `/browser pending`
- `browser confirm`
- `/browser cancel`
- `/browser note <url> <note>`
- `/browser summarize`
- `/browser save page`
- `/browser plan`
- `/browser history`
- `/browser clear session`
- `/browser safety`
- `/browser remember note`

Fibi will not read browser history, cookies, passwords, or pages silently. She
does not click, fill forms, send messages, purchase things, or scrape sites.

Release artifacts:

```text
dist/Fibi_Chubi_v0.27.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.27.0.exe
dist/release_manifest_v0.27.0.json
dist/checksums_v0.27.0.txt
```

Docs:

- `docs/BROWSER_HELPER_V027.md`

## Fibi v0.26 Beta Feedback, Local Issues, And Update Prep

v0.26 adds local beta testing tools without telemetry or auto-updates.

New beta commands:

- `/issue new <title | details>`
- `/issue list`
- `/issue last`
- `/issue close <id>`
- `/issue reopen <id>`
- `/issue export <id>`
- `/issue export all`
- `/issue link support last`
- `/feedback new <note>`
- `/feedback list`
- `/feedback export`
- `/support bundle for issue <id>`
- `/release health`
- `/update status`
- `/update notes`
- `/update safety`
- `/debug summary`
- `/debug recent errors`
- `/debug last route`
- `/debug paths`
- `/debug workers`

Beta files stay local:

- issues: `data/issues/issues.jsonl`
- feedback: `data/issues/feedback.jsonl`
- exports: `data/reports/`

Release artifacts:

```text
dist/Fibi_Chubi_v0.26.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.26.0.exe
dist/release_manifest_v0.26.0.json
dist/checksums_v0.26.0.txt
```

Docs:

- `docs/BETA_FEEDBACK_FLOW_V026.md`
- `docs/ISSUE_TRACKER_V026.md`
- `docs/UPDATE_PREP_V026.md`

## Fibi v0.25 Real Installer, Beta Distribution, And User Onboarding

v0.25 adds the beta distribution flow: Inno Setup script, installer build helper,
checksum generation, release manifest, beta tester guide, and clearer installed
data-folder commands.

New install/support commands:

- `/install status`
- `/data folder`
- `/open data folder`
- `/open logs folder`
- `/reset instructions`

Installer/build tools:

```powershell
python tools/build_windows.py --clean --zip
python tools/make_checksums.py
python tools/build_installer.py
```

Release artifacts:

```text
dist/Fibi_Chubi_v0.26.0_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.26.0.exe
dist/release_manifest_v0.26.0.json
dist/checksums_v0.26.0.txt
```

## Fibi v0.24 Beta QA, First-Run Polish, And Release Hardening

v0.24 prepares Fibi for local beta testers without adding new assistant powers.

New beta/release commands:

- `/first run status`
- `/beta status`
- `/beta on`
- `/beta off`
- `/limitations`
- `/self test`
- `/support bundle`

Release docs:

- `docs/RELEASE_NOTES_V024.md`
- `docs/RESET_AND_UNINSTALL.md`
- `docs/QA_RESULTS_V024.md`

Release zip:

```text
dist/Fibi_Chubi_v0.26.0_windows_beta.zip
```

## Fibi v0.17 Foundation Cleanup

v0.17 focuses on foundation stability instead of new visible powers:

- stretched greetings and social check-ins route locally under 300ms
- date/time and safe action intents still run before model routing
- new `fibi/engines/routers/` boundaries begin splitting `FibiCore`
- new `fibi/rag/rag_memory_service.py` is the primary memory interface
- new `LegacyMemoryAdapter` keeps old memory-style calls available while RAG
  becomes the default for new memory reads/writes
- new `tools/migrate_legacy_memory_to_rag.py` migrates old SQLite memories with
  dry-run by default
- new `MigrationManager` and `WorkerManager` provide central foundations for
  future database and background-task cleanup

Migration commands:

```powershell
python tools/migrate_legacy_memory_to_rag.py --dry-run
python tools/migrate_legacy_memory_to_rag.py --apply
```

## Fibi v0.23 Windows Build, Installer, And Release Candidate

v0.23 gives Fibi a real writable home outside the source folder or bundled exe.
Development launch still works:

```powershell
python app.py
```

Packaged launch target:

```powershell
dist\Fibi Chubi\Fibi Chubi.exe
```

Build commands:

```powershell
python tools/build_windows.py
python tools/build_windows.py --clean
python tools/build_windows.py --skip-tests
python tools/build_windows.py --zip
```

If PyInstaller is missing:

```powershell
pip install pyinstaller
```

Runtime data locations:

- source/dev mode: `data/`
- packaged normal mode: `%APPDATA%\Fibi Chubi\`
- packaged portable mode: create `portable_mode.txt` beside `Fibi Chubi.exe`,
  then data goes to `.\data\`

Bundled by default:

- Fibi app code
- PyQt UI assets from `fibi/ui/assets`
- `config/default_settings.json`
- local README and release docs
- version/build metadata

Excluded by default:

- `data/`
- logs, reports, exports, caches, temp audio
- memory DBs and journal DBs
- `.env` files and secrets
- `voice_models/`
- RVC `.pth` and `.index` files
- tests

Release checks:

```powershell
python tools/verify_release.py
python tests\smoke_v023_packaged_paths.py
```

Useful release/runtime commands:

- `/version`
- `/version detailed`
- `/health gui`
- `/startup diagnostics`
- `/export error report`

Manual release QA checklist:

`docs/RELEASE_QA_V023.md`

RVC voice models are not bundled. After install, place models under
`%APPDATA%\Fibi Chubi\voice_models\` or portable `.\data\voice_models\`, then
configure:

```text
/voice skin model <path-to-model.pth>
/voice skin index <path-to-model.index>
/voice skin backend rvc_python
/voice skin on confirm
```

## Fibi v0.22 GUI Reliability, QA, And Packaging Prep

v0.22 focuses on making Fibi safer and easier to run as a real desktop app.

New reliability commands:

- `/version`
- `/health gui`
- `/startup diagnostics`
- `/export error report`
- `/utility tts on`
- `/utility tts off`
- `/project checks on`
- `/project checks off`

GUI smoke mode:

```powershell
python app.py --gui-smoke
```

This initializes the PyQt app, creates the main window, verifies key widgets,
then exits. If a GUI display is unavailable, it reports the issue instead of
crashing the launcher.

Diagnostics and reports:

- startup diagnostics: `data/startup_diagnostics.json`
- shutdown marker: `data/shutdown_marker.json`
- safe error reports: `data/reports/fibi_error_report_*.zip` in dev mode, or
  the packaged user data reports folder
- manual GUI QA checklist: `docs/GUI_MANUAL_QA_V022.md`
- packaging prep: `packaging/`

Error reports exclude memory databases, project source code, raw journals,
voice model files, and secrets.

## Fibi v0.21 Guided Work Session Mode

Fibi can guide a supervised project task as a local step-by-step session. This
is not autonomy; it is a tiny plan, progress tracker, and next-step helper.

Useful commands:

- `/session start <goal>`
- `/session current`
- `/session continue`
- `/session next`
- `/session pause`
- `/session resume`
- `/session cancel`
- `/session summary`
- `/session history`
- `/session clear completed`

Natural prompts such as `help me fix this`, `make a plan`, `continue`,
`what's next?`, `guide me through this`, `resume the task`, and `stop this task`
route through the same local session system.

Session safety rules:

- no autonomous file edits
- no autonomous checks
- no autonomous app control
- no terminal freedom
- no installs
- no git
- no deploys
- no deleting files
- no secret reading
- no hidden work
- every risky action still uses the existing confirmation flow

Sessions persist locally in:

```text
data/work_sessions.json
```

When a session completes, Fibi stores a short RAG event summary only. She does
not store full code or full check output.

## Fibi v0.20 Check Output Fix Suggestions

Fibi can inspect the last failed safe check, identify likely error locations,
read only safe related project files, and suggest a pending patch when the fix
is low or medium risk.

This completes the local safety loop:

```text
suggest patch -> apply confirm -> run check confirm -> fail -> suggest fix -> apply confirm
```

Useful commands:

- `/check analyze last`
- `/check suggest fix`
- `/check fix last`
- `/fix last check`
- `/fix explain`
- `/fix clear`

Natural prompts such as `why did it fail?`, `suggest a fix`, `fix the check`,
`fix the tests`, and `can you fix the build?` use the same safe path.

Fix suggestion safety rules:

- no automatic edits
- no automatic check reruns
- no package installs
- no git
- no deploys
- no deleting files
- no editing secrets
- no model-generated command execution
- no hidden file modifications
- patch confirmation still goes through `apply patch confirm`

If the output points to a risky area such as auth, payment, security,
permissions, secrets, or unclear files, Fibi marks it manual-only.

## Fibi v0.19 Safe Project Check Runner

Fibi can now run a small whitelist of project verification checks after user
confirmation. This is for local validation only; Fibi still does not get an
arbitrary terminal.

Safety rules:

- whitelisted presets only
- confirmation required by default
- `subprocess.run(..., shell=False)` only
- command working directory must stay inside the registered project
- no installs
- no git commands
- no delete/remove/rm/del commands
- no migrations, deploys, publishes, or long-running servers by default
- model output can never execute a command
- full output is saved locally, but history and memory store only summaries

Useful commands:

- `/check presets`
- `/check run <preset>`
- `/check pending`
- `/check confirm`
- `/check cancel`
- `/check last`
- `/check history`
- `/check output last`
- `/check safety`

Natural prompts such as `compile project`, `run tests`, `run lint`, and
`check this project` create a pending check. They do not run until you confirm:

```powershell
compile project
run check confirm
```

Check output is saved locally under:

```text
data/project_checks/<check_id>/
```

Metadata-only check history is stored in:

```text
data/project_check_history.jsonl
```

Relevant settings live in local app settings:

```text
allow_project_checks = true
require_check_confirmation = true
allow_low_risk_checks_without_confirmation = false
check_timeout_seconds = 60
max_check_output_chars = 12000
save_full_check_output = true
auto_suggest_check_after_patch = true
auto_run_check_after_patch = false
```

## Fibi v0.18 Safe Patch Apply Mode

Fibi can now apply user-reviewed project edit suggestions, but only inside a
registered project and only after an exact confirmation phrase. This is not
autonomous coding.

Safety rules:

- no terminal commands
- no package installs
- no git operations
- no automatic test runs
- no hidden writes
- no deleting files
- no writing outside the registered project
- no `.env`, secret, private key, binary, vendor, minified, or lockfile edits
- high-risk auth, payment, database, migration, security, and permission code is
  manual-only in v0.18

Patch flow:

```powershell
/edit file app.py replace "hello" with "hello tiny"
/patch pending
/patch apply confirm
/patch rollback last
```

Useful commands:

- `/patch pending`
- `/patch apply confirm`
- `/patch cancel`
- `/patch rollback last`
- `/patch history`
- `/patch safety`

Before writing, Fibi creates a local backup under:

```text
data/patch_backups/<patch_id>/
```

Patch history is metadata-only and local:

```text
data/patch_history.jsonl
```

## Setup

Install Python 3.11 or newer, then install dependencies from the project root:

```powershell
pip install -r requirements.txt
```

Fibi does not install packages automatically at startup. If `python app.py`
reports a missing desktop dependency, either run the command above yourself or
use the explicit one-time helper:

```powershell
python app.py --install-deps
```

## Run

```powershell
python app.py
```

## Local Logs

Fibi writes structured local logs to:

```text
data/fibi.log
```

Set `FIBI_LOG_LEVEL=DEBUG` for noisier troubleshooting or `FIBI_LOG_FILE` to
choose a different local log path. The logger masks common API keys, tokens,
passwords, and bearer tokens before writing to console or file.

## Optional Ollama Setup

Fibi talks to local Ollama at `http://localhost:11434` and prefers the fast
model `qwen2.5:1.5b`. Larger models work, but small models make desktop chat
feel much more alive.
If Ollama is not running, she uses safe local fallback replies.

```powershell
ollama pull qwen2.5:1.5b
ollama pull qwen3:8b
ollama serve
```

Model and timeout settings live in `fibi/settings.py` and can be overridden in
`fibi/config.json`:

```json
{
  "ollama_model": "qwen2.5:1.5b",
  "ollama_timeout_seconds": 20
}
```

## Manual Action Core

Fibi v0.12 gives Fibi her first safe manual hands. She can act only when the
user directly asks her to. Model output never triggers actions.

Supported safe commands include:

- `open Chrome`
- `open YouTube`
- `search Google for Python recursion`
- `search YouTube for lo-fi music`
- `wiki Alan Turing`
- `volume up`
- `volume down`
- `mute`
- `unmute`
- `what time is it`
- `what date is it`
- `refresh apps`
- `list apps`
- `find app chrome`

Safety boundaries:

- no autonomous control
- no terminal command execution
- no file deletion or modification
- no private-message reading
- no clipboard action by default
- no screenshots by default
- no shutdown/restart by default
- no sending messages or email
- no buying, login, or password actions

Action settings persist locally in `data/fibi_state.json`. Action history is
written locally to `data/action_journal.jsonl`. The local app allowlist is stored
in `data/app_index.json`.

Useful commands:

- `/actions status`
- `/actions on`
- `/actions off`
- `/apps refresh`
- `/apps count`
- `/apps search <name>`
- `/pending action`
- `/cancel action`
- `/screenshots status`
- `/screenshots on confirm`
- `/screenshots off`
- `/shutdown actions status`
- `/shutdown actions on confirm`
- `/shutdown actions off`

Risky actions require settings plus confirmation. For example, shutdown actions
are disabled by default; after `/shutdown actions on confirm`, Fibi still asks
for an exact phrase such as `confirm shutdown`.

App indexing scans common Windows app locations only: Start Menu, Desktop,
Program Files, and Program Files (x86). It does not scan user documents deeply
and does not upload the app list.

## Voice Command Mode

Fibi v0.13 adds push-to-talk voice input. It is off by default. There is no
always-listening mode and no wake word listener yet.

Supported now:

- mic button in the PyQt window
- `/listen`
- local transcript routing through the same `FibiCore` pipeline as typed text
- safe voice actions such as `open chrome` or `search YouTube lo-fi`
- risky voice actions still require confirmation
- low-confidence action transcripts ask for confirmation instead of acting

Voice privacy defaults:

- voice input off by default
- wake word off by default
- audio not saved
- transcripts not journaled
- cloud speech APIs not used
- voice text follows the same action permission rules as typed text

Voice commands:

- `/voice input on confirm`
- `/voice input off`
- `/voice status`
- `/listen`
- `/mic devices`
- `/mic test`
- `/wake word status`
- `/wake word off`

Optional install for local speech recognition:

```powershell
pip install SpeechRecognition
pip install pyaudio
```

On Windows, `pyaudio` can be fussy. If it is missing, Fibi stays alive and says
things like `mic creature missing.` or `voice brain not installed.`

## Optional Local RVC Voice Skin

Fibi v0.16 can optionally generate speech with edge-tts first, then pass that
audio through a local RVC voice model before playback. This is a voice skin only:
Fibi's identity remains in her life, memory, personality, and behavior engines.

Privacy and safety:

- disabled by default
- local files only
- no uploads
- no cloud API required
- normal edge-tts remains the fallback
- use only models you have permission to use
- do not distribute unauthorized voice models
- do not impersonate real people or claim an official character voice

Install optional files from a local zip:

```powershell
python tools/install_rvc_voice_model.py "D:\PhoebeJP_e260_s7540_RVCv2_RMVPE%20.zip"
```

This extracts only:

```text
voice_models/fibi_rvc/model.pth
voice_models/fibi_rvc/model.index
```

Optional heavy dependencies are kept out of the main install:

```powershell
pip install -r requirements-rvc.txt
```

RVC packages can be fussy on Python 3.12. If `rvc-python` does not install,
use a local RVC WebUI backend later; Fibi will still run normally without it.

Voice skin commands:

- `/voice skin status`
- `/voice skin model voice_models/fibi_rvc/model.pth`
- `/voice skin index voice_models/fibi_rvc/model.index`
- `/voice skin backend rvc_python`
- `/voice skin on confirm`
- `/voice skin test`
- `/voice skin off`
- `/voice cache status`
- `/voice cache clear`

If RVC conversion fails, Fibi says nothing scary and plays the normal edge-tts
voice instead.

## Context Drop And File Awareness

Fibi v0.14 can understand context the user explicitly gives her. This is not
screen reading and not clipboard spying.

Supported context inputs:

- pasted long text
- pasted code blocks
- `/context add <text>`
- `/explain <text>`
- `/summarize <text>`
- dropped text/code files

Supported file types:

- `.txt`, `.md`, `.py`, `.js`, `.ts`, `.tsx`, `.jsx`
- `.json`, `.csv`, `.html`, `.css`, `.log`, `.yaml`, `.yml`

Rules:

- files must be explicitly dropped or selected by the user
- max file size is 1 MB
- unsupported files fail safely
- Fibi never executes files
- Fibi never imports code
- Fibi never scans neighboring files
- Fibi never recursively scans folders
- clipboard reading remains disabled by default
- screenshots remain disabled
- context is temporary by default
- long-term memory requires `/context remember last confirm`

Context commands:

- `/context`
- `/context last`
- `/context clear`
- `/context remember last confirm`
- `/context forget last`
- `/context privacy`
- `/context add <text>`
- `/explain <text>`
- `/summarize <text>`

Secret-looking values are masked in previews and model context, including API
keys, tokens, passwords, authorization headers, private keys, and long random
secret strings. Raw temporary context remains local.

## Project Workspace Mode

Fibi v0.15 can understand a project folder the user explicitly registers. This
is project awareness, not project control.

Commands:

- `/project add <path>`
- `/project list`
- `/project current`
- `/project switch <name>`
- `/project scan`
- `/project files`
- `/project search <text>`
- `/project read <relative_path>`
- `/project summary`
- `/project note <text>`
- `/project forget <name> confirm`
- `/project open vscode`
- `/project privacy`

Scanner behavior:

- scans only registered project folders
- records filenames, relative paths, sizes, and modified times
- skips `node_modules`, `.git`, `.next`, `dist`, `build`, `out`, caches,
  virtualenvs, IDE folders, and generated folders
- refuses `.env`, secrets, private keys, credential files, and large/binary
  files
- never runs npm, pip, git, shell commands, or package installers
- never edits or writes project files

Project context sent to models is sanitized summary/snippet context only. Cloud
remains disabled by default, and local absolute paths are not included in model
hints.

## Safe Project Edit Suggestions

Fibi v0.16 can help write code, but only as manual suggestions. She can inspect
safe files inside the active registered project, propose unified diffs, and show
copy-paste replacement blocks. She does not apply patches yet.

Commands:

- `/edit plan <request>`
- `/edit file <relative_path> <request>`
- `/edit explain last`
- `/edit copy last`
- `/edit clear`
- `/edit safety`

You can also ask naturally when a project is active, for example:

- `change components/Button.tsx to make the button blue`
- `replace "Old Title" with "Tiny App" in app/page.tsx`

Safety rules:

- no write-to-disk behavior
- no patch application
- no terminal commands
- no package installs
- no dependency changes without warning
- no `.env`, credential, private-key, or secret edits
- no destructive deletes
- auth, payment, security, database, and migration edits are high risk
- cloud remains disabled by default and context is sanitized before any optional
  model use

Edit metadata is journaled locally in `data/project_edit_journal.jsonl`.
`data/last_edit_suggestion.json` may hold the latest suggestion for copying.
Full code is not stored in the edit journal by default.

## Fast Replies And Model Routing

Local command and action detection runs before the Fast Response Classifier and
before any model route. Greetings, thanks, goodbye, success, frustration, and
tiny status checks use local fast paths and should feel instant. Normal
questions and requests route to the model router only when a model is allowed.

Fibi v0.15.1 adds a `RouteDecisionEngine` so routing is explicit and easier to
debug. Slash commands, local utilities, date/time, volume, app/search actions,
privacy, memory, project, context, route, and TTS commands never call Ollama or
cloud providers. Complex chat is the only normal route that can use the model.

Route debug commands:

- `/route last`
- `/route test <message>`

Example:

```text
/route test what's the date
```

Fibi should answer with a local route such as `local_utility/tell_date`.

Slash commands, privacy commands, memory care, and Notebook commands are also
local-only.

The Model Router order is:

1. local commands
2. local greeting fast path
3. local creature reactions
4. optional NVIDIA provider when explicitly enabled
5. optional Ollama provider
6. local fallback line

Response budgets keep the creature from waiting too long:

- greeting: 300 ms
- local reaction: 500 ms
- command: 1000 ms
- simple chat: 2000 ms
- complex chat: 8000 ms

If a model path is slow or unhealthy, Fibi falls back to lines like `still here`
or `local creature mode`.

If Ollama times out, Fibi puts the model path on a short cooldown and answers
future complex questions locally instead of waiting again. `/model status` shows
cooldown text like `ollama sleepy for 53s` when active.

Useful commands:

- `/model status`
- `/model local`
- `/model ollama`
- `/model nvidia`
- `/model auto`
- `/cloud on confirm`
- `/cloud off`
- `/cloud context none`
- `/cloud context minimal`
- `/cloud context memory_hint`

## Optional NVIDIA API Setup

Cloud is disabled by default and NVIDIA is not required. Fibi can run fully
offline with only the Local Micro-Brain. Optional cloud providers are language
tools only; Fibi's identity and safety rules remain local.

Create a local `.env` from `.env.example` or set environment variables:

```powershell
$env:NVIDIA_API_KEY="your_key_here"
```

Defaults:

- `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`
- `NVIDIA_MODEL=nvidia/nemotron-mini-4b-instruct`
- `NVIDIA_TIMEOUT_SECONDS=8`
- `NVIDIA_MAX_TOKENS=60`
- `NVIDIA_TEMPERATURE=0.7`

Generic OpenAI-compatible cloud variables are also supported:

- `CLOUD_PROVIDER=disabled`
- `CLOUD_API_KEY=`
- `CLOUD_BASE_URL=`
- `CLOUD_MODEL=`
- `CLOUD_TIMEOUT_SECONDS=8`

Cloud context is sanitized. Minimal mode sends only Fibi identity, current mood,
time feel, and the user message. Memory hint mode can send one or two short
natural hints. It never sends raw SQLite rows, journal dumps, dreams, inner
thoughts, clipboard, screenshots, API keys, secrets, full logs, or local file
paths.

Return to local-only mode with:

```text
/cloud off
/model local
```

## Slow Reply Troubleshooting

If a greeting feels slow, check logs for:

- `FAST_PATH_USED: true`
- `PROVIDER_USED: local`
- `MODEL_USED: local-greeting`
- `FINAL_REPLY_TIME_MS`

If a normal message is slow, lower Ollama timeout/model size or use local mode:

```text
/model local
```

Performance commands:

- `/perf`
- `/perf reset`
- `/cancel`
- `/stop`
- `/route last`
- `/route test <message>`
- `/tts status`
- `/tts stop`

`/model status` includes local model health such as whether Ollama is sleepy and
whether cloud is off.

TTS is non-blocking from the UI's point of view: the bubble appears first, then
speech is attempted in a background thread. Utility/action replies are low
priority and skip voice by default so date/time/app/search/status answers stay
snappy. Turn general voice output on/off with:

```text
/voice output on
/voice output off
```

## Daily Desktop App Features

Fibi v0.11 adds a system tray menu when the platform supports it:

- Show / Hide Fibi
- Nap / Wake
- Quiet Mode
- Open Notebook
- Open Settings
- Model Status
- Privacy Status
- Quit

Closing the window can minimize to tray instead of exiting. Tray icon assets are
optional; Fibi falls back to a simple generated icon.

Settings are stored locally in `fibi_settings.json` under the configured data
folder. The settings panel includes general behavior, privacy, models, voice,
sound, performance, and data controls. API keys are never displayed in full.

First-run setup is short and local-first:

- welcome
- privacy explanation
- voice/silent choice
- local model choice
- memory learning choice

Cloud remains off by default. Clipboard remains off by default.

Autostart uses the Windows Startup folder and writes `Fibi.cmd`. It is never
enabled automatically:

```text
/autostart on confirm
/autostart off
/startup status
```

Health commands:

```text
/health
/assets
```

Portable data folder:

```powershell
$env:FIBI_DATA_DIR="D:\FibiData"
python app.py
```

Manual GUI checklist: `docs/GUI_VERIFICATION_CHECKLIST.md`.

## Optional TTS Setup

Voice output uses `edge-tts` and `pygame`. If either package or audio playback is
unavailable, Fibi still chats silently without crashing.

## Assets

Fibi searches these folders:

- `fibi/assets/`
- `fibi/ui/assets/`

Expression PNG names:

- `idle.png`
- `happy.png`
- `thinking.png`
- `talking.png`
- `sleepy.png`
- `angry.png`
- `blink.png` optional

Missing expression files fall back to `idle.png`.

Optional sound effects can be placed in:

- `fibi/assets/sounds/`
- `fibi/ui/assets/sounds/`

Sound names Fibi will try:

- `startup.wav`, `.mp3`, or `.ogg`
- `message.wav`, `.mp3`, or `.ogg`
- `thinking.wav`, `.mp3`, or `.ogg`

Missing sounds are skipped silently.

## Mood And Memory

The life engine lives in `fibi/life/life_engine.py`. It tracks mood, speaking
and thinking state, idle timing, blink timing, and animation phases.

Fibi saves small local memory to:

```text
data/fibi_state.json
```

Example:

```json
{
  "mood": "happy",
  "last_user_message": "hello",
  "interaction_count": 12
}
```

Long-term categorized memories and conversations are stored in local SQLite:

```text
data/fibi_memory.db
```

The schema is in `fibi/engines/schema.sql`. Optional sample memories live in
`data/sample_memories.json`; Fibi does not import them automatically.

## Continuity And Journal

Fibi records small sampled journal events in the same local SQLite database.
Events include startup, shutdown, idle reactions, user messages, learned
memories, project mentions, mood changes, fallbacks, and sampled errors.

The Life Engine preserves these continuity fields in `data/fibi_state.json`:

- `last_started_at`
- `last_seen_at`
- `last_shutdown_at`
- `total_sessions`
- `total_interactions`
- `last_known_mood`

The Journal Engine can produce a short daily summary locally without Ollama.

## Pattern Awareness

The Pattern Engine looks for simple recurring behavior using existing sampled
journal and memory data. MVP patterns include late-night coding, frequent VS
Code use, repeated project mentions, repeated errors, long idle gaps, frequent
greetings, and returns after long breaks.

Patterns are local hints, not diagnoses. They use transparent thresholds and
confidence scores and do not create a continuous activity history.

## Bond And Creature State

Life Engine stores a small non-romantic desktop-companion bond model:

- affection
- trust
- comfort
- mischief
- attachment level

Values change slowly through greetings, kind messages, successful moments,
frustration, petting, repeated dragging, long absences, and late-night work.
They only adjust Fibi's warmth, teasing, comfort, and gentle honesty.

All values remain local in `data/fibi_state.json`.

## Touch, Drag, And Nest Position

Clicking Fibi produces cooldown-safe poke or pet reactions. Repeated pokes can
make her mildly annoyed. Dragging changes her presence state, produces tiny
relocation reactions, and saves `window_x` and `window_y` locally.

Saved positions are restored only when valid for a currently connected screen;
otherwise Fibi safely returns to the lower-right corner.

Repeatedly placing Fibi near one position establishes a persistent nest. A
single accidental drag cannot replace it. Restoration tries the latest valid
position, then the nest, then the default corner.

## Rituals And Daily Continuity

Local morning, evening, daily-return, project-return, and shutdown rituals have
persistent cooldowns so greetings never stack. Curated lines come from the
Reaction Library and are filtered by context, bond, time, and repetition.

At shutdown, sampled journal events become a local SQLite daily summary.
Project affinity changes only for already-known projects. Time curves make Fibi
more curious in the morning, focused in the afternoon, and sleepy late at night.

## Creature Motion And Emotional Timing

Motion Engine selects small local sprite motions for touch, dragging, thinking,
sleepiness, waking, naps, annoyance, and celebrations. PyQt composites position
and scale transforms into the existing 30 ms breathing loop, so animation never
blocks chat, TTS, blinking, or dragging. Rotation is intentionally omitted for
now because the current fixed sprite bounds could clip rotated artwork.

Timing Engine adds brief nonblocking pauses, thinking lines, and typing styles.
Expression Controller prevents flicker and returns temporary reactions to the
persistent mood. The bubble supports tiny typing, text-length auto-hide, TTS
hold, and duplicate suppression.

Repetition Guard persists only short recent buffers in `fibi_state.json`.
Unchanged context, focused coding, low attention, naps, or recent duplicates can
produce a silent motion or no reaction. Optional sound events (`click`, `happy`,
`annoyed`, `sleep`, `wake`, `drag`, `success`) skip silently when files or pygame
are unavailable.

## Inner Life, Dreams, And Preferences

Fibi v0.07 adds private tiny thoughts, dreams while napping, slow preferences,
stable evidence-backed opinions, emotional memory weighting, and gentle mood
drift. These are creature-state signals, not productivity integrations.

Dreams and inner thoughts are stored separately from factual memories. They may
be whimsical, but they do not create user facts, projects, or beliefs. Fibi only
learns explicit memories through the existing cautious memory rules.

Thought bubbles are rare, attention-aware, repetition-guarded, and blocked while
Fibi is busy or the user appears focused. Most thoughts stay internal.

## Memory Care And Notebook

Fibi v0.08 adds local memory controls. The Memory Care Engine can list, search,
inspect, edit, delete, mark, reduce, export, import-validate, and reset local
data with confirmation checks for destructive actions.

The PyQt UI includes a small `Notebook` button that opens "Fibi's notebook" with
sections for memories, journal, dreams, preferences, and projects. It can edit
or delete selected memories, export a local bundle, clear dreams, and clear the
journal.

Slash commands work locally before Ollama:

- `/help`
- `/memories`
- `/memory search <text>`
- `/forget <text>`
- `/forget category <category> confirm`
- `/dreams`
- `/clear dreams confirm`
- `/journal today`
- `/summary yesterday`
- `/preferences`
- `/projects`
- `/export memories`
- `/privacy`
- `/reset fibi confirm`

Exports are written to `data/exports/fibi_export_YYYYMMDD_HHMMSS.json`.
Full reset requires the exact phrase `reset fibi confirm` and can create a
backup export first.

## Local RAG Memory

Fibi v1 RAG memory is a production-style local Retrieval-Augmented Generation
subsystem for personal memories. It is local-first and does not call cloud
services.

Architecture:

- `fibi/rag/config.py`: RAG paths, thresholds, and retrieval settings
- `fibi/rag/embedding.py`: local embedding providers
- `fibi/rag/repository.py`: SQLite metadata and audit events
- `fibi/rag/vector_store.py`: persisted FAISS vector index
- `fibi/rag/service.py`: add, update, delete, search, duplicate detection,
  scoring, top-k retrieval, and conversation context assembly
- `fibi/rag/ingestion.py`: local document extraction, chunking, and background
  indexing
- `fibi/rag/retrieval.py`: query rewriting and retrieval cache
- `fibi/rag/evaluation.py`: offline retrieval-quality evaluation over a
  `corpus/` plus `train.json` dataset
- `fibi/engines/rag_memory_engine.py`: Fibi-facing integration facade

Storage:

```text
data/fibi_memory.db        SQLite metadata
data/rag/fibi_rag.faiss    FAISS vector index
data/rag/fibi_rag_ids.json FAISS row-to-memory id map
```

The default embedding backend is deterministic local feature hashing. It needs
no network and downloads no model files. The config also supports an explicit
local `sentence_transformers` backend if installed later.

Optional heavier local embedding backend:

```powershell
pip install -r requirements-rag.txt
```

Then configure `RAGConfig(embedding_backend="sentence_transformers")` in the
integration layer that creates the RAG service.

Example API:

```python
from fibi.rag import RAGMemoryService

rag = RAGMemoryService()
memory = rag.add_memory(
    "Imran is building Fibi as a tiny desktop lifeform.",
    category="project",
    source="conversation",
    source_id="chat-2026-07-05-001",
    source_uri="local://conversation/chat-2026-07-05-001",
    source_title="User conversation",
    provenance={"turn": 1, "collector": "fibi"},
    importance=0.9,
)
results = rag.retrieve_top_k("Fibi desktop creature", top_k=3)
context = rag.retrieve_conversation_context("what do you remember about Fibi?")
```

Features:

- add, update, and soft-delete memories
- search memories with configurable similarity threshold
- retrieve top-k scored results
- conversation context retrieval with character budget
- source/provenance tracking for each memory
- local document ingestion for TXT, Markdown, DOCX, optional PDF, and
  future-ready image/audio/video metadata paths
- incremental FAISS indexing for new memories
- versioned FAISS manifest
- retrieval cache
- local query rewriting
- hybrid vector plus keyword search
- optional memory expiration
- health monitoring through `RAGMemoryService.health()`
- long-term SQLite metadata
- persisted FAISS vector database
- exact-hash and embedding-similarity duplicate detection
- memory scoring with similarity, importance, confidence, and recency
- local-only logging and audit events

Local evaluation:

```text
eval/corpus/fibi_memories.jsonl
eval/train.json
eval/benchmark.py
eval/rag_memory/corpus/fibi_memories.jsonl
eval/rag_memory/train.json
```

The eval layout is inspired by NVIDIA `rag-eval`: a corpus directory plus a
`train.json` query set. Fibi's evaluator is intentionally offline and uses
deterministic retrieval metrics such as recall@k and mean reciprocal rank
instead of cloud judges or RAGAS.

Run the local benchmark suite:

```powershell
python eval\benchmark.py --dataset eval
```

NeMo Retriever note: NVIDIA NeMo Retriever is the right tool for indexing and
querying multimodal document corpora such as PDFs, Office files, images, audio,
and video. Fibi's built-in RAG memory is different: it stores small personal
memories and conversation-derived facts locally in SQLite plus FAISS. The app
does not fake a NeMo Retriever integration when the local Retriever service or
CLI is not installed.

Smoke test:

```powershell
python tests/smoke_v017_rag_memory.py
python tests/smoke_v019_rag_memory_v1.py
python tests/smoke_v021_rag_nextgen.py
```

More docs:

- `docs/RAG_MIGRATION_GUIDE.md`
- `docs/RAG_DEVELOPER_GUIDE.md`

## Privacy Settings

Privacy settings persist locally in `data/fibi_state.json`. Clipboard remains
disabled by default. There is no screenshot setting because screenshots are not
supported.

Current controls cover foreground app observation, window title observation,
clipboard observation, journaling, dreams, inner thoughts, pattern detection,
idle bubbles, TTS, sounds, Ollama, and memory learning. Disabling a feature
stops that feature path locally.

## Relationship, Boundaries, And Quiet Mode

Fibi v0.09 adds a local Relationship Engine, Boundary Engine, and Social Context
Filter. These keep Fibi socially believable without becoming clingy, romantic,
manipulative, or noisy.

Fibi now tracks a small local relationship stance: familiarity, teasing safety,
comfort with silence, quiet/playful preferences, annoyance, warmth, distance,
and interaction style. This state changes slowly. Trust and kindness can make
her warmer over time; boundaries and annoyance make her quieter immediately.

Boundary phrases like "not now", "quiet", "busy", "shut up", and "leave me
alone" are handled locally before Ollama. Fibi responds briefly with lines like
"okay.", "quiet mode.", or "sorry." and does not argue or guilt-trip.

Quiet mode commands:

- `/quiet`
- `/quiet 30m`
- `/quiet off`
- `/status`
- `/relationship`
- `/relationship reset confirm`

Quiet mode stops idle bubbles, thought bubbles, and non-essential ambient
reactions while preserving direct user messages and silent animations.

Fibi is not romantic. She should not use dependency language, guilt, shame, or
intense sarcasm. Teasing is allowed only when trust/familiarity are sufficient,
annoyance is low, no boundary is active, and the moment is not sensitive.

## Nap, Wake, Attention, And Habits

Fibi can nap after long inactivity when sleepy, low-energy, or active late at
night. Messages, clicks, dragging, and window focus wake her. Normal idle
reactions stop while she naps.

Attention Engine makes silence an explicit choice. Direct messages always get
attention; click, drag, idle, nap, celebration, and comfort reactions use their
own cooldowns.

Habit Engine chooses consistent local behaviors such as guarding the desktop,
watching VS Code, counting tabs badly, tiny patrols, and pretend debugging.
Habits and creature interactions do not require Ollama.

## Desktop Awareness And Privacy

Fibi samples the current foreground app/window and time of day when preparing a
reply. She does not create an activity timeline. Clipboard reading is disabled
by default and requires both configuration and explicit call-site permission.

All memory, journal entries, summaries, affinities, rituals, and observations stay local.

Fibi does not:

- take screenshots
- read private messages
- read notifications or page contents
- continuously track applications
- read the clipboard without explicit permission
- require a cloud model

Ollama remains optional and local-first. Local continuity, idle reactions,
memory hints, opinions, pattern awareness, petting, dragging, naps, habits,
celebrations, and comfort reactions still work without it.

## Reply Pipeline

Replies flow through:

1. update presence, continuity, bond, and nap state
2. sample safe context and write important journal events
3. retrieve memories, yesterday context, patterns, and known-project affinity
4. update mood drift, preferences, and private inner thoughts
5. calculate attention, time temperament, habits, rituals, and local reactions
6. handle local message, click, drag, nest, nap, wake, dream, celebration, or comfort events
7. prepare memory hints, opinions, and personality context
8. call Ollama only when no local reaction fits
9. clean, display, and optionally speak
10. persist mood, bond, nest, rituals, conversation, journal, daily summary, dreams, thoughts, and preferences

## Direct Smoke Test

If pytest is unavailable:

```powershell
python tests/smoke_v003.py
python tests/smoke_v004.py
python tests/smoke_v005.py
python tests/smoke_v006.py
python tests/smoke_v007.py
python tests/smoke_v008.py
python tests/smoke_v009.py
python tests/smoke_v009_hotfix.py
python tests/smoke_v010.py
python tests/smoke_v011.py
python tests/smoke_v012_actions.py
python tests/smoke_v013_voice.py
python tests/smoke_v014_context.py
python tests/smoke_v015_project_workspace.py
```
