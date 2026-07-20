# Fibi v0.30 Memory Privacy

Fibi is local-first. Memory is stored locally in SQLite and FAISS files. Memory is not uploaded.

## Consent Controls

- `/memory consent` shows current consent settings.
- `/memory learning off` pauses new memory learning.
- `/memory learning on` resumes safe general learning.
- `/memory consent reset` restores safe defaults.
- `/memory approval required on` requires approval for sensitive memories.
- `/memory approval required off` disables approval prompts, but secrets are still blocked.

## Sensitive Memory Guard

Fibi blocks secrets outright:

- passwords
- API keys
- tokens
- private keys
- recovery codes
- bank/card numbers
- government IDs
- raw private page text
- raw project secrets

Fibi requires clear approval for sensitive personal memories such as exact home address, medical diagnosis, highly private relationship details, or legal details.

## Deletion Audit

Deletes are recorded locally in:

`data/memory/memory_deletion_log.jsonl`

The audit stores the memory id, category, delete time, reason, confirmation flag, and a text hash. It does not store deleted memory text.
