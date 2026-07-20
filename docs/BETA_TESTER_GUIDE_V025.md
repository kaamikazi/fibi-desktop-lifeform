# Fibi v0.25 Beta Tester Guide

Current beta artifact names may be newer than this historical guide. For v0.30,
use `Fibi_Chubi_v0.30.0_windows_beta.zip` and see
`docs/BEGINNER_GUIDE_V029.md` for first commands and
`docs/MEMORY_REVIEW_CENTER_V030.md` plus `docs/SAFETY_MODEL_V029.md` for memory and safety rules.

Fibi is a tiny desktop lifeform for Windows. She is local-first, sleepy, playful,
and intentionally cautious.

## Install

Portable zip:

1. Extract `Fibi_Chubi_v0.25.0_windows_beta.zip`.
2. Open the extracted `Fibi Chubi` folder.
3. Run `Fibi Chubi.exe`.

Installer, if provided:

1. Run `Fibi_Chubi_Setup_v0.25.0.exe`.
2. Choose whether to create a Desktop shortcut.
3. Launch Fibi from Start Menu or Desktop.

## What To Test

- first launch onboarding
- `/first run status`
- `/self test`
- `/health gui`
- fast greeting replies
- settings window
- `/support bundle`
- portable mode with `portable_mode.txt`
- reset/uninstall instructions

## What Not To Expect Yet

- full installer polish
- wake word
- browser automation
- autonomous computer control
- bundled RVC voice model
- cloud assistant behavior

## Privacy

Cloud is off by default. Clipboard observation, screenshots, voice input, RVC,
and autonomous actions are off unless explicitly enabled. User data is stored
locally under `%APPDATA%\Fibi Chubi\` or portable `.\data\`.

## Support Bundle

Inside Fibi, run:

```text
/support bundle
```

This creates a safe diagnostic zip in the reports folder. It masks obvious
secrets and excludes memory databases, voice models, `.env`, and project source.

## Reset And Uninstall

See `docs/RESET_AND_UNINSTALL.md`.

Short version:

- normal data: `%APPDATA%\Fibi Chubi\`
- portable data: `<release folder>\data\`
- zip uninstall: delete the extracted folder
- installer uninstall: use Windows Apps/Programs uninstall

## Optional RVC Voice Skin

Place local voice models in `%APPDATA%\Fibi Chubi\voice_models\` or portable
`.\data\voice_models\`, then configure:

```text
/voice skin model <path-to-model.pth>
/voice skin index <path-to-model.index>
/voice skin backend rvc_python
/voice skin on confirm
```

If RVC is unavailable, Fibi falls back to normal edge-tts.
