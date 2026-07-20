# Fibi Chubi v0.30 Installer Notes

v0.30 can ship as a portable zip first, with an optional Inno Setup installer:

1. Build with `python tools/build_windows.py --clean --zip`.
2. Share `dist/Fibi_Chubi_v0.30.3_windows_beta.zip`.
3. If Inno Setup is available, also share `dist/installers/Fibi_Chubi_Setup_v0.30.3.exe`.
4. User extracts the folder and runs `Fibi Chubi.exe`, or runs the installer.

## User Data

Normal packaged mode stores writable data in:

`%APPDATA%\Fibi Chubi\`

Portable mode is enabled by creating this file beside `Fibi Chubi.exe`:

`portable_mode.txt`

When portable mode is on, Fibi stores writable data in:

`<release folder>\data\`

## Shortcuts

The Inno Setup installer creates a Start Menu shortcut and optionally creates a
Desktop shortcut. It does not enable autostart.

## Uninstall

For zip releases, delete the extracted `Fibi Chubi` folder.

To reset user data, close Fibi and delete:

`%APPDATA%\Fibi Chubi\`

For portable mode, delete:

`<release folder>\data\`

## Voice Models

RVC voice model files are intentionally not bundled. They can be large and are
user-specific. Place local models under:

`%APPDATA%\Fibi Chubi\voice_models\`

or, in portable mode:

`<release folder>\data\voice_models\`

Then configure them inside Fibi:

```text
/voice skin model <path-to-model.pth>
/voice skin index <path-to-model.index>
/voice skin backend rvc_python
/voice skin on confirm
```

If the RVC backend or model files are unavailable, Fibi falls back to normal
edge-tts voice.
