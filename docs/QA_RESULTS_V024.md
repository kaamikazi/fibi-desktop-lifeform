# Fibi v0.24 QA Results

Date/time: 2026-07-07 Asia/Dhaka

Environment:

- Windows desktop project workspace
- Python 3.12.1
- PyInstaller available
- Dev mode tested
- Packaged build tested through release verifier and GUI smoke

## Automated Checks

- [x] `python -m compileall -q .`
- [x] `python -m pytest -q`
- [x] `python app.py --gui-smoke`
- [x] `python tests\smoke_v023_packaged_paths.py`
- [x] `python tests\smoke_v024_beta_release.py`
- [x] `python tools/build_windows.py --clean --zip`
- [x] `python tools/verify_release.py --gui-smoke`

## Manual GUI QA From v0.22/v0.23

Skipped for direct human visual confirmation in this environment:

- visual mascot placement
- drag feel
- settings dialog hand inspection
- real microphone test
- real RVC model conversion
- real end-user unzip/install flow

Human beta checklist:

1. Open `dist\Fibi Chubi\Fibi Chubi.exe`.
2. Confirm the welcome bubble appears on a clean first run.
3. Run `/first run status`.
4. Run `/self test`.
5. Run `/health gui`.
6. Run `/support bundle`.
7. Confirm the support bundle appears under the user data reports folder.
8. Create `portable_mode.txt` beside the exe and confirm portable `data/` is used.

## Notes

- RVC is intentionally optional and not bundled.
- Cloud remains off by default.
- User data is excluded from the release zip.
