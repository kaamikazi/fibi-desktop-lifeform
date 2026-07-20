# Fibi v0.30 Precommit Validation

- Date: 2026-07-20
- Project root: E:\Fibi chubi

## Results

| Command | Result | Notes |
| --- | --- | --- |
| `python -m compileall -q .` | ATTEMPTED_TIMEOUT | Timed out while traversing ignored heavyweight folders such as `.venv-rvc`, `build`, `dist`, `data`, and `voice_models`; no code failure was reported before timeout. |
| `python -m compileall -q -x "(\.git|\.venv-rvc|build|dist|data|voice_models|__pycache__|\.pytest_cache)" .` | PASS | Source-only compile check completed successfully. |
| `python -m pytest -q` | PASS | 129 passed, 3 warnings. Warnings: pygame/pkg_resources deprecation, speech_recognition `aifc` deprecation, speech_recognition `audioop` deprecation. |
| `python app.py --gui-smoke` | PASS | Returned `GUI_SMOKE_OK`; FAISS loaded through non-AVX2 fallback. |
| `python tests\smoke_v029_command_center.py` | PASS | Command center smoke passed. |
| `python tests\smoke_v030_memory_review.py` | PASS | Memory review smoke passed. |

## Skipped Checks

- Full Windows build was not rerun in this repository initialization step because release artifacts already existed and build outputs are intentionally ignored for the source repository.
- No commands that upload, deploy, send email, call paid APIs, or mutate external systems were run.

## Final Validation Result

PASS_WITH_WARNINGS
