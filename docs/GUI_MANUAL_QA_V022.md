# Fibi v0.22 Manual GUI QA

Use this checklist from the project root after installing dependencies.

- [ ] Launch with `python app.py`.
- [ ] Greeting appears without crash.
- [ ] Greeting/local `hi` response appears under 300ms before TTS.
- [ ] Drag Fibi around the desktop.
- [ ] Click/pet Fibi.
- [ ] Use `/nap`.
- [ ] Use `/wake`.
- [ ] Send a typed message.
- [ ] Use `/status`.
- [ ] Open Settings.
- [ ] Open Notebook.
- [ ] Open Health panel.
- [ ] Toggle voice output on/off.
- [ ] Press mic button with voice input off.
- [ ] Use `/voice status`.
- [ ] Use `/voice skin status`.
- [ ] Use `/voice skin test` if local RVC backend is configured.
- [ ] Drop a small text file.
- [ ] Drop a folder and confirm project.
- [ ] Use `/project summary`.
- [ ] Create an edit suggestion with `/edit file ...`.
- [ ] Inspect `/patch pending`.
- [ ] Use `/check presets`.
- [ ] Start a session with `/session start review this project`.
- [ ] Continue with `/session continue`.
- [ ] Close Fibi and reopen.
- [ ] Confirm window position restores.
- [ ] Confirm shutdown persists state.
- [ ] Run `python app.py --gui-smoke`.
- [ ] Export report with `/export error report`.
