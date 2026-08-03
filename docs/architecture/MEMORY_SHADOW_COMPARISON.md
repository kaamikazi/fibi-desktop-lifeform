# Memory Shadow Comparison

Status: development-only and disabled by default.

`MemoryShadowComparison` characterizes the legacy adapter, RAG adapter, and
normalized query result without changing production retrieval. It executes
only when a caller explicitly configures it with
`MemoryShadowSettings(enabled=True)`.

## Safe Metrics

The result contains only candidate counts, source/category distributions,
duplicate count, missing-consent count, ranking agreement, failure-category
counts, and elapsed milliseconds. It contains no query, memory text, prompt,
provider response, private path, or database row.

Normal runtime composition creates the object with `enabled=False` and never
calls `compare`. Automated tests use synthetic records only. A developer may
run the explicit synthetic fixture:

```powershell
python tools/run_memory_shadow_fixture.py
```

The tool does not open Fibi's data directory and prints metrics only. There is
no production command, startup hook, background worker, environment-only
toggle, provider call, memory write, or report file.

## Limits

This facility is not Stage 2 dual-read production comparison. Ranking agreement
uses normalized synthetic text in process only and never includes that text in
the returned metric. It does not decide authority, merge duplicates, resolve
contradictions, or feed provider context.

## Removal

Remove the `memory_shadow_comparison` composition field and
`fibi/memory/shadow_comparison.py`. Because the comparison writes nothing and
is off by default, removal needs no data migration.
