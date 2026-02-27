# TP-2026-02-22-universal-control-plane-v1-phase8-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE8
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE7
- `UNLOCKS`: UCPV1-PHASE9

## Название/цель
Universal Control Plane v1 / Phase 8: Knowledge Studio + Pack Compiler, чтобы контур `Draft -> Validate -> Publish -> Rollback` был полностью управляем через Console и блокировал publish при нарушении minimum data contract.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/VERTICAL_PACK_KIT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase7-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/knowledge_*`
  - `truffles-api/app/services/reference_pack_*`
  - `truffles-api/tests/*knowledge*`
  - `truffles-api/tests/*onboarding*`
- `Baseline commands`:
  - `rg -n "knowledge|publish|rollback|draft|validate|pack" truffles-api/app`
  - `rg -n "knowledge|publish|rollback|draft|validate" truffles-api/tests`
  - `rg -n "knowledge" SPECS/CONTROL_PLANE.md SPECS/CONSULTANT.md`
- `FACT findings`:
  - Phase8 execution required after Phase7 pass.
  - Must verify current draft/publish/rollback coverage and identify contract gaps before code changes.
- `Detected drift (docs vs code)`: to be validated at phase8 start

## One web search (mandatory before implementation)
- **Query (exact):** `knowledge publishing workflow draft validate publish rollback contract gate best practices`
- **Date/time (local):** to be executed at phase8 start
- **Why this query is precise:** фокус на жизненном цикле публикации знаний и fail-closed контрактных блокировках.
- **Sources opened (from this query):**
  - to be filled at phase8 start
- **Existing solutions found:** to be filled at phase8 start
- **Decision:** to be filled at phase8 start
- **Rejected options:** to be filled at phase8 start
- **Open questions:** to be filled at phase8 start

## Root cause (mandatory)
- **Symptom:** B08 still planned and not закрыт как отдельный evidence-backed блок.
- **Minimal reproduction:** to be defined at phase8 start based on FACT pre-check.
- **Evidence to capture:** compile/publish/rollback checks, audit trail, deterministic tests.
- **Five Whys (or equivalent):** to be completed at phase8 start
- **Root cause statement:** to be completed at phase8 start
- **Fix mechanism:** to be completed at phase8 start

## Reuse-first plan (mandatory)
- **Internal reuse:** existing knowledge/reference-pack services, onboarding contract validators, publish audit flow.
- **External reuse:** publication workflow patterns from official docs gathered in one web search section.
- **Why not reinvent the wheel:** extend current pack lifecycle contracts instead of adding parallel publish subsystem.

## Invariant
- Any inbound still resolves to `FACT/COLLECT/HANDOFF`.
- Hard-law/safety/tenant guards remain fail-closed.
- Published knowledge artifacts remain deterministic and auditable per scope.

## Scope
- Draft storage and validation rules for knowledge artifacts in Console.
- Publish/rollback pipeline for packs with explicit status transitions.
- Minimum data contract enforcement per domain before publish.

## Out of scope
- Rewriting LLM runtime core.
- New domain runtime logic outside existing pack contracts.
- Cross-block refactor outside knowledge lifecycle scope.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase8-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase8-a500.md`
- `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase8-a521.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `truffles-api/app/**` (knowledge/pack lifecycle scope only)
- `truffles-api/tests/**` (knowledge/pack scope only)
- `contracts/console_api/openapi.v1.yaml` (if API changes)

## Plan (1..N)
1. Start dedicated phase8 session/worktree and execute FACT pre-check.
2. Finalize analysis gate (contract delta, risks, migration, rollback).
3. Implement/complete Knowledge Studio lifecycle (`Draft -> Validate -> Publish -> Rollback`) in scope.
4. Add deterministic validation and audit/observability checks.
5. Add/update tests and openapi contract if API changed.
6. Sync docs/evidence and close block.

## DoD
- Publish is blocked when minimum data contract is invalid.
- Rollback to last published version works deterministically and is auditable.
- Console governance endpoints enforce platform-admin RBAC and tenant context.
- Tests and evidence prove pack lifecycle correctness.
- `docs/BLOCK_GRAPH.yaml`: `UCPV1-PHASE8 -> passed`, `UCPV1-PHASE9` unlocked.

## Checks
- `cd truffles-api && ruff check app tests`
- `pytest -q truffles-api/tests -k "knowledge or publish or rollback or reference_pack"`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase8-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase8-a500.md --graph docs/BLOCK_GRAPH.yaml`

## Evidence
- Console API/DB/runtime diffs for knowledge lifecycle.
- Deterministic tests + trace/meta/audit snippets for publish/rollback flow.
- Phase8 report with verdict and residual risks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** targeted knowledge/publish suites first.
- **Stop condition:** 2 runs without new evidence -> stop and refresh RCA.
- **Escalation path:** Brain/Top Architect for expanded run budget.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased activation by tenant/branch with publish gate default fail-closed.
- **Go/no-go signals:** publish validation failures, rollback success rate, audit integrity.
- **Rollback:** revert phase8 changes and pin previous published artifact.
- **Post-release monitoring window:** 24h with knowledge/publish dashboards and trace checks.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase8-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - no pass without code/tests/report/graph sync in same block.

## Rollback
- Revert phase8 commit(s).
- Restore previous published knowledge artifact/version.
- Re-run targeted knowledge lifecycle tests.

## No-go
- No broad refactor outside knowledge lifecycle scope.
- No semantic hardcode in core routing.
- No weakening of fail-closed publish gates.

## Risks/Blockers
- Pack schema drift across domains can break publish compatibility.
- Partial publish artifacts can create rollback complexity without strict version pinning.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` then this TP
- `Do not touch`: unrelated parallel tracks and unrelated UCP blocks
- `Open risks`: schema drift, publish rollback observability
- `First command to verify`: `rg -n "knowledge|publish|rollback|reference_pack" truffles-api/app`
