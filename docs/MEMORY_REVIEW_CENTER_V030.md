# Fibi v0.30 Memory Review Center

Fibi can remember, but the user owns the notebook.

## Commands

- `/memories` lists visible local memories.
- `/memory search <term>` searches local RAG memory.
- `/memory show <id>` shows source, confidence, approval, and text.
- `/memory approve <id>` approves a pending sensitive memory.
- `/memory pin <id>` and `/memory unpin <id>` mark useful memories.
- `/memory archive <id>` hides a memory without deleting it.
- `/memory edit <id> <new text>` stages an edit. Say `memory edit confirm`.
- `/memory delete <id>` stages a delete. Say `memory delete confirm`.
- `/memory delete category <category>` stages a broad delete. Say `memory delete confirm`.
- `/memory export` writes local JSON and Markdown exports under `data/reports`.
- `/memory health` shows RAG memory count, approval count, vector index status, cache, storage path, and learning status.

## GUI

Use the `Memory` button or tray `Memory Review` item.

The panel shows learning status, search, category filtering, memory details, approve, pin, archive, delete, export, and safety notes.

## Export Rules

Exports exclude secrets, raw private page text, raw project source, deleted memories, archived memories by default, and internal embeddings.
