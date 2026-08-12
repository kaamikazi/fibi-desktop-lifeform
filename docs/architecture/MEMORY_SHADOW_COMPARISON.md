# Memory Shadow Comparison

Status: Stage 1 compatibility facade; superseded for new diagnostics by the
[Stage 2 comparison](MEMORY_STAGE_2_COMPARISON.md).

`MemoryShadowComparison` characterizes the legacy adapter, RAG adapter, and
normalized query result without changing production retrieval. It executes
only when a caller explicitly configures it with
`MemoryShadowSettings(enabled=True)`.

## Safe Metrics

The result contains only candidate counts, source/category distributions,
duplicate count, missing-consent count, ranking agreement, failure-category
counts, and elapsed milliseconds. It contains no query, memory text, prompt,
provider response, private path, or database row.

Normal runtime composition no longer imports or constructs this object.
Automated tests use synthetic records only. The compatibility command delegates
to the Stage 2 suite:

```powershell
python tools/run_memory_shadow_fixture.py
```

The tool does not open Fibi's data directory and prints aggregate JSON only. There is
no production command, startup hook, background worker, environment-only
toggle, provider call, memory write, or report file.

## Limits

This facility is not Stage 2 dual-read production comparison. Ranking agreement
uses normalized synthetic text in process only and never includes that text in
the returned metric. It does not decide authority, merge duplicates, resolve
contradictions, or feed provider context.

## Removal

Remove the compatibility classes after all Stage 1 callers are retired. The
Stage 2 service shares this module to avoid a parallel comparison framework.
Removal needs no data migration.
