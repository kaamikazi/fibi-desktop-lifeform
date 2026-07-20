# Fibi Chubi Packaging

v0.30 prepares the Windows beta distribution flow plus Memory Review docs.

Build:

```powershell
python tools/build_windows.py --clean --zip
```

Output:

```text
dist/Fibi Chubi/Fibi Chubi.exe
dist/Fibi_Chubi_v0.30.4_windows_beta.zip
dist/installers/Fibi_Chubi_Setup_v0.30.4.exe
```

Rules:

- bundle app code, UI assets, docs, config templates, and version metadata
- do not bundle user memory databases
- do not bundle logs, reports, exports, caches, or temp audio
- do not bundle `.env` files
- do not bundle RVC `.pth` or `.index` voice model files by default
- keep `python app.py` working for development
- keep packaged app data writable outside the bundled executable directory

Runtime data:

- normal packaged mode: `%APPDATA%\Fibi Chubi\`
- portable mode: create `portable_mode.txt` beside `Fibi Chubi.exe`, then data goes to `.\data\`

Verify:

```powershell
python tools/verify_release.py
python tools/make_checksums.py
python tools/build_installer.py
```
