# Memory Stage 2 Findings

Status: synthetic evidence only. Stage 3 remains blocked.

## Executed Evidence

The committed `stage2-synthetic-2026-08` dataset contains 20 fictional cases.
The explicit synthetic run completed all 20:

| Result | Count |
| --- | ---: |
| Healthy | 15 |
| Needs investigation | 3 |
| Migration blocker | 2 |
| Timeout observations | 2 |
| Reports with unavailable source | 2 |
| Aggregate exact overlap@K | 4 |
| Aggregate exact duplicate pairs | 4 |

The two blocker fixtures deliberately simulate an unavailable source and a
source/normalized timeout. Investigation cases cover contradiction metadata,
missing metadata, and unavailable semantic acceleration. Exact overlap,
paraphrase, source-exclusive, lifecycle exclusion, sensitive/secret exclusion,
deterministic ordering, NumPy fallback, irrelevant retrieval, and empty results
are represented separately.

These numbers are deterministic fixture observations except latency, which is
environment-dependent. They are not measurements of the user's memory stores.

## Interpretation

The synthetic results demonstrate that the Stage 1 normalized view retains all
available fixture candidates, reports exact duplicates without merging, keeps
source differences visible, and degrades safely when semantic acceleration is
missing. The tests also prove temporary databases, indexes, manifests, access
counters, timestamps, and file inventory remain unchanged during comparison.

The findings do not establish real-world overlap, consent mismatch frequency,
deletion consistency, retrieval relevance, or migration value. No local-data
comparison was executed. Therefore no conclusion may be drawn about actual user
memory quality or whether one current store should become authoritative.

## Decision Questions

Before migration, maintainers must review normalized retention, lifecycle and
sensitive exclusion consistency, consent gaps, cross-store duplication,
semantic acceleration benefit, source availability, irrelevant retrieval,
read-only feasibility, deletion design, and metadata completeness. A single
aggregate quality score is intentionally prohibited.

## Stage 3 Entry Criteria

Stage 3 controlled import remains blocked until all of the following exist and
are separately approved:

- verified point-in-time backup and restore rehearsal;
- transactional, idempotent importer with fault-injected rollback;
- explicit duplicate and contradiction review policy;
- complete source-store/table/record mappings and checksums;
- consolidated consent and sensitivity semantics;
- cross-store deletion and derived-index cleanup specification;
- sanitized private local-data evidence that justifies migration;
- user confirmation and a tested rollback release.

A future local-data report must be private, ignored, aggregate-only, and created
only after explicit read and save confirmations. It must never be committed
automatically.
