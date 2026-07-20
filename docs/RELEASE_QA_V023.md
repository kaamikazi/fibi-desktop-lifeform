# Fibi v0.23 Release QA

Use this checklist before sharing a Windows release candidate.

## Build

- [ ] Run `python tools/build_windows.py --clean --zip`
- [ ] Confirm `dist/Fibi Chubi/Fibi Chubi.exe` exists
- [ ] Confirm the zip exists under `dist/`
- [ ] Run `python tools/verify_release.py`

## First Run

- [ ] Launch `dist/Fibi Chubi/Fibi Chubi.exe`
- [ ] Confirm Fibi appears
- [ ] Confirm the user data folder is created under `%APPDATA%\Fibi Chubi\`
- [ ] Confirm no writes happen inside the bundled executable payload
- [ ] Ask `hi` and confirm the reply is instant
- [ ] Open Settings
- [ ] Run `/health gui`
- [ ] Run `/voice status`
- [ ] Run `/actions status`
- [ ] Drop a safe text file or use context add
- [ ] Add a test project with `/project add <path>`
- [ ] Start a guided session with `/session start review this project`
- [ ] Close and restart Fibi
- [ ] Export an error report with `/export error report`

## Portable Mode

- [ ] Close Fibi
- [ ] Create `portable_mode.txt` beside `Fibi Chubi.exe`
- [ ] Relaunch Fibi
- [ ] Confirm data is created beside the executable under `data/`
- [ ] Confirm `%APPDATA%\Fibi Chubi\` is not required for portable operation

## Reset And Uninstall

- [ ] Normal reset: delete `%APPDATA%\Fibi Chubi\`
- [ ] Portable reset: delete `<release folder>\data\`
- [ ] Zip uninstall: delete the extracted release folder

## Privacy

- [ ] Confirm cloud remains disabled by default
- [ ] Confirm clipboard observation is disabled by default
- [ ] Confirm screenshots are disabled by default
- [ ] Confirm autonomous actions are disabled by default
- [ ] Confirm RVC is disabled by default
- [ ] Confirm voice input is disabled by default
- [ ] Confirm RVC `.pth` and `.index` files are not bundled
- [ ] Confirm logs, caches, memory DBs, exports, and reports are not bundled

