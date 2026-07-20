# Fibi v0.30 Repository Safety Audit

- Audit date: 2026-07-20
- Project root: E:\Fibi chubi
- Files considered by Git before staging: 409
- Text files scanned for secrets: 395
- Final audit result: PASS_WITH_WARNINGS

## Excluded Runtime/Private Paths
- data/
- voice_models/
- .venv-rvc/
- build/
- dist/
- .pytest_cache/
- __pycache__/
- .git_empty_backup_*
- .gitignore.pre_build_week_backup*
- *.db
- *.sqlite
- *.sqlite3
- *.log
- *.tmp
- *.pem
- *.key
- *.token
- *.secret

## Possible Secret Findings
- None found in files eligible for tracking.

## Reviewed False-Positive Warnings
- .agents/skills/rag-blueprint/references/deploy/helm-openshift.md:30 - Assigned secret value pattern/example only - passwo..._KEY
- .agents/skills/rag-blueprint/references/deploy/helm-openshift.md:31 - Assigned secret value pattern/example only - passwo..._KEY
- fibi/engines/secret_sanitizer.py:19 - Assigned secret value pattern/example only - SECRET...le(r
- fibi/engines/sensitive_memory_guard.py:14 - Assigned secret value pattern/example only - API_KE...le(r
- fibi/engines/sensitive_memory_guard.py:23 - Assigned secret value pattern/example only - SECRET...le(r
- fibi/settings.py:61 - Assigned secret value pattern/example only - API_KE...env(
- tests/smoke_v014_context.py:93 - Assigned secret value pattern/example only - API_KE...int(
- tests/smoke_v015_project_workspace.py:60 - Assigned secret value pattern/example only - API_KE...key}
- tests/smoke_v015_project_workspace.py:125 - Assigned secret value pattern/example only - secret...ond(
- tests/smoke_v016_project_edits.py:64 - Assigned secret value pattern/example only - secret...ond(
- tests/smoke_v030_memory_review.py:32 - Assigned secret value pattern/example only - secret...ory(
- tests/test_v020_check_fix_suggestions.py:74 - Assigned secret value pattern/example only - secret...sis(
- tests/test_v030_memory_review.py:61 - Assigned secret value pattern/example only - secret...ory(
- tests/test_v030_memory_review.py:62 - Assigned secret value pattern/example only - API_KE...key}

## Privacy Findings
- Runtime memory, logs, reports, voice caches, voice models, build outputs, generated release artifacts, and old .git backups are excluded by .gitignore.
- .env.example remains eligible and contains placeholders only.
- Test fixtures use placeholder or runtime-assembled dummy values rather than contiguous real-looking provider keys.
- SECURITY.md, PRIVACY.md, and CONTRIBUTING.md were added without personal email addresses or secrets.
- No remote upload, GitHub repository creation, or push was performed.

## Large File Findings
- >100MB: 344.93 MB - .venv-rvc\Lib\site-packages\rvc_python\base_model\rmvpe.onnx
- >100MB: 293.52 MB - .venv-rvc\Lib\site-packages\torch\lib\torch_cpu.dll
- >100MB: 180.73 MB - .venv-rvc\Lib\site-packages\rvc_python\base_model\hubert_base.pt
- >100MB: 172.79 MB - .venv-rvc\Lib\site-packages\rvc_python\base_model\rmvpe.pt
- >100MB: 154.17 MB - dist\Fibi_Chubi_v0.30.0_windows_beta.zip
- >100MB: 154.14 MB - dist\Fibi_Chubi_v0.29.0_windows_beta.zip
- >100MB: 154.12 MB - dist\Fibi_Chubi_v0.28.0_windows_beta.zip
- >100MB: 154.09 MB - dist\Fibi_Chubi_v0.27.0_windows_beta.zip
- >100MB: 154.07 MB - dist\Fibi_Chubi_v0.26.0_windows_beta.zip
- >100MB: 154.04 MB - dist\Fibi_Chubi_v0.25.0_windows_beta.zip
- >100MB: 154.04 MB - dist\Fibi_Chubi_v0.24.0_windows_beta.zip
- >100MB: 154.04 MB - dist\Fibi_Chubi_v0.23.0_windows_rc.zip
- >100MB: 114.79 MB - .venv-rvc\Lib\site-packages\llvmlite\binding\llvmlite.dll
- >25MB: 87.82 MB - voice_models\fibi_rvc\model.index
- >25MB: 84.87 MB - .venv-rvc\Lib\site-packages\torchcrepe\assets\full.pth
- >25MB: 57.05 MB - dist\Fibi Chubi\_internal\ctranslate2\ctranslate2.dll
- >25MB: 52.67 MB - voice_models\fibi_rvc\model.pth
- >25MB: 48.71 MB - dist\Fibi Chubi\_internal\faiss_cpu.libs\libopenblas.dll
- >25MB: 34.04 MB - .venv-rvc\Lib\site-packages\numpy\.libs\libopenblas.FB5AE2TYXYH2IJRDKGDGQ3XBKLKTF43H.gfortran-win_amd64.dll
- >25MB: 31.51 MB - .venv-rvc\Lib\site-packages\parselmouth.cp310-win_amd64.pyd
- >25MB: 28.47 MB - .venv-rvc\Lib\site-packages\torch\lib\torch_cpu.lib
- >25MB: 27.86 MB - dist\Fibi Chubi\_internal\speech_recognition\pocketsphinx-data\en-US\language-model.lm.bin
- >25MB: 26.88 MB - .venv-rvc\Lib\site-packages\faiss_cpu.libs\openblas-34e6e391ae70f97921193cc485380a5a.dll
- >5MB: 19.68 MB - dist\Fibi Chubi\_internal\PyQt6\Qt6\bin\opengl32sw.dll
- >5MB: 19.47 MB - dist\Fibi Chubi\_internal\numpy.libs\libscipy_openblas64_-63c857e738469261263c764a36be9436.dll
- >5MB: 19.22 MB - .venv-rvc\Lib\site-packages\scipy.libs\libscipy_openblas-f07f5a5d207a3a47104dca54d6d0c86a.dll
- >5MB: 18.32 MB - .venv-rvc\Lib\site-packages\av.libs\avcodec-62-0f4d449c1bbaaa5eeb9f8a10b4cc7e85.dll
- >5MB: 17.94 MB - .venv-rvc\Lib\site-packages\torch\lib\torch_python.dll
- >5MB: 17.11 MB - dist\Fibi Chubi\Fibi Chubi.exe
- >5MB: 17.11 MB - build\pyinstaller_fibi\Fibi Chubi.exe
- >5MB: 16.79 MB - build\pyinstaller_fibi\Fibi Chubi.pkg
- >5MB: 16.76 MB - build\pyinstaller_fibi\PYZ-00.pyz
- >5MB: 11.98 MB - .venv-rvc\Lib\site-packages\av.libs\libx265-7e74dd5103fd9dad5114dffeefd474ce.dll
- >5MB: 10 MB - dist\Fibi Chubi\_internal\PyQt6\Qt6\bin\Qt6Core.dll
- >5MB: 9.1 MB - dist\Fibi Chubi\_internal\PyQt6\Qt6\bin\Qt6Gui.dll
- >5MB: 8.4 MB - .venv-rvc\Lib\site-packages\torch\lib\sleef.lib
- >5MB: 7.9 MB - dist\Fibi Chubi\_internal\hf_xet\hf_xet.pyd
- >5MB: 7.47 MB - dist\Fibi Chubi\_internal\PIL\_avif.cp312-win_amd64.pyd
- >5MB: 7.25 MB - .venv-rvc\Lib\site-packages\av.libs\libSvtAv1Enc-5eeef79489c86980df49968253b5be77.dll
- >5MB: 7.05 MB - dist\Fibi Chubi\_internal\tokenizers\tokenizers.pyd
- >5MB: 6.99 MB - .venv-rvc\Lib\site-packages\faiss\_swigfaiss.cp310-win_amd64.pyd
- >5MB: 6.92 MB - dist\Fibi Chubi\_internal\faiss\faiss.dll
- >5MB: 6.68 MB - dist\Fibi Chubi\_internal\python312.dll
- >5MB: 6.28 MB - dist\Fibi Chubi\_internal\PyQt6\Qt6\bin\Qt6Widgets.dll
- >5MB: 5.51 MB - .venv-rvc\Lib\site-packages\scipy\optimize\_highspy\_core.cp310-win_amd64.pyd
- >5MB: 5.49 MB - .venv-rvc\Lib\site-packages\av.libs\avfilter-11-780a5681e7b21881ef585cd5ce000321.dll
- >5MB: 5.47 MB - build\pyinstaller_fibi\xref-pyinstaller_fibi.html
- >5MB: 5.4 MB - dist\Fibi Chubi\_internal\Pythonwin\mfc140u.dll
- >5MB: 5.24 MB - dist\Fibi Chubi\_internal\faiss\_swigfaiss.pyd
- >5MB: 5.01 MB - dist\Fibi Chubi\_internal\pydantic_core\_pydantic_core.cp312-win_amd64.pyd
- >5MB: 5 MB - .venv-rvc\Lib\site-packages\pydantic_core\_pydantic_core.cp310-win_amd64.pyd

## Action Taken
- Preserved unusable .git directory as .git_empty_backup_2026_07_20_2.
- Initialized a fresh local Git repository on branch main.
- Hardened .gitignore before staging.
- Reworked dummy secret test fixtures to avoid contiguous real-looking keys.
- Added minimal SECURITY.md, PRIVACY.md, and CONTRIBUTING.md.
- Generated this masked repository safety audit.

## Final Audit Result
PASS_WITH_WARNINGS
