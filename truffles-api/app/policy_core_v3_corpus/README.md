# policy_core_v3_corpus — corpus tooling

**Status:** PoC tooling. Not in runtime hot path.
**Spec:** [`SPECS/SHADOW_RUN_V3.md`](../../../SPECS/SHADOW_RUN_V3.md) Phase B.3.

This package replays a corpus of messy customer dialogs through
`run_shadow`, using an oracle/drift mock LLM, and produces a histogram
report from the resulting `ComparisonRecord` JSONL.

## Files

| File | Responsibility |
|---|---|
| `schema.py` | Typed `CorpusDialog` / `CorpusTurn`; strict JSONL loader |
| `oracle_llm.py` | Mock LLM modes: `oracle` (verbatim), `drift` (deterministic corruption), `degrade` (always empty) |
| `runner.py` | `run_corpus(...)` — pure async replay of all dialogs through `run_shadow` |
| `aggregator.py` | `aggregate_records` / `aggregate_jsonl_file` / `format_report_text` |

## CLI

- `scripts/policy_core_v3_shadow_corpus_run.py` — read corpus YAML/JSONL, run, write `ComparisonRecord` JSONL.
- `scripts/policy_core_v3_shadow_aggregate.py` — read `ComparisonRecord` JSONL, print histogram.

## Corpus fixture

`truffles-api/tests/corpora/beauty_salon_pilot_v0.jsonl` is the **DRAFT**
internal-pilot corpus. Status field = `"draft"` until the owner reviews and
flips to `"owner_approved"`. SCRIPTED_TECHNICAL_PROOF only — not real
production traffic.

## Invariants

- Pure: aggregator and schema have zero I/O beyond reading user-supplied
  files; runner only calls `run_shadow`.
- No imports from `app.services` or `app.core` (static guard).
- Drift mode produces **deterministic** corruption keyed by dialog/turn so
  re-runs are reproducible.
- All v3 outputs are typed; oracle is `PolicyDecisionV3` not freeform JSON.
