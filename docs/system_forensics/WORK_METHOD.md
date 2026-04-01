# Consultant Core Forensic Work Method

Status: `active`
Baseline snapshot: `8319d9e1` at `2026-03-26T23:04:29+05:00`

## Objective
Replace fragile session memory with durable repo-backed forensic memory.

## Evidence Tags
- `FACT`: directly supported by repository evidence. Must include file references.
- `INFERENCE`: a conclusion derived from one or more facts. Must cite the facts it depends on.
- `UNKNOWN`: evidence is missing or ambiguous. Must not be silently guessed.

## Required Outputs Per Hotspot
Each hotspot file analysis must answer:
- what the file does,
- why it exists,
- who calls it,
- what it reads,
- what it writes,
- where it owns orchestration,
- where it only adapts or projects,
- where it rewrites meaning post-owner,
- what is salvageable,
- what must be demoted or removed,
- what the file's role should be in the target architecture.

## Update Protocol
1. Commit any dirty state that changes hotspot files before analyzing them.
2. Record the analysis in `docs/system_forensics/files/`.
3. Update the ledgers in `docs/system_forensics/ledgers/`.
4. Update `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md` with any new stable conclusions.
5. If archive synthesis/program docs now conflict with fresh deep-audit conclusions, publish an explicit contradiction review before treating the archive as governing.
6. Register new document families in `STRUCTURE.md` and summarize the new forensic state in `STATE.md`.

## Strict Non-Goals
- No runtime behavior fixes.
- No narrative progress claims without documents.
- No closure claims while strategic architecture remains `open`.

## Source Discipline
- Use repo evidence first.
- Use exactly one web search per nontrivial forensic/implementation family when required by canon.
- Record the web search in the Task Package.

## One Web Search For This Family
- Query: `site:docs.arc42.org arc42 template architecture documentation`
- Date/time: `2026-03-26T22:40:00+05:00`
- Primary source: `https://docs.arc42.org/`
- Decision: integrate a layered architecture-forensics document system rather than a single summary file.

## Document Layers
1. Primary deep-audit layer: fresh first-hand system-level research before any outside handoff is treated as authoritative.
2. Executive packet scaffold: top-level docs plus the machine-readable companion for outside readers and future implementation governance.
3. File analyses: one file, one deep document.
4. Ledgers: cross-cut system views that aggregate multiple file analyses.
5. Final synthesis: older deep synthesis and research/program packet that still acts as archive evidence.

## Acceptance For A Finished Analysis Block
A forensic block is acceptable only if:
- the hotspot analysis is evidence-backed,
- at least one ledger changed because of that analysis,
- the final synthesis starter was updated if the finding is system-level,
- and `git diff --check` passes.
