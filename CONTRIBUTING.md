# Contributing

Fibi is a local-first Python desktop companion project.

## Setup

```powershell
python -m pip install -r requirements.txt
python app.py
```

Optional voice, RVC, and RAG dependencies may require their own setup files.

## Tests

Run the core validation before opening a pull request:

```powershell
python -m compileall -q .
python -m pytest -q
python app.py --gui-smoke
```

## Privacy Rules

- Do not commit `.env` files.
- Do not commit API keys, passwords, tokens, private keys, cookies, or credentials.
- Do not commit runtime data from `data/`.
- Do not commit memory databases, logs, reports, support bundles, voice caches, model files, build outputs, release ZIPs, or executables.
- Use placeholders in examples.
- Keep pull requests source-focused and local-first.
