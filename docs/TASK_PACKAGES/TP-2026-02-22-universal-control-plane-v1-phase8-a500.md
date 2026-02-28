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
  - Console endpoints for lifecycle already implemented: `/knowledge/current`, `/knowledge/validate`, `/knowledge/publish`, `/knowledge/history`, `/knowledge/rollback`.
  - Service contract already implemented in `knowledge_registry_service` (`get_current_published`, `upsert_draft`, `validate_draft`, `publish_version`, `list_history`) and used by Console router.
  - Deterministic test coverage for knowledge/reference-pack path is present and green in phase8 session.
- `Detected drift (docs vs code)`: B08 remained `planned` in docs/graph while core lifecycle contract and tests were already implemented in codebase.

## One web search (mandatory before implementation)
- **Query (exact):** `knowledge publishing workflow draft validate publish rollback contract gate best practices`
- **Date/time (local):** `2026-02-28 05:44 (+05)`
- **Why this query is precise:** фокус на жизненном цикле публикации знаний и fail-closed контрактных блокировках.
- **Sources opened (from this query):**
  - Kentico Xperience docs, content publishing workflow best practices: https://docs.kentico.com/documentation/developers-and-admins/development/content-retrieval/content-retrieval-specification/best-practices-for-published-content-retrieval
- **Existing solutions found:** strict separation between draft and published states, retrieval only from published artifacts, explicit rollback/versioning patterns.
- **Decision:** reuse existing internal DB-first lifecycle and preflight gates; close B08 via evidence + doc sync instead of introducing a new publishing subsystem.
- **Rejected options:** re-building a parallel publish pipeline outside current `knowledge_registry_service` (out of scope and duplicates existing behavior).
- **Open questions:** none for B08 closure.

## Root cause (mandatory)
- **Symptom:** B08 still planned and not закрыт как отдельный evidence-backed блок.
- **Minimal reproduction:** inspect phase8 status in `docs/BLOCK_GRAPH.yaml` + master report, then verify implemented lifecycle endpoints/services/tests in current code.
- **Evidence to capture:** compile/publish/rollback checks, audit trail, deterministic tests.
- **Five Whys (or equivalent):**
  1. Why B08 looked unfinished? Status stayed `planned` in block graph and report.
  2. Why status lagged code? Lifecycle was implemented incrementally, but no dedicated phase8 closure pass executed.
  3. Why closure pass was missed? No explicit phase8 evidence session synchronized TP/Report/Graph/STATE together.
  4. Why it matters? Zero-context agents trust docs first; stale status causes repeated analysis and planning drift.
  5. Why drift persisted? Program-level closure discipline was not applied as a dedicated B08 block.
- **Root cause statement:** documentation-state drift, not missing phase8 runtime contract.
- **Fix mechanism:** execute dedicated phase8 FACT verification, run deterministic checks, and synchronize canonical docs/statuses to `passed`.

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
- `docs/SESSIONS/SESSION-2026-02-28-ucpv1-phase8-a521.md`
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
