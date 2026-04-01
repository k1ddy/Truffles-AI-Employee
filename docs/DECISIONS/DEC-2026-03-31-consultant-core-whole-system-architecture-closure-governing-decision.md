# DEC-2026-03-31 Consultant Core Whole-System Architecture Closure Governing Decision

Status: `accepted_by_explicit_user_instruction`
Date: `2026-03-31`

## Decision
The completed canary root-first sequence is not equivalent to whole-system closure.
From this point forward, consultant-core recovery is governed by a whole-system closure program that treats the canary sequence as evidence and salvage, not as final completion.

The governing architecture is:
- `Single Semantic Owner`
- `Strict Binding Boundary`
- `Canonical Continuity State`
- `First-Class Fact Plane`
- `Adapter-only Legacy Mesh`

Operational consequence:
- runtime control paths must collapse toward one minimal compiled control plane;
- replay and human audit are forbidden until the whole-system architecture blocks close.

## Why this supersedes the previous operating base
The earlier block `1..10` sequence recovered a touched canary envelope.
The system audits still show wider open blocker families:
- distributed semantic ownership
- multiple truth carriers
- boundary semantic leakage
- mixed pack/runtime behavior
- live legacy compatibility mesh
- duplicated operational entrypoints

Therefore the next move is not replay.
The next move is whole-system architecture closure.

## Mandatory order
1. `Decision Freeze`
2. `Authority Freeze`
3. `Fact Contract Schema`
4. `Narrow Fact-Family Cutover`
5. `Continuity / State Normalization`
6. `Post-Owner Semantic Constriction`
7. `Boundary Constriction`
8. `Pack / Runtime Separation Completion`
9. `Legacy Mesh Drain`
10. `Shadow Lane Elimination`
11. `Operational Entrypoint Dedupe`
12. `Whole-System Governance Closure`
13. `Replay + Full Human Semantic Audit`

## Non-negotiable sequencing corrections
- Do not start from a visible family symptom.
- Do not run replay before architecture closure.
- Do not do broad boundary tightening before explicit fact scope exists.
- Do not force journal-first rewrite before continuity normalization around current `DialogState` nucleus.
- Do not delete legacy surfaces without caller proof.
- Do not update canon/state after micro-fixes inside an unfinished block.
  Canon/state/report sync happens only after one full block closes.

## First real implementation slice
The first admissible implementation slice after freeze is:
1. `Authority Freeze`
2. `Fact Contract Schema`
3. `Narrow Fact-Family Cutover` for `location / hours / parking`

Why first:
- it targets the largest open missing architecture object;
- it intersects the current visible residue with the highest-leverage shared mechanism;
- it avoids fake progress through local patches.

## Current canonical continuity decision
Short-term canonical continuity nucleus remains around `DialogState`.
`TurnJournalV1` and `ConversationProjectionV1` remain target-state direction, not the immediate first plumbing pivot.

## Runtime-law consequences
- Only the policy-core owner path may write semantic meaning.
- Binding may narrow/deny/authorize; it may not widen semantic or fact scope.
- Boundary may validate/deny/degrade/preserve; it may not mint meaning.
- Legacy modules may transport, adapt, shadow-compare, or observe; they may not co-own semantic, continuity, or fact scope.
- Compatibility carriers may exist only as explicitly registered derived/adaptor carriers with deletion owner and expiry criteria.

## Final completion rule
Whole-system recovery is not done while any of the following remain:
- more than one live semantic writer
- more than one mutable continuity writer
- any fact widening outside the fact contract
- any boundary semantic repair lane
- any legacy surface with unclear authority
- any duplicated operational entrypoint for one mechanism
- any hidden/shadow lane that can still affect runtime

## Evidence anchors
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
