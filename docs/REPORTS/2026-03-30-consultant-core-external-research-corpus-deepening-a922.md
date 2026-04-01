# 2026-03-30 Consultant-Core External Research Corpus Deepening (a922)

## Scope
Correct and deepen `docs/system_forensics/` so it becomes one self-contained executive packet for external researchers, while preserving the older hotspot/ledger/final archive as evidence.

## Outcome
- Status: `done`
- Practical truth: unchanged (`r35f` remains current truth)
- Product closure: still `open`
- Runtime behavior: unchanged

## What changed
1. Published the missing top-level executive packet under `docs/system_forensics/` so canon no longer points to absent files.
2. Reframed `docs/system_forensics/INDEX.md` around external readers first and archive detail second.
3. Made the corpus explicitly explain why earlier external-facing analyses were truthful but still insufficient.
4. Preserved the older `files/`, `ledgers/`, and `final/` material as the detailed evidence archive instead of discarding it.

## What did not change
- No product runtime behavior changed.
- No replay was run.
- No human-semantic verdict changed.
- No architecture implementation slice started.

## Governing conclusion
The repo already had a broad forensic archive, but it was still too mixed and too internal to act as one reliable external-research packet. The corrected top-level corpus now gives outside researchers a readable system narrative while keeping the deeper archive intact as evidence.

## Checks
- required root-level `docs/system_forensics/*` presence check -> `external_research_corpus_ok`
- `git diff --check`
