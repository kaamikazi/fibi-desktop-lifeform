# Fibi v0.24 Beta Release Notes

Fibi is a tiny desktop lifeform for Windows. She floats on the desktop, chats in
a small bubble, keeps local memory, and tries to feel like a soft little
roommate instead of a corporate assistant.

## What Works

- PyQt6 floating desktop window
- draggable mascot window
- local chat routing and fast greetings
- optional Ollama model use
- local RAG memory
- health panel and `/health gui`
- startup diagnostics
- safe support bundle export
- Windows PyInstaller build
- zip release candidate
- portable mode with `portable_mode.txt`

## Safe Defaults

- cloud off
- clipboard observation off
- screenshots off
- autonomous actions off
- voice input off
- RVC voice skin off
- project checks require confirmation
- user data kept outside the bundled app folder

## Run

Development:

```powershell
python app.py
```

Packaged:

```powershell
dist\Fibi Chubi\Fibi Chubi.exe
```

## Privacy Notes

Fibi stores user data locally. Normal packaged mode uses `%APPDATA%\Fibi Chubi\`.
Portable mode uses `<release folder>\data\`.

The release zip must not contain memory databases, logs, reports, caches, `.env`
files, or voice model files.

## Optional RVC Voice Skin

RVC model files are not bundled. Place local models under
`%APPDATA%\Fibi Chubi\voice_models\` or portable `.\data\voice_models\`.

Then configure:

```text
/voice skin model <path-to-model.pth>
/voice skin index <path-to-model.index>
/voice skin backend rvc_python
/voice skin on confirm
```

If RVC is missing or fails, Fibi falls back to normal edge-tts.

## Known Limitations

- RVC requires optional local setup
- Ollama is optional and may be unavailable
- voice input needs microphone dependencies
- full installer is not built yet
- wake word is not enabled
- browser automation is not implemented
- autonomy is disabled
- cloud is off by default

## Troubleshooting

Run these inside Fibi:

```text
/first run status
/self test
/health gui
/startup diagnostics
/support bundle
```

Support bundles are written to the reports folder in Fibi's user data directory.
They mask obvious secrets and exclude memory databases, voice models, and source
project files.

