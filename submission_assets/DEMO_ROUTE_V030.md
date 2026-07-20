# Fibi v0.30 Demo Route

Target runtime: 2:30 to 2:45. Hard cap: 2:50.

Before the take:

```powershell
cd "E:\Fibi chubi"
python tools\reset_demo_profile.py --confirm-demo-reset
$env:FIBI_DATA_DIR="E:\Fibi chubi\demo_runtime"
python app.py
```

## 0:00-0:12 - Hook and desktop presence

- Mouse action: start with Fibi visible on a clean desktop; slowly move cursor near her window.
- Input: none.
- Expected screen: small floating Fibi window, chat bubble, input box, toolbar buttons.
- Narration: "This is Fibi. She is not trying to be Siri. She is a tiny desktop lifeform with her own local memory and safety systems."
- Fallback: if GUI fails, show `python app.py --gui-smoke`.
- Max seconds: 12.

## 0:12-0:28 - Model-independent identity

- Mouse action: switch to the architecture visual or README diagram.
- Input: open `submission_assets\architecture_overview_v030.svg`.
- Expected screen: User -> Fibi Desktop Presence -> Router / Orchestrator -> local systems and replaceable language provider.
- Narration: "The language model is replaceable. Fibi's identity, notebook, permissions, mood, and refusals live outside the model."
- Fallback: show the README architecture section.
- Max seconds: 16.

## 0:28-0:48 - Short natural prompt

- Mouse action: click Fibi chat input.
- Input: `heyyyy`
- Expected screen: local social reply such as "tiny creature online." or another short Fibi-style line.
- Narration: "Simple social moments stay local and instant. Presence comes before model power."
- Fallback: type `hi`.
- Max seconds: 20.

## 0:48-1:18 - Memory Review Center

- Mouse action: click the Memory Review button.
- Input: search `local-first`; select `Demo memory scheduled for deletion`; click delete, then confirm if prompted. Optional command fallback: `/memory search local-first`, `/memory delete 5`, `memory delete confirm`.
- Expected screen: fictional memories only; pinned local-first memory; deletion reply says `forgot one memory crumb.`
- Narration: "Her notebook is user-owned. You can search it, pin what matters, and delete a memory instead of begging a model to forget."
- Fallback: use `/memories` and `/memory learning off`, `/memory learning on`.
- Max seconds: 30.

## 1:18-1:34 - Sensitive-memory guard

- Mouse action: return to chat input.
- Input: `/memory safety`. Optional manual prop: type but do not submit `FAKE_DEMO_KEY_NOT_REAL_12345`.
- Expected screen: `memory safety: secrets never stored. sensitive notes need approval. exports skip secrets and raw private text.`
- Narration: "The demo value is fake, but it is shaped like something private. Fibi's memory guard is built to keep secret crumbs out of the notebook."
- Fallback: show `docs\MEMORY_PRIVACY_V030.md`.
- Max seconds: 16.

## 1:34-1:55 - Workflow Recipes

- Mouse action: type in chat input.
- Input: `/workflow list`, then `/workflow start Daily Fibi Startup Check`, then `/workflow next`.
- Expected screen: recipe list, guided step, next command hint. It does not auto-run risky actions.
- Narration: "Workflows are guided rituals, not autopilot. They show steps and preserve confirmation boundaries."
- Fallback: show `docs\WORKFLOW_RECIPES_V028.md`.
- Max seconds: 21.

## 1:55-2:14 - Command Center and permissions

- Mouse action: click Command Center or type commands.
- Input: `/permissions`, then `/safety`.
- Expected screen: permissions list; safety map says cloud is off by default and no hidden browsing or surprise patching.
- Narration: "The permission surface is visible. Browser actions, patches, sending, and destructive work stay behind explicit boundaries."
- Fallback: `/capabilities` and `/refusals`.
- Max seconds: 19.

## 2:14-2:29 - Verification proof

- Mouse action: switch to terminal or File Explorer.
- Input: show recent validation command output or run `python app.py --gui-smoke`; show `dist\Fibi Chubi\Fibi Chubi.exe` if available.
- Expected screen: `GUI_SMOKE_OK`, test pass summary, or packaged beta executable.
- Narration: "This is a tested local beta. The repository is public, and the build artifacts remain local for manual review."
- Fallback: show README testing commands and latest pushed commit.
- Max seconds: 15.

## 2:29-2:42 - Closing

- Mouse action: return to Fibi or architecture visual.
- Input: none.
- Expected screen: Fibi visible or architecture visual.
- Narration: "The model can change. Her identity and history remain. The user owns the notebook. This is Fibi."
- Fallback: none.
- Max seconds: 13.
