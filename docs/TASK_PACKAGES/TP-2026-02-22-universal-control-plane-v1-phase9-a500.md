# TP-2026-02-22-universal-control-plane-v1-phase9-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE9
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE8
- `UNLOCKS`: UCPV1-PHASE10

## Название/цель
Universal Control Plane v1 / Phase 9: Runtime Pack-Agnostic Decoupling, чтобы core runtime не зависел напрямую от demo-pack и подключал доменные различия только через neutral adapters/capabilities/contracts.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `SPECS/VERTICAL_PACK_KIT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase8-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/pack_runtime_*`
  - `truffles-api/app/services/demo_salon_knowledge.py` (as canary boundary only)
  - `truffles-api/app/routers/webhook/**`
  - `truffles-api/tests/test_demo_salon_eval.py`
  - `truffles-api/tests/test_message_endpoint.py`
- `Baseline commands`:
  - `rg -n "demo_salon|pack_runtime|neutral_adapter|fallback_adapter" truffles-api/app`
  - `rg -n "demo_salon|pack_runtime|neutral" truffles-api/tests`
  - `rg -n "demo-neutral|pack-agnostic|runtime" AGENTS.md SPECS/CONTROL_PLANE.md`
- `FACT findings`:
  - Phase9 execution required after Phase8 pass.
  - Must verify remaining demo-coupling points and runtime adapter boundaries before changes.
- `Detected drift (docs vs code)`: to be validated at phase9 start

## One web search (mandatory before implementation)
- **Query (exact):** `runtime plugin architecture decouple domain pack from core service best practices`
- **Date/time (local):** to be executed at phase9 start
- **Why this query is precise:** фокус на plugin/adapter boundaries и исключении direct domain coupling в core runtime.
- **Sources opened (from this query):**
  - to be filled at phase9 start
- **Existing solutions found:** to be filled at phase9 start
- **Decision:** to be filled at phase9 start
- **Rejected options:** to be filled at phase9 start
- **Open questions:** to be filled at phase9 start

## Root cause (mandatory)
- **Symptom:** B09 still planned and phase9 closure по runtime decoupling ещё не выполнено как отдельный блок.
- **Minimal reproduction:** to be defined at phase9 start based on FACT pre-check.
- **Evidence to capture:** import maps, adapter contract tests, runtime trace/meta evidence.
- **Five Whys (or equivalent):** to be completed at phase9 start
- **Root cause statement:** to be completed at phase9 start
- **Fix mechanism:** to be completed at phase9 start

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `pack_runtime_*` adapters/contracts and capability merge stack.
- **External reuse:** plugin/adapter architecture guidance from one web search source.
- **Why not reinvent the wheel:** evolve current adapter boundaries instead of rewriting runtime orchestration.

## Invariant
- Any inbound still resolves to `FACT/COLLECT/HANDOFF`.
- Hard-law/safety/tenant guards remain fail-closed.
- Core runtime stays domain-neutral; domain behavior remains data/pack-driven.

## Scope
- Remove/contain direct demo-pack coupling from core runtime paths.
- Enforce neutral runtime adapter contract and fallback behavior.
- Add deterministic checks for adapter boundary integrity.

## Out of scope
- Rewriting LLM core from scratch.
- New business domain feature additions outside decoupling scope.
- Broad refactor outside runtime pack-adapter boundaries.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `docs/SESSIONS/SESSION-2026-02-28-ucpv1-phase9-a522.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `truffles-api/app/**` (runtime adapter scope only)
- `truffles-api/tests/**` (runtime adapter scope only)
- `contracts/console_api/openapi.v1.yaml` (if API changes)

## Plan (1..N)
1. Start dedicated phase9 session/worktree and execute FACT pre-check.
2. Finalize analysis gate (contract delta, risks, migration, rollback).
3. Implement/complete runtime pack-agnostic decoupling in scope.
4. Add deterministic adapter boundary checks and trace/meta assertions.
5. Add/update tests and openapi contract if API changed.
6. Sync docs/evidence and close block.

## DoD
- Core runtime does not rely on direct demo-pack imports in decision path.
- Adapter boundaries are explicit and verified by deterministic tests.
- Neutral fallback behavior remains deterministic and observable.
- Tests and evidence prove no regression in outcome contract.
- `docs/BLOCK_GRAPH.yaml`: `UCPV1-PHASE9 -> passed`, `UCPV1-PHASE10` unlocked.

## Checks
- `cd truffles-api && ruff check app tests`
- `pytest -q truffles-api/tests -k "pack_runtime or demo_salon_eval or message_endpoint or adapter"`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md --graph docs/BLOCK_GRAPH.yaml`

## Evidence
- Runtime import/adapter boundary diffs.
- Deterministic tests + trace/meta snippets for neutral runtime path.
- Phase9 report with verdict and residual risks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** targeted runtime adapter suites first.
- **Stop condition:** 2 runs without new evidence -> stop and refresh RCA.
- **Escalation path:** Brain/Top Architect for expanded run budget.

## Release safety (mandatory for non-doc changes)
- **Strategy:** gated rollout by adapter flag/tenant scope.
- **Go/no-go signals:** adapter error rate, fallback frequency, trace integrity.
- **Rollback:** revert phase9 changes and restore previous runtime adapter routing.
- **Post-release monitoring window:** 24h with runtime trace and error-budget checks.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - no pass without code/tests/report/graph sync in same block.

## Rollback
- Revert phase9 commit(s).
- Restore previous adapter routing/fallback behavior.
- Re-run targeted runtime adapter tests.

## No-go
- No broad refactor outside runtime adapter scope.
- No semantic hardcode in core routing.
- No weakening of fail-closed gates.

## Risks/Blockers
- Hidden import coupling can persist in legacy helper paths.
- Adapter fallback drift can mask coupling regressions without strict trace checks.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` then this TP
- `Do not touch`: unrelated parallel tracks and unrelated UCP blocks
- `Open risks`: hidden coupling and fallback drift
- `First command to verify`: `rg -n "demo_salon|pack_runtime|neutral_adapter|fallback_adapter" truffles-api/app`
