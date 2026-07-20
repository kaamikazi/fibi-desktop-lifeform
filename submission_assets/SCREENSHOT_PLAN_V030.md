# Fibi v0.30 Screenshot Plan

Do not fabricate screenshots. Do not capture private desktop areas. Use the isolated demo profile only.

Prepare first:

```powershell
cd "E:\Fibi chubi"
python tools\reset_demo_profile.py --confirm-demo-reset
$env:FIBI_DATA_DIR="E:\Fibi chubi\demo_runtime"
python app.py
```

Target folder:

```text
submission_assets\screenshots\
```

## 1. Hero desktop presence

- Filename: `submission_assets\screenshots\01_fibi_desktop.png`
- Exact app state: Fibi floating on a clean desktop with chat input visible.
- Exact visible text: chat bubble can show `guarding desktop.` or no private text.
- Crop area: Fibi window plus a little desktop space; avoid taskbar personal items.
- Recommended resolution: 1920x1080 full frame, then crop to 16:9 if needed.
- Privacy check: no notifications, browser tabs, file paths, or personal apps visible.

## 2. Memory Review Center

- Filename: `submission_assets\screenshots\02_memory_review_center.png`
- Exact app state: Memory Review Center open after reset.
- Exact visible text: `Imran prefers Fibi to remain local-first.`, `Presence before intelligence.`, `Demo memory scheduled for deletion.`
- Crop area: Fibi memory review dialog only.
- Recommended resolution: 1600x900 or larger.
- Privacy check: confirm `demo_runtime` was used; no real memories.

## 3. Sensitive-memory refusal

- Filename: `submission_assets\screenshots\03_sensitive_memory_guard.png`
- Exact app state: Chat shows `/memory safety`; optional fake value is visible only if manually typed and reviewed.
- Exact visible text: `secrets never stored. sensitive notes need approval.`
- Crop area: Fibi chat bubble and input area.
- Recommended resolution: 1280x720 or larger.
- Privacy check: only the fake value appears; no real credentials.

## 4. Workflow Recipe in progress

- Filename: `submission_assets\screenshots\04_workflow_recipe.png`
- Exact app state: after `/workflow start Daily Fibi Startup Check` and `/workflow next`.
- Exact visible text: `recipe started: Daily Fibi Startup Check`, `next recipe crumb`, `say: /workflow next`.
- Crop area: chat bubble or workflow visible area.
- Recommended resolution: 1280x720 or larger.
- Privacy check: no project paths or logs.

## 5. Command Center / permission overview

- Filename: `submission_assets\screenshots\05_command_center_permissions.png`
- Exact app state: Command Center open, or chat shows `/permissions`.
- Exact visible text: `permissions:`, `cloud: off`, `memory learning: on`, `patch apply: off`.
- Crop area: dialog or chat bubble only.
- Recommended resolution: 1600x900 or larger.
- Privacy check: verify no API key status or local username is exposed.

## 6. Test and packaged-beta proof

- Filename: `submission_assets\screenshots\06_verified_beta.png`
- Exact app state: terminal or File Explorer showing verified beta proof.
- Exact visible text: `129 passed`, `GUI_SMOKE_OK`, or `Fibi Chubi.exe`.
- Crop area: terminal/File Explorer only, with unrelated folders hidden.
- Recommended resolution: 1920x1080.
- Privacy check: do not show email, tokens, private logs, browser content, or unrelated directories.
