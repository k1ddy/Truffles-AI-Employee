# TP-2026-02-22-universal-control-plane-v1-phase4-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE4
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE3
- `UNLOCKS`: UCPV1-PHASE5

## Название/цель
Universal Control Plane v1 / Phase 4: завершить Onboarding State Machine v2 как управляемый server-side go-live pipeline для Platform Admin, включая deterministic preflight, approve/reject/waive workflow, explicit blockers и fail-closed go-live gate.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase3-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/onboarding_state.py`
  - `truffles-api/app/services/onboarding_blueprints.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_onboarding_state.py`
  - `truffles-api/tests/test_console_onboarding_contract_api.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
- `Baseline commands`:
  - `rg -n 'advance_onboarding|get_onboarding_scorecard|approve_branch_go_live|reject_branch_go_live|waive_branch_go_live|run_onboarding_autopilot' truffles-api/app/routers/console.py`
  - `rg -n 'build_onboarding_readiness_kernel|build_onboarding_scorecard|ensure_onboarding_step|advance_onboarding_step' truffles-api/app/services/onboarding_state.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_state.py`
- `FACT findings`:
  - Базовые элементы state machine уже есть: step transition, readiness kernel, scorecard, go-live approve/reject/waive endpoints.
  - Hard-go-live gate частично enforced через `_require_branch_scorecard_ready`, но нужен phase-level acceptance audit против B04 DoD и закрытие remaining contract gaps.
  - Требуется зафиксировать и закрыть разрыв между текущим поведением и целевым B04: server-side preflight + explicit blockers + reproducible go-live decision trace.
- `Detected drift (docs vs code)`: `partial` (в коде есть значительная часть B04, но нет формального closure evidence блока UCPV1-PHASE4 и централизованного acceptance report).

## One web search (mandatory before implementation)
- **Query (exact):** `aws step functions human approval workflow best practices state machine`
- **Date/time (local):** `2026-02-27 16:52, Asia/Almaty`
- **Why this query is precise:** целенаправленно ищет первоисточники по надежной реализации state-machine с human approval, guardrails и staged transitions для production onboarding pipeline.
- **Sources opened (from this query):**
  - AWS Prescriptive Guidance, Workflow engine on AWS: https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-integrating-microservices/workflow-engine.html
  - AWS Step Functions tutorial, human approval step: https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-human-approval.html
  - AWS Step Functions use cases and orchestration patterns: https://docs.aws.amazon.com/step-functions/latest/dg/use-cases.html
- **Existing solutions found:** server-side state orchestration, explicit approval/rejection paths, event/audit-first transitions, deterministic rollback/degrade patterns.
- **Decision:** `reuse + integrate` — доусилить текущую реализацию onboarding/go-live в существующем `console` + `onboarding_state`, без нового orchestration engine в рамках этого блока.
- **Rejected options:**
  - Внедрять новый внешний workflow engine в этом блоке: отклонено как выход за scope и риск архитектурного скачка без DEC.
  - Перенести go-live логику в UI: отклонено (нарушает server-side source of truth).
- **Open questions:** нет, scope блока фиксирован через B04.

## Root cause (mandatory)
- **Symptom:** Onboarding state machine v2 не закрыт как формально принятый program-block, несмотря на наличие части механики в коде.
- **Minimal reproduction:**
  - Проверить цепочку endpoints и сервисов onboarding/go-live.
  - Сверить runtime behavior с B04 DoD по explicit blockers, preflight и approve/reject/waive semantics.
- **Evidence to capture:** targeted pytest outputs, API contract evidence, branch go-live gate behavior, decision/audit traces по go-live actions.
- **Five Whys (or equivalent):**
  1. Why? Block B04 still marked planned.
  2. Why? Нет полного acceptance closure с привязкой к block-level DoD.
  3. Why? Реализация развивалась волнами, но без финального program-level consolidation для UCPV1-PHASE4.
  4. Why? Не зафиксирован единый contract delta и evidence bundle для phase gate.
  5. Why? Без этого следующий блок (policy governance) стартует на неполной certainty по onboarding/go-live contracts.
- **Root cause statement:** отсутствует целевой block-level closure контракта Onboarding State Machine v2 (analysis->implementation->evidence), а не полностью отсутствующий код.
- **Fix mechanism:** выполнить phase4 consolidation: закрыть contract gaps в коде и тестах, собрать deterministic evidence bundle, синхронизировать docs/block graph/state с verdict `passed`.

## Reuse-first plan (mandatory)
- **Internal reuse:** `onboarding_state` primitives, go-live endpoints в `console.py`, текущие scorecard/readiness schemas/tests.
- **External reuse:** best-practice patterns из AWS Step Functions docs (approval orchestration, explicit state transitions).
- **Why not reinvent the wheel:** ядро state-machine уже реализовано в текущем runtime; требуется contract hardening и acceptance closure, а не новая подсистема.

## Invariant
- Tenant isolation и RBAC fail-closed остаются неизменными.
- Go-live gate не может быть ослаблен (approval/waiver только с явной причиной и auditable actor).
- Branch activation path не обходит scorecard/readiness blockers.
- Никакого semantic hardcode в core runtime.

## Scope
- Провести analysis gate B04 и подтвердить фактические gaps против DoD.
- Доработать server-side onboarding transition/go-live gate только в пределах B04.
- Усилить/добавить deterministic tests по approve/reject/waive + blockers + preflight outcomes.
- Собрать и зафиксировать evidence bundle + doc sync для block closure.

## Out of scope
- Новый workflow orchestration engine.
- Изменения LLM decision core.
- Changes outside onboarding/go-live governance path.
- CI pipeline redesign.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase4-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `STATE.md`

## Plan (1..N)
1. Выполнить FACT audit текущего onboarding/go-live поведения против B04 DoD (analysis gate).
2. Внести минимальные кодовые правки для закрытия выявленных contract gaps.
3. Усилить deterministic тесты по transition/go-live blockers и approval/waiver semantics.
4. Прогнать проверки, собрать evidence и оформить phase4 report.
5. Обновить `STATE.md` и перевести `UCPV1-PHASE4` в `passed` (или `blocked` с причиной).

## DoD
- Branch не может выйти в live при незакрытых обязательных blockers.
- Approve/reject/waive workflow полностью server-side и auditable.
- Readiness/preflight статусы выдаются детерминированно и повторяемо.
- Targeted onboarding/go-live тесты зелёные и покрывают negative paths.
- Block documentation sync закрыт без дрейфа (TP/Report/STATE/BLOCK_GRAPH).

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py`
- `pytest -q truffles-api/tests/test_console_onboarding_state.py`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k 'go_live or onboarding_scorecard or onboarding_autopilot'`
- `python3 truffles-api/scripts/generate_openapi.py --check`

## Evidence
- targeted test logs for onboarding/go-live paths
- contract evidence (openapi/check + endpoint behavior)
- audit event evidence for approve/reject/waive transitions
- updated phase4 report + state entry + block graph status

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** начинать с узких onboarding/go-live тестов, затем запускать расширенный subset только при изменениях в контракте.
- **Stop condition:** 2 итерации без нового сигнала -> остановка и обновление RCA.
- **Escalation path:** Brain/Top Architect approval для дополнительных прогонов.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout (internal platform-admin tenant first).
- **Go/no-go signals:** go-live gate negative tests, deterministic blockers serialization, audit events completeness.
- **Rollback:** revert block commit; вернуть предыдущий onboarding/go-live contract.
- **Post-release monitoring window:** 24h on go-live decision endpoints + audit events.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `SPECS/CONTROL_PLANE.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase4-a500.md`
  - `STATE.md`
  - `docs/BLOCK_GRAPH.yaml`
- `Drift closeout rule`:
  - block не закрывается без синхронного обновления docs и evidence.

## Rollback
- Revert phase4 commits.
- Re-run targeted onboarding tests to confirm rollback consistency.

## No-go
- Не переносить оркестрацию в client-side.
- Не ослаблять go-live hard gates.
- Не трогать unrelated marketing/runtime tracks.
- Не работать в `main` как в рабочей ветке реализации.

## Risks/Blockers
- Возможны скрытые regressions в смежных onboarding endpoints из-за высокой связанности `console.py`.
- Нужна аккуратная совместимость для branch с legacy onboarding_state.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `truffles-api/app/routers/console.py` go-live + onboarding endpoints
- `Do not touch`: webhook runtime core, unrelated marketing/provider tracks
- `Open risks`: onboarding legacy-state compatibility
- `First command to verify`: `pytest -q truffles-api/tests/test_console_onboarding_state.py`

## Branch / Worktree / Base
- Branch: `feat/2026-02-27-ucpv1-phase4-a500`
- Worktree: `/home/zhan/worktrees/2026-02-27-ucpv1-phase4-a500`
- Base: `origin/main`
