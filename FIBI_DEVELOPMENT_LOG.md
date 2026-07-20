# Project Fibi Development Log

This document records the work completed on Fibi so far.

## 30.2. Demo UI Polish

- Updated the patch version to `0.30.2`.
- Replaced the fixed, crowded two-column main window with responsive header,
  presence, input, and compact action zones.
- Added a subtle provider badge derived from existing local/cloud state.
- Increased Fibi's visible size by cropping transparent PNG canvas margins in
  memory while preserving source assets, expression alignment, and animation.
- Kept all existing main-window destinations available in a compact footer.
- Added focused geometry, provider-state, secret-visibility, and isolated-data
  tests plus an offscreen UI smoke test.

## 30.1. Optional Gemini Development Provider

- Updated patch version to `0.30.1`.
- Added a lazy `google-genai` provider with session-only model discovery,
  stable Flash preference, timeout control, optional streaming, and normalized
  safe errors.
- Added explicit provider selection and dedicated Gemini privacy permission.
- Added category-level cloud context preview and approved-summary-only memory
  context.
- Added visible one-attempt Ollama fallback without moving identity, memory,
  permissions, workflows, or actions into the provider.
- Added provider commands, settings controls, capability metadata, secret
  masking, safe support-bundle status, mocked tests, and a manual one-call tool.
- Added Gemini and cloud-context privacy documentation.

## 30. Memory Review Center And Consent Controls

- Updated app/build version to `0.30.0`.
- Added local Memory Review, Memory Consent, and Sensitive Memory Guard engines.
- Added user-visible memory list, search, show, approve, pin, archive, edit,
  delete, category delete, export, health, consent, and safety commands.
- Added confirmation staging for memory edits, single deletes, and broad
  category deletes.
- Added deletion audit records under `data/memory/memory_deletion_log.jsonl`
  with text hashes only.
- Added sanitized JSON and Markdown memory export under `data/reports/`.
- Added a PyQt Memory Review panel and tray entry.
- Extended Command Center, capability registry, `/privacy`, `/safety`, and
  `/health gui` with memory visibility and consent details.
- Added v0.30 memory docs plus unit and smoke tests.

## 22. GUI Reliability, Manual QA, And Packaging Prep

- Added version metadata in `fibi/version.py`.
- Added `/version`, `/health gui`, `/startup diagnostics`, and
  `/export error report`.
- Added `StartupDiagnosticsEngine` with local startup diagnostics for Python,
  PyQt6, data directory, memory DB, RAG vector folder, settings files, optional
  dependencies, and shutdown markers.
- Added `ShutdownManager` with a local shutdown marker.
- Added `ErrorReportEngine` for safe diagnostic zip exports without memory DBs,
  raw journals, project source, voice model files, or secrets.
- Added a small PyQt health panel and Health button.
- Added GUI event error boundaries around send, mic, tray callbacks, drops, and
  session chip updates.
- Improved settings visibility for project checks, utility TTS, voice input,
  RVC voice skin, and safe actions.
- Added `python app.py --gui-smoke`.
- Added `docs/GUI_MANUAL_QA_V022.md`.
- Added packaging prep docs/spec/checklists under `packaging/`.
- Added v0.22 smoke and pytest coverage.

## 21. Guided Work Session Mode

- Added work-session contracts in Python and TypeScript:
  - `WorkSession`
  - `WorkSessionStep`
  - `WorkSessionPlan`
  - `WorkSessionState`
  - `WorkSessionProgress`
  - `WorkSessionAction`
  - `WorkSessionDecision`
  - `WorkSessionSummary`
- Added `WorkSessionEngine` with local persistence under
  `data/work_sessions.json`.
- Added `WorkPlannerEngine` for conservative project plans such as failed-build
  debugging, UI improvement, project review, and ambiguous task guidance.
- Added `WorkStepRunner` that only runs safe informational steps and refuses
  restricted steps without permission.
- Added session commands:
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
- Added natural session intents such as `help me fix this`, `continue`,
  `what's next?`, and `stop this task`.
- Added lightweight PyQt session chip showing active session status/current
  step.
- Added short RAG memory events when sessions complete without storing full
  code or outputs.
- Added v0.21 smoke and pytest coverage.

## 20. Check Output Fix Suggestions

- Added failed-check analysis contracts in Python and TypeScript:
  - `CheckFailureAnalysis`
  - `CheckFixSuggestion`
  - `CheckFixPlan`
  - `ErrorLocation`
  - `RelatedFileCandidate`
  - `FixConfidenceResult`
  - `PendingFixSuggestion`
- Added `CheckFailureAnalyzer` for Python, TypeScript, ESLint, pytest,
  Next.js, missing dependency, command-not-found, timeout, and unknown failure
  classification.
- Added `RelatedFileResolver` to map error paths to registered project files
  while refusing traversal, outside-project paths, secrets, unsafe files, and
  unscanned files.
- Added `CheckFixPlanner` with a conservative local fix path for obvious Python
  missing-parenthesis syntax errors.
- Wired fix suggestions through the existing patch safety and confirmation
  system; no fix is applied automatically.
- Added commands:
  - `/check analyze last`
  - `/check suggest fix`
  - `/check fix last`
  - `/fix last check`
  - `/fix explain`
  - `/fix clear`
- Added natural fix intents such as `why did it fail?`, `suggest a fix`, and
  `fix the tests`.
- Added RAG memory events for fix suggestions without storing full output or
  code.
- Added v0.20 smoke and pytest coverage.

## 19. Safe Project Check Runner

- Added project check contracts in Python and TypeScript:
  - `ProjectCheckRequest`
  - `ProjectCheckCommand`
  - `ProjectCheckResult`
  - `ProjectCheckSafetyResult`
  - `PendingProjectCheck`
  - `ProjectCheckHistoryEntry`
  - `ProjectCheckOutputSummary`
  - `CheckCommandPreset`
- Added safe check engines:
  - `ProjectCheckPresetEngine`
  - `ProjectCheckSafetyEngine`
  - `ProjectCheckRunner`
  - `ProjectCheckConfirmationEngine`
  - `ProjectCheckHistoryEngine`
  - `CheckOutputSummarizer`
- Added `/check` commands for presets, pending, confirm, cancel, last result,
  history, output preview, and safety status.
- Added natural project check intents such as `compile project`, `run tests`,
  `run lint`, and `check this project`; these create pending checks only.
- Kept checks whitelisted, confirmation-first, project-root bounded, and
  `shell=False`.
- Blocked installs, git commands, delete/remove commands, migrations, deploys,
  publishes, and unknown arbitrary commands.
- Added local output storage under `data/project_checks/<check_id>/`.
- Added metadata-only check history under `data/project_check_history.jsonl`.
- Added RAG memory events for check outcomes without storing huge output or
  secrets.
- Added v0.19 smoke and pytest coverage.

## 18. Safe Patch Apply Mode

- Added patch dataclasses and TypeScript contracts:
  - `PatchPlan`
  - `PatchFileChange`
  - `PatchApplyRequest`
  - `PatchApplyResult`
  - `PatchBackup`
  - `PatchRollbackResult`
  - `PatchRiskResult`
  - `PendingPatch`
  - `PatchReviewSummary`
- Added `PatchSafetyEngine` for low/medium/high/blocked risk checks.
- Added `PatchEngine` for Python-only text replacement patch application.
- Added `PatchConfirmationEngine` with exact confirmation and 5-minute expiry.
- Added `PatchBackupEngine` with backups under `data/patch_backups/<patch_id>/`.
- Added `PatchHistoryEngine` with metadata-only JSONL history.
- Added patch commands:
  - `/patch pending`
  - `/patch apply confirm`
  - `/patch cancel`
  - `/patch rollback last`
  - `/patch history`
  - `/patch safety`
- Wired `/edit plan` and `/edit file` to create pending patch plans when safe.
- Added natural `apply that` nudge that shows the confirmation phrase instead of
  applying.
- Added RAG memory event writes after successful patch apply without storing
  full code.
- Added structured patch logs for create, safety, apply, failure, rollback, and
  rollback success events.
- Added v0.18 smoke and pytest coverage.

## 17. Core Decomposition, RAG Cutover, And Routing Cleanup

- Added router boundaries under `fibi/engines/routers/`:
  - `CommandRouter`
  - `ActionRouter`
  - `ChatRouter`
  - `MemoryRouter`
  - `ContextRouter`
  - `ProjectRouter`
  - `VoiceRouter`
  - `ResponsePipeline`
- Wired `FibiCore` through those routers for command, action, chat, context,
  project, voice, and memory paths while preserving old handler bodies.
- Kept stretched greetings and social check-ins local and high-confidence.
- Moved relevant memory retrieval and new direct conversation memory writes to
  the primary local RAG service.
- Added `fibi/rag/rag_memory_service.py` as the beginner-friendly primary RAG
  memory facade.
- Added `LegacyMemoryAdapter` so old memory-style calls can keep working during
  the cutover.
- Added `tools/migrate_legacy_memory_to_rag.py` with dry-run default and JSON
  reports under `data/reports/`.
- Added `MigrationManager` and `WorkerManager` foundations for future cleanup.
- Added structured logging beside existing console route diagnostics.
- Added v0.17 smoke and pytest coverage.

## 16.1 Optional Local RVC Voice Skin

- Added optional, disabled-by-default RVC voice skin settings.
- Added local validation for `.pth` model files and `.index` feature indexes.
- Added `RvcVoiceSkinEngine` adapter with safe fallback to normal edge-tts.
- Added `VoiceCacheEngine` for short converted-line cache keys and clearing.
- Added local commands:
  - `/voice skin status`
  - `/voice skin model <path>`
  - `/voice skin index <path>`
  - `/voice skin backend rvc_python`
  - `/voice skin backend rvc_webui_api`
  - `/voice skin on confirm`
  - `/voice skin off`
  - `/voice skin test`
  - `/voice cache status`
  - `/voice cache clear`

- Added `tools/install_rvc_voice_model.py` to extract only `.pth` and `.index`
  files from a local zip.
- Added `voice_models/README.md`, `requirements-rvc.txt`, and gitignore rules
  for large local voice model/cache files.
- Kept RVC optional, local-only, and non-blocking from the UI's perspective.
- Documented safety notes against unauthorized model distribution or
  impersonation.

## 15.1 Routing Stability And TTS Polish

- Added `RouteDecisionEngine` for explicit route names, reasons, and debug
  snapshots.
- Added `/route last` and `/route test <message>` as local-only debugging
  commands.
- Kept slash commands, local actions, date/time, volume, app/search, memory,
  privacy, project, context, route, and TTS commands out of model routing.
- Added route logs:
  - `NORMALIZED_TEXT`
  - `ACTION_INTENT_CHECKED`
  - `ACTION_INTENT_DETECTED`
  - `ACTION_TYPE`
  - `ACTION_ROUTE_USED`
  - `ROUTE_DECISION`
  - `ROUTE_REASON`
  - `TTS_PRIORITY`

- Replaced vague model fallback wording with clearer local fallback lines.
- Added model timeout cooldown so repeated complex questions do not repeatedly
  wait on a sleeping Ollama route.
- Added `TtsManager` for speech priority and utility-reply skipping.
- Added `/tts stop`, `/tts status`, `/voice output on`, and `/voice output off`.
- Added `tests/smoke_v0151_routing_tts.py`.

## 16. Safe Project Edit Suggestions

- Added v0.16 manual-only coding help.
- Added edit suggestion dataclasses and matching TypeScript interfaces.
- Added `EditSafetyEngine` with low, medium, high, and blocked risk levels.
- Added `DiffGenerator` for unified diffs and copy-paste replacement blocks.
- Added `ProjectEditPlanner` for edit intent detection, target-file planning,
  safe file reads, last suggestion storage, and metadata journaling.
- Added local commands:
  - `/edit plan <request>`
  - `/edit file <relative_path> <request>`
  - `/edit explain last`
  - `/edit copy last`
  - `/edit clear`
  - `/edit safety`

- Added natural edit detection for active projects.
- Preserved the hard v0.16 safety boundary:
  - no file writes
  - no patch application
  - no terminal commands
  - no package installs
  - no secret file edits
  - no autonomous edits

## 1. Initial Project Repair

- Inspected the complete existing Python project and preserved its structure.
- Found the original entry point and repaired broken imports and paths.
- Added the root `app.py` launcher so Fibi runs with:

  ```powershell
  python app.py
  ```

- Added Python package `__init__.py` files where needed.
- Repaired the syntactically broken original Ollama brain module.
- Preserved all existing assets and control modules.

## 2. Floating Desktop Window

- Built the primary interface with PyQt6.
- Added an always-on-top, frameless, translucent desktop window.
- Positioned Fibi near the lower-right desktop area on startup.
- Added dragging through the sprite, bubble, label, and window background.
- Added a text input and send button.
- Added a rounded speech bubble beside the character.
- Kept AI and TTS work in background threads so the UI remains responsive.

## 3. Expressions And Animation

- Added expression support for:
  - idle
  - happy
  - thinking
  - talking
  - sleepy
  - angry

- Added asset lookup in both:
  - `fibi/assets/`
  - `fibi/ui/assets/`

- Missing expressions safely fall back to `idle.png`.
- Added smooth floating movement.
- Added subtle breathing through small sprite scaling.
- Added talking bounce while voice playback is active.
- Added optional blinking through `blink.png`.
- Missing blink artwork is skipped safely.
- Blink intervals are randomized so they feel less mechanical.

## 4. Ollama And Fast Replies

- Connected Fibi to the local Ollama HTTP API.
- Added configurable model and timeout settings in `fibi/settings.py`.
- Set the preferred fast model to `qwen2.5:1.5b`.
- Added model fallback priority:
  1. `qwen2.5:1.5b`
  2. `qwen2.5:3b`
  3. `qwen3:4b`
  4. `qwen3:8b`

- Added a 20-second hard request timeout.
- Limited model output to 60 predicted tokens.
- Reduced model context and conversation history.
- Added instant local replies for `hey`, `hi`, `hello`, `yo`, and `sup`.
- Added one simplified retry when Ollama returns an empty-looking response.
- Added varied local fallback responses when Ollama is missing, slow, or empty.
- Logged the complete Ollama response object when its response field is empty.

## 5. AI Debug Logs

Added logs for:

```text
AI START TIME:
AI END TIME:
AI DURATION SECONDS:
MODEL USED:
ERROR:
RAW AI REPLY:
AFTER MOOD CLEAN:
CLEANED DISPLAY:
TTS TEXT:
CURRENT MOOD:
```

## 6. Response Cleanup

- Added the modular `clean_response()` helper.
- Added optional use of the Python `emoji` package.
- Built emoji-name matching from `emoji.EMOJI_DATA`.
- Added fallback phrase cleanup when the package is missing.
- Removed written emoji descriptions such as:
  - sleepy face
  - smiling face with smiling eyes
  - face with tears of joy
  - red heart
  - sparkles

- Added matching for space, underscore, and hyphen variations.
- Preserved real Unicode emojis.
- Cleaned punctuation and whitespace after phrase removal.
- Applied cleanup before:
  - memory/history storage
  - chat bubble display
  - TTS generation

## 7. Mood Tags And Empty Replies

- Added removal of model mood tags before display and speech:
  - `[idle]`
  - `[happy]`
  - `[thinking]`
  - `[talking]`
  - `[sleepy]`
  - `[angry]`

- Added validation for replies containing only:
  - whitespace
  - mood tags
  - removed emoji descriptions
  - punctuation

- Removed the repeating `I'm here!` parser fallback.
- Added varied fallback lines instead.

## 8. TTS And Sound

- Added optional voice output with `edge-tts` and `pygame`.
- Voice failures no longer crash the application.
- Fibi changes to the talking expression during playback.
- Fibi returns to happy or idle after playback.
- Actual display text and TTS-safe text are handled separately.
- Mixed text has emojis removed before TTS so emoji names are not spoken.
- Emoji-only replies receive natural sounds:
  - laughing emoji -> `hehe`
  - crying emoji -> `wahh`
  - sleepy emoji -> `eepy`
  - heart emoji -> `aww`
  - skull emoji -> `dead.`

- Added optional startup, thinking, and message sound support.
- Missing sound files or pygame are skipped silently.

## 9. Original Mood Engine

- Added keyword-based mood selection.
- Angry/annoyed triggers include error, problem, bug, crash, and failed.
- Happy triggers include thanks, good, cute, and love.
- Thinking triggers include wait, think, search, and loading.
- Sleepy triggers include sleep, tired, and night.
- Speaking always uses the talking expression.

## 10. Life Engine

- Created a dedicated Life Engine.
- Added presence states:
  - idle
  - thinking
  - speaking
  - listening
  - observing

- Added persistent internal moods:
  - happy
  - sleepy
  - curious
  - focused
  - excited
  - annoyed
  - idle

- Added a deterministic mood state machine outside the language model.
- Added expression mapping for moods that do not have dedicated artwork.
- Added randomized idle reactions every 45-120 seconds.
- Idle reactions are blocked while thinking, speaking, or listening.
- Added time-aware late-night reactions.
- Added persistent life state in:

  ```text
  data/fibi_state.json
  ```

- The state stores mood, last user message, and interaction count.

## 11. Memory Engine

- Added a local SQLite Memory Engine.
- Added categorized memories:
  - facts
  - events
  - projects
  - habits
  - beliefs
  - goals
  - important moments

- Added save, duplicate prevention, retrieval, access tracking, and summaries.
- Added local conversation history storage.
- Added cautious learning from explicit phrases such as:
  - `my name is ...`
  - `I am building ...`
  - `I want to ...`
  - `I often ...`
  - `I believe ...`

- Added the SQLite schema in:

  ```text
  fibi/engines/schema.sql
  ```

- Long-term memory is stored locally in:

  ```text
  data/fibi_memory.db
  ```

- Added optional sample memories in `data/sample_memories.json`.
- Sample memories are not imported automatically to avoid false memories.
- Fixed SQLite connection ownership so database handles always close properly.

## 12. Observation Engine

- Added safe foreground-window detection for Windows.
- Added foreground process-name detection.
- Added time-of-day detection:
  - morning
  - afternoon
  - evening
  - night
  - late night

- Added safe fallback behavior when active-window APIs are unavailable.
- No continuous activity timeline is recorded.
- Clipboard reading is disabled by default.
- Clipboard access requires both engine configuration and explicit call permission.

## 13. Personality Engine

- Moved Fibi's identity and core values outside the language model.
- Added the architectural priorities:

  ```text
  Presence > Memory > Personality > Intelligence
  ```

- Added local personality reactions that do not require Ollama.
- Added memory summaries and observations to prepared model context.
- Added strict rules preventing the model from inventing memories or observations.
- Kept replies short, sleepy, playful, curious, supportive, and slightly chaotic.
- Allowed gentle teasing and disagreement.

## 14. Model Engine

- Added a replaceable Model Engine boundary.
- Ollama is treated as a language tool, not Fibi's identity.
- The engine receives context prepared by the Personality Engine.
- Added fast model priority, timeout handling, short outputs, and safe errors.
- Made the `requests` dependency optional for local-only reactions.
- Local personality and memory still work when model access is unavailable.

## 15. Fibi v0.02 Core

- Added `FibiCore` as the engine orchestrator.
- The response path is now:

  1. update presence
  2. sample safe desktop observation
  3. save and retrieve relevant local memories
  4. prepare identity and context through Personality Engine
  5. use a local reaction when possible
  6. call Model Engine only when needed
  7. extract mood tags
  8. clean emoji descriptions
  9. validate empty responses
  10. choose display and TTS text
  11. save conversation/event memory
  12. return to persistent mood

- Wired the PyQt chat worker through `FibiCore`.
- Preserved existing UI, animation, voice, asset, and fallback behavior.

## 16. Shared Types And Documentation

- Added Python engine types in `fibi/engines/types.py`.
- Added matching TypeScript contracts in `fibi/types/fibi.ts`.
- Added architecture documentation in `ARCHITECTURE.md`.
- Updated `README.md` with:
  - setup
  - run command
  - Ollama setup
  - TTS setup
  - assets
  - sounds
  - memory database
  - privacy rules
  - reply pipeline

- Updated both requirements files with current dependencies.

## 17. Safety And Local-First Rules

- No project assets were deleted.
- Existing control modules were preserved.
- Memory remains in a local SQLite database.
- Mood state remains in a local JSON file.
- Ollama remains local-first and optional.
- Clipboard access is opt-in.
- Observation is sampled only when needed.
- Missing models, assets, emoji support, TTS, pygame, and sounds fail safely.

## 18. Verification Completed

- Compiled all Python files successfully with the bundled Python runtime.
- Tested SQLite schema creation, save, retrieval, and connection cleanup.
- Tested cautious memory learning.
- Tested local personality greetings without Ollama.
- Tested model-unavailable fallback behavior.
- Tested emoji-description cleanup and TTS-safe emoji handling.
- Tested clipboard-denied default behavior.
- Tested observation time-of-day behavior.
- Added test files:
  - `tests/test_cleanup.py`
  - `tests/test_engines.py`

`pytest` was not installed in the bundled runtime, so focused smoke tests were
executed directly. The project remains launched from the root with:

```powershell
python app.py
```

## 19. Fibi v0.03 Continuity And Pattern Awareness

- Added `JournalEngine` with migration-safe SQLite journal entries.
- Added startup/shutdown continuity timestamps and session counters.
- Added startup lines based on the time since Fibi was last active.
- Added deterministic local daily journal summaries.
- Added `PatternEngine` for sampled recurring behaviors.
- Added context-aware idle reactions with cooldowns and repeat avoidance.
- Added natural memory hints that only use retrieved trusted memories.
- Added a small evidence-gated opinion layer for gentle disagreement.
- Updated `FibiCore` to combine journal, memory, patterns, personality, local
  opinions, optional Ollama, cleanup, mood, and persistence.
- Added v0.03 pytest coverage and a direct smoke-test runner.
- Expanded privacy documentation: no screenshots, private-message reading,
  notifications, continuous app timeline, or default clipboard access.

## 20. Fibi v0.04 Embodiment And Affection

- Added persistent affection, trust, comfort, mischief, and attachment values.
- Added Attention Engine with reaction-specific cooldowns and intentional silence.
- Added Habit Engine for desktop guarding, cursor watching, tab counting, tiny
  patrols, pretend debugging, and late-night judgment.
- Added click/pet reactions with spam detection and journal events.
- Added drag start/end reactions and persistent validated desktop position.
- Added napping, waking, energy, and new creature presence states.
- Added local success celebrations and short frustration comfort reactions.
- Updated Personality Engine so bond adjusts warmth, teasing, and gentle honesty
  without inventing memories or becoming romantic.
- Added v0.04 Python/TypeScript contracts and direct smoke tests.
- Preserved all privacy boundaries and kept Ollama optional for creature behavior.

## 21. Fibi v0.05 Rituals, Nest, And Continuity

- Added a structured, bond-aware local Reaction Library.
- Added persistent morning, evening, return, project, and shutdown rituals.
- Added a nest requiring three nearby placements before promotion.
- Added saved-position, nest, and default restoration paths.
- Added deterministic time-of-day personality curves.
- Added migration-safe daily summary and project affinity tables.
- Added optional yesterday references and affinity for known projects only.
- Added matching Python/TypeScript contracts and v0.05 smoke tests.
- Preserved local-first privacy and optional Ollama behavior.

## 22. Fibi v0.06 Creature Polish

- Added Motion Engine with fourteen cooldown-safe motion intents.
- Added nonblocking bounce, hop, sway, shake, tilt, stretch, settle, squish,
  recoil, and celebration transforms to the existing PyQt timer.
- Added Timing Engine for emotional pauses and typing styles.
- Added Expression Controller with minimum duration and temporary return state.
- Added bubble typing, auto-hide, duplicate suppression, and TTS hold.
- Added bounded persistent Repetition Guard buffers and silence rules.
- Added optional sound-event mapping with missing-file fallback.
- Added aligned Python/TypeScript contracts and v0.06 smoke tests.
- Preserved local-first privacy boundaries and optional Ollama behavior.

## 23. Fibi v0.07 Dreams And Inner Life

- Added Inner Life Engine for private tiny thoughts, rare thought bubbles, and
  dream fragments.
- Added SQLite tables for `inner_life_entries`, `fibi_dreams`, `preferences`,
  and `opinions` using migration-safe `CREATE TABLE IF NOT EXISTS`.
- Added Dream System for nap-time fragments and rare wake-up dream lines.
- Added Preference Engine for slow local preferences from nest, project,
  late-night, poke, and success patterns.
- Added Opinion Engine v0.02 with evidence-gated playful disagreement.
- Added emotional weighting for success, frustration, tiredness, quit/delete
  signals, late-night work, and known projects.
- Added mood drift for long quiet periods, napping, repeated frustration, and
  success recovery.
- Updated `FibiCore` so model output does not create new project memories and
  dreams/thoughts never become factual memories.
- Added aligned Python/TypeScript contracts and v0.07 smoke tests.
- Preserved local-first privacy boundaries: no screenshots, private-message
  reading, calendar/email integration, continuous surveillance, cloud
  requirement, or autonomous desktop control.

## 24. Fibi v0.08 Trust, Memory Care, And User Control

- Added Memory Care Engine for listing, searching, inspecting, editing,
  deleting, importance changes, category forgetting, export, import validation,
  data clearing, and confirmed reset flows.
- Added Privacy Settings Engine with persistent local permissions in
  `data/fibi_state.json` and migration-safe state preservation.
- Added local slash commands for memory, dreams, privacy, journal summaries,
  preferences, projects, exports, forgetting, and confirmed reset.
- Added natural local memory questions and safe "forget that" behavior using
  the last referenced memory.
- Added Notebook PyQt dialog with memories, journal, dreams, preferences, and
  project sections plus edit/delete/export/clear controls.
- Added memory confidence, emotional weight, source, and updated timestamp
  migration for existing SQLite memory rows.
- Added local export bundles under `data/exports/`.
- Wired privacy settings through observation filtering, journaling, dreams,
  inner thoughts, pattern detection, idle bubbles, Ollama, TTS, sounds, and
  memory learning.
- Added aligned Python/TypeScript contracts and v0.08 smoke tests.
- Preserved local-first privacy boundaries and kept Ollama optional.

## 25. Fibi v0.09 Relationship Memory And Boundaries

- Added Relationship Engine for local non-romantic social stance, familiarity,
  teasing safety, quiet/playful preference, annoyance, warmth, distance, and
  interaction style.
- Added Boundary Engine for soft/hard boundary detection and persistent quiet
  mode.
- Added Social Context Engine to allow, replace, or silence reactions based on
  quiet mode, boundary state, annoyance, familiarity, and teasing safety.
- Added local `/quiet`, `/quiet 30m`, `/quiet off`, `/status`, `/relationship`,
  and `/relationship reset confirm` commands.
- Added short apology behavior with cooldown and no guilt-tripping.
- Added explicit social preference learning for quiet, playfulness, no teasing,
  annoyance, companionship, and no TTS.
- Added Notebook relationship/quiet/boundary summary entries and export fields.
- Extended reaction metadata and aligned Python/TypeScript contracts.
- Added v0.09 smoke tests for boundaries, quiet mode, social filtering,
  relationship reset, command locality, and legacy state preservation.
- Preserved privacy boundaries: no screenshots, private-message reading,
  continuous surveillance, cloud requirement, romance, manipulation, or
  autonomous desktop control.

## 26. Fibi v0.09 Hotfix Fast Reply Router And NVIDIA Provider

- Added a no-observation fast greeting path before memory, journal, patterns,
  dreams, Ollama, or cloud calls.
- Added Model Router with local, optional NVIDIA, optional Ollama, and fallback
  provider results.
- Added optional NVIDIA OpenAI-compatible provider using `NVIDIA_API_KEY` from
  the environment with requests fallback when the OpenAI SDK is unavailable.
- Added Cloud Context Sanitizer to keep NVIDIA prompts minimal and remove local
  paths, secrets, clipboard, raw database rows, journals, dreams, and logs.
- Added cloud privacy settings: `allow_nvidia_api`, `allow_cloud_model`, and
  `cloud_context_level`.
- Added `/model ...` and `/cloud ...` local commands.
- Added `.env.example` and optional `openai` / `python-dotenv` requirements.
- Added debug performance logs for fast path, router duration, provider, model,
  cloud permission, NVIDIA/Ollama duration, fallback use, and final reply time.
- Added direct hotfix smoke tests measuring greetings under 300 ms and proving
  greetings/slash commands do not call Ollama or NVIDIA.
- Preserved local-first defaults: NVIDIA and cloud model use are disabled until
  explicitly enabled.

## 27. Fibi v0.10 Speed, Stability, And Offline Survival

- Added Fast Response Classifier before observation, memory, journal, patterns,
  Ollama, or cloud providers.
- Added Local Micro-Brain for greetings, thanks, goodbye, success, frustration,
  tiny status checks, simple chat, quiet mode, and offline fallback.
- Added Response Budget Engine with category-specific budgets and local timeout
  fallbacks.
- Added provider-agnostic cloud provider base and generic OpenAI-compatible
  provider config.
- Added Model Health Engine and persisted performance metrics for `/model status`
  and `/perf`.
- Added Warmup Engine for background startup checks.
- Added `/cancel`, `/stop`, `/perf`, and `/perf reset`.
- Updated PyQt send flow so cancel commands can pass through while Fibi is busy
  and stale responses are ignored.
- Added TTS timing and skip logs while keeping TTS off the display path.
- Added v0.10 smoke tests proving common inputs stay local and fast with no
  Ollama/cloud calls.
- Preserved cloud-disabled defaults and local-first privacy boundaries.

## 28. Fibi v0.11 Desktop Integration And Daily Launch

- Added App Settings Engine with local `fibi_settings.json` persistence.
- Added system tray integration with show/hide, nap/wake, quiet mode, Notebook,
  Settings, status, privacy, and quit actions.
- Added a simple local Settings dialog and first-run setup flow.
- Added Windows Startup-folder autostart support with explicit confirmation.
- Added Data Health Engine and `/health` command.
- Added Asset Health Engine and `/assets` command.
- Added `FIBI_DATA_DIR` support for portable local state/data.
- Added shutdown clean-state marking and gentle unclean-start recovery.
- Added app-facing `FibiCore` methods for status, settings, model/privacy
  status, nap, wake, shutdown, and health checks.
- Added GUI manual verification checklist at
  `docs/GUI_VERIFICATION_CHECKLIST.md`.
- Added v0.11 smoke tests for settings, first-run, commands, autostart,
  health/assets, data-dir override, and shutdown persistence.
- Preserved local-first defaults, optional models, and privacy boundaries.

## 29. Fibi v0.12 Manual Action Core

- Added local action type definitions with safe, confirmation-required, and
  blocked-for-now risk levels.
- Added persistent Action Settings with safe manual actions enabled and risky,
  terminal, clipboard, file-modification, shutdown, screenshot, and autonomous
  actions disabled by default.
- Added local Action Intent Detector for direct user commands such as opening
  known apps, web searches, YouTube/Wikipedia searches, volume controls,
  time/date, and app-index commands.
- Added Permission Engine to block model-generated actions, autonomous actions,
  terminal commands, file deletion/modification, private-message reading,
  clipboard actions, sending messages, purchases, login, and password actions.
- Added Desktop Action Engine with safe URL opening, local app-index launching,
  media-key volume controls with pyautogui fallback, and time/date replies.
- Added App Index Engine with local `data/app_index.json`, shallow scans of
  Start Menu/Desktop/Program Files locations, optional pywin32 shortcut support,
  and fuzzy search.
- Added Action Confirmation Engine with 30-second pending confirmations and
  `/pending action` / `/cancel action`.
- Added local Action Journal at `data/action_journal.jsonl`.
- Added `/actions`, `/apps`, `/screenshots`, and `/shutdown actions` commands.
- Wired action handling into `FibiCore` before model routing so safe actions do
  not call Ollama/cloud and model output cannot execute actions.
- Added Python and TypeScript action contracts.
- Added `tests/smoke_v012_actions.py` and `tests/test_v012_actions.py`.
- Preserved the rule: Fibi has first safe hands, not autonomous control.

## 30. Fibi v0.13 Voice Command Mode

- Added voice input settings with voice off by default, push-to-talk enabled,
  wake word disabled, no audio saving, and no transcript journaling by default.
- Added Speech Recognition Engine using explicit short listens and safe
  fallbacks for missing dependencies or microphones.
- Added Voice Command Router so transcribed text flows through the same
  `FibiCore` slash/action/model pipeline as typed text.
- Added Voice Health Engine and local commands for `/voice status`, `/listen`,
  `/mic devices`, `/mic test`, `/wake word status`, and `/wake word off`.
- Added PyQt mic button near the text input. Listening runs in a background
  thread so animations continue.
- Added voice action safety behavior: low-confidence action transcripts ask for
  confirmation, risky actions still require normal action confirmation, and
  blocked actions remain blocked.
- Added Python and TypeScript voice contracts.
- Added optional `SpeechRecognition` requirement and documented optional
  `pyaudio` install notes.
- Added `tests/smoke_v013_voice.py` and `tests/test_v013_voice.py`.
- Preserved the rule: ears only open when the user presses the mic button or
  runs `/listen`; no creepy listening and no secret autonomy.

## 31. Fibi v0.14 Context Drop And File Awareness

- Added Context Engine for temporary user-provided context sessions.
- Added File Reader Engine for safe, explicit text/code file drops up to 1 MB.
- Added Secret Sanitizer to mask API keys, tokens, passwords, authorization
  headers, private keys, `.env` style values, and long random secret strings in
  previews and model context.
- Added `/context`, `/context last`, `/context clear`, `/context privacy`,
  `/context add`, `/context remember last confirm`, and `/context forget last`.
- Added `/explain <text>` and `/summarize <text>` context commands that route
  through the normal model path.
- Added long pasted text/code/traceback detection with temporary context capture.
- Added PyQt drag-and-drop file support and a small context chip.
- Added context-aware model hints that use sanitized user-provided context only
  when the user asks about it.
- Added Python and TypeScript context contracts.
- Added `tests/smoke_v014_context.py` and `tests/test_v014_context.py`.
- Preserved privacy boundaries: no screen reading, no automatic clipboard
  reading, no screenshots, no file execution, no recursive folder scans, and no
  long-term memory without explicit confirmation.

## 32. Fibi v0.15 Project Workspace Mode

- Added Project Workspace types and TypeScript contracts.
- Added Project Scanner Engine for safe metadata-only scans of registered
  project folders.
- Added Project Workspace Engine with local `data/project_workspaces.json`
  persistence, active project selection, safe file reads, summaries, notes, and
  forget support.
- Added `/project` commands for add/list/current/switch/scan/files/search/read/
  summary/note/forget/open-vscode/privacy.
- Added project folder drop confirmation via `confirm project`.
- Added sanitized project summary hints for project-aware questions.
- Added secret safety for `.env`, private keys, credential files, and generated
  folders.
- Added `tests/smoke_v015_project_workspace.py` and
  `tests/test_v015_project_workspace.py`.
- Preserved v0.15 boundaries: no edits, no terminal, no package installs, no git
  operations, no full-drive scans, and no autonomous project control.

## 33. Fibi v0.17 Local RAG Memory

- Added `fibi/rag/` with config, embedding providers, SQLite repository, FAISS
  vector store, typed models, and service orchestration.
- Added local deterministic hashing embeddings by default, with optional
  sentence-transformers backend support.
- Added RAG memory add, update, soft delete, search, top-k retrieval,
  conversation context assembly, duplicate detection, configurable thresholds,
  and scoring with similarity, importance, confidence, and recency.
- Added SQLite metadata tables `rag_memories` and `rag_memory_events` in the
  local memory database.
- Added persisted FAISS files under `data/rag/`.
- Added `RAGMemoryEngine` facade for future FibiCore integration.
- Added unit tests and `tests/smoke_v017_rag_memory.py`.
- Preserved local-first boundaries: no cloud services, no remote embeddings,
  and no automatic upload of user memory.

## 34. Fibi v0.18 Safe Startup Bootstrap

- Replaced hidden startup dependency installation with an explicit dependency
  check in `fibi/bootstrap.py`.
- Added `python app.py --install-deps` as an opt-in helper for users who want
  the launcher to run the documented `pip install -r requirements.txt` command.
- Kept normal `python app.py` local-first and non-mutating: missing PyQt6 now
  produces clear setup instructions instead of starting a package install.
- Added unit and smoke tests for dependency detection and help text.

## 35. Fibi v1 RAG Memory Foundations

- Re-read and applied the local project NVIDIA skills `rag-blueprint`,
  `nemo-retriever`, and `rag-eval` as guidance.
- Extended RAG memories with first-class source and provenance fields:
  source id, URI, title, timestamp, metadata, and provenance JSON.
- Added migration-safe SQLite column creation for existing local RAG databases.
- Added offline RAG memory evaluation utilities inspired by `rag-eval`, using a
  local `corpus/` plus `train.json` dataset and deterministic recall/MRR
  metrics instead of cloud judges.
- Added `eval/rag_memory/` with sample personal-memory corpus and query cases.
- Documented the boundary between Fibi's local personal-memory RAG and NVIDIA
  NeMo Retriever's service-backed multimodal document retrieval workflow.
- Added unit and smoke tests for provenance persistence, context source labels,
  and retrieval quality.

## 36. Fibi v0.20 Structured Logging Foundation

- Added `fibi/logging_config.py` for centralized local logging setup.
- Wired `python app.py` to configure logging before PyQt startup.
- Added console and local file logging to `data/fibi.log` by default, with
  `FIBI_LOG_LEVEL` and `FIBI_LOG_FILE` overrides.
- Added a secret-masking filter for common API keys, tokens, passwords, bearer
  tokens, and OpenAI-style `sk-...` keys before records reach handlers.
- Added unit and smoke tests for idempotent setup, file output, and masking.

## 37. Fibi v0.21 Next-Generation Local RAG

- Re-discovered NVIDIA Build Skills from `.agents_OFF/skills` and applied
  `rag-blueprint`, `rag-eval`, and `nemo-retriever` guidance.
- Added migration-safe document and chunk metadata tables for local ingestion.
- Added incremental FAISS append for new memories plus a versioned index
  manifest.
- Added local query rewriting, retrieval cache, hybrid vector/keyword ranking,
  health reporting, and memory expiration support.
- Added local document ingestion for text, Markdown, DOCX, optional PDF, and
  future-ready image/audio/video metadata paths without fake extraction.
- Added background indexing queue for non-blocking document ingestion.
- Added top-level `eval/corpus`, `eval/train.json`, and `eval/benchmark.py`
  with Recall@K, MRR, Precision@K, latency, embedding timing, retrieval timing,
  false-positive counts, and failure reporting.
- Added RAG migration and developer guides.
- Added next-generation RAG unit, smoke, migration, and benchmark tests.
# 23. Windows Build, Installer, And Release Candidate

- Added packaged-aware runtime path resolver in `fibi/runtime_paths.py`.
- Kept development data under `data/` while packaged mode uses
  `%APPDATA%/Fibi Chubi/`.
- Added portable packaged mode with `portable_mode.txt` beside the executable.
- Added `config/default_settings.json` with privacy-safe release defaults.
- Added build metadata via `fibi/build_info.py` and `/version detailed`.
- Updated error reports and logging to use packaged-safe user data folders.
- Finalized `packaging/pyinstaller_fibi.spec` for
  `dist/Fibi Chubi/Fibi Chubi.exe`.
- Added `tools/build_windows.py` and `tools/verify_release.py`.
- Added release/installer docs and `docs/RELEASE_QA_V023.md`.
- Added v0.23 packaged-path unit and smoke tests.
# 29. Command Center, Capability Registry, And Help System

- Updated app/build version to `0.29.0`.
- Added a read-only capability registry for chat, memory, voice, desktop
  actions, projects, patches, checks, browser helper, workflows, issues,
  feedback, support, release/update, and packaging/build tools.
- Added a read-only command registry with categories, descriptions, examples,
  risk levels, confirmation flags, capability ids, and docs paths.
- Added `/help`, `/help search`, `/commands`, `/capabilities`, `/capability`,
  `/permissions`, `/safety`, `/refusals`, `/confirmations`, `/what can you do`,
  and `/beginner guide`.
- Added natural help prompts for command discovery and safety explanations.
- Added a permission overview engine and safety explainer engine.
- Added a simple PyQt Command Center panel with search, command categories,
  capability status, safety notes, and examples.
- Added v0.29 beginner, command, capability, and safety docs plus unit/smoke
  tests.

# 28. Workflow Recipes

- Updated app/build version to `0.28.0`.
- Added workflow recipe domain types across Python and TypeScript mirrors.
- Added built-in recipes for project debugging, safe release builds, beta QA,
  browser outreach research, bug report support bundles, and daily startup
  checks.
- Added workflow safety validation that blocks auto-run, hidden browsing,
  auto-send, auto-apply, install/delete/deploy/upload, secrets, and scraping
  behavior.
- Added workflow state under `data/workflows/`, workflow history, pause/resume,
  cancel, and export to safe report files.
- Linked workflow starts with supervised work sessions without bypassing the
  existing patch/check/browser/action confirmation systems.
- Added short RAG memory event creation on workflow completion only.
- Added `/workflow` commands, `/recipes`, natural recipe prompts, health output,
  and a small GUI/tray Recipes touchpoint.
- Added v0.28 docs, unit tests, and smoke test.

# 27. Safe Browser Helper Mode

- Updated app/build version to `0.27.0`.
- Added browser helper types across Python and TypeScript mirrors.
- Added local browser sessions and notes under `data/browser/`.
- Added browser safety checks for URL schemes, blocked credential/history/cookie
  requests, blocked auto-click/form-submit/send/buy/scrape requests, and
  confirmation-required external URL opening.
- Added user-provided HTML/text extraction with scripts/styles removed.
- Added browser research notes and manual browser checklist support.
- Added `/browser` commands and natural prompt routing for safe browser help.
- Added browser helper status to health/debug output.
- Added small GUI/tray browser helper touchpoint.
- Added v0.27 docs, unit tests, and smoke test.

# 26. Beta Feedback Loop, Local Issue Tracker, And Update Prep

- Updated app/build version to `0.26.0`.
- Added local issue tracking in `data/issues/issues.jsonl`.
- Added `/issue` commands for create, list, last, show, close, reopen, export,
  export all, and support-bundle linking.
- Added natural-language beta report triggers for crashes, broken voice/RVC,
  and bug-report requests.
- Added local beta feedback capture in `data/issues/feedback.jsonl`.
- Extended support bundles with optional masked issue and feedback metadata.
- Added `/release health`, local update-manifest parsing, and safe debug
  commands.
- Added tiny GUI/tray Report issue touchpoint.
- Added v0.26 docs plus unit and smoke tests.
- Updated release zip naming to `Fibi_Chubi_v0.26.0_windows_beta.zip`.

# 25. Real Installer, Beta Distribution, And User Onboarding

- Updated app/build version to `0.25.0`.
- Added Inno Setup installer script at `packaging/inno/FibiChubi.iss`.
- Added `tools/build_installer.py` with graceful missing-Inno instructions.
- Added `tools/make_checksums.py` and release manifest generation.
- Added beta tester guide in `docs/BETA_TESTER_GUIDE_V025.md`.
- Hardened first-launch onboarding language and safe choices.
- Added `/install status`, `/data folder`, `/open data folder`,
  `/open logs folder`, and `/reset instructions`.
- Updated release zip naming to `Fibi_Chubi_v0.25.0_windows_beta.zip`.
- Added v0.25 unit and smoke tests.

# 24. Beta QA, First-Run Polish, And Release Hardening

- Updated app/build version to `0.24.0`.
- Added beta mode setting and `/beta status`, `/beta on`, `/beta off`.
- Added first-run packaged welcome line and `/first run status`.
- Added `/limitations`, `/self test`, and `/support bundle`.
- Hardened error reports with runtime path summary and beta status.
- Added release notes, reset/uninstall docs, and v0.24 QA results.
- Renamed release zip target to `Fibi_Chubi_v0.24.0_windows_beta.zip`.
- Added v0.24 unit and smoke tests.
# Fibi v0.30.3

- Narrowed local conversation fast paths to deterministic greetings and
  high-confidence short social checks.
- Added repeat-aware micro-replies and model escalation diagnostics.
- Added root-aware, secret-safe Gemini environment loading and provider status.
- Repaired Settings tab contrast, grouping, scrolling, and voice processing
  controls.
- Added mock-only routing/provider tests and responsive Settings smoke coverage.
- Updated Windows beta packaging metadata to `0.30.3`.

# Fibi v0.30.4

- Added normalized Gemini provider error categories and session-only health
  states.
- Added one bounded retry with jitter for temporary service and network errors.
- Added a short degraded/rate-limited cooldown that automatically recovers.
- Cached and ranked stable text-generation model candidates per session.
- Added a lightweight Ollama health probe before Gemini fallback.
- Preserved model-router invocation and fallback attempt diagnostics after
  failures.
- Added `/provider reset health` and expanded safe `/provider status` output.
- Disabled RVC only in the isolated demo reset profile.
- Added a local capability response for live-data questions without connected
  tools.
- Added mock-only v0.30.4 unit and smoke coverage.
- Updated Windows beta packaging metadata to `0.30.4`.
