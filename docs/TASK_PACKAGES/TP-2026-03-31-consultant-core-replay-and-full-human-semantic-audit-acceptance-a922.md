# TP-2026-03-31-consultant-core-replay-and-full-human-semantic-audit-acceptance-a922

## Название / цель
Запустить fresh practical replay и полный human semantic audit от текущей repo-side reproof базы, чтобы честно определить product/practical closure без архитектурных допущений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`

## Invariant
- no product or practical closure claim without fresh replay and full human semantic audit
- no baseline refresh from invalid or incomplete acceptance evidence
- no runtime code changes inside acceptance unless a new runtime block is explicitly reopened

## Scope
- fresh replay from current head
- full turn-by-turn human semantic audit
- acceptance summary and failure-family update

## Out of scope
- new runtime fixes without a newly opened runtime TP
- registry-only closure claims

## Touch-list
- acceptance artifacts under `/tmp/booking_quality/...`
- acceptance report docs
- active docs/state/packet only after the acceptance lane closes honestly

## Plan
1. Run guarded replay from current head.
2. Produce full human semantic audit artifacts.
3. Compare against current practical truth `r35f`.
4. If acceptance fails, open the first newly broken runtime block from evidence.
5. If acceptance passes, update closure status honestly.

## DoD
- fresh replay is infra-valid
- full human semantic audit is complete
- product/practical status is stated from evidence, not from repo narrative

## Checks
- `python3 scripts/recovery_execution_guard.py`
- acceptance commands to be fixed on activation with exact run-id and artifact directory

## Evidence
- fresh replay artifact bundle
- manual audit bundle
- acceptance report

## Rollback
- no code rollback in this TP; if acceptance exposes a runtime defect, open a new runtime TP

## No-go
- no `green` claim from stale artifacts
- no baseline refresh without valid acceptance evidence

## Риски / блокеры
- acceptance may expose reopened runtime debt despite repo-side reproof

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- unknown until acceptance evidence is fresh

### Why not in this block
Acceptance determines whether any runtime debt remains.

### Risk if deferred
Practical and product status remain unknown.

### Linked follow-up Task Package(s)
- to be named from acceptance evidence if replay or audit fails

### Expiry / trigger to stop deferral
- stop deferral before any `done`, `green`, or baseline refresh claim

## Next-block contract (mandatory)
### Next block objective
Either close acceptance honestly or open the first new runtime block from fresh evidence.

### First deterministic check command
`python3 scripts/recovery_execution_guard.py`

### Blocked-by conditions
- current reproof block must remain the active repo-side base

### Owner role for closure
Brain / Top Architect
