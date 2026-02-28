# TP-2026-02-22-universal-control-plane-v1-phase9-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE9
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE8
- `UNLOCKS`: UCPV1-PHASE10

## Название/цель
Universal Control Plane v1 / Phase 9: Runtime Pack-Agnostic Decoupling, чтобы убрать demo-coupling из core runtime path и держать pack-поведение только в adapter/capability слоях.

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
  - `truffles-api/app/services/pack_runtime_default.py`
  - `truffles-api/app/services/pack_runtime_demo_adapter.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/tests/test_pack_runtime_service.py`
  - `truffles-api/tests/test_policy_handler_runtime.py`
- `Baseline commands`:
  - `rg -n "demo_salon|pack_runtime|neutral_adapter|fallback_adapter" truffles-api/app`
  - `rg -n "demo_salon|pack_runtime|neutral" truffles-api/tests`
  - `rg -n "demo-neutral|pack-agnostic|runtime" AGENTS.md SPECS/CONTROL_PLANE.md`
- `FACT findings`:
  - Core already routed through `pack_runtime_service`, но `pack_runtime_default` содержал slug map с explicit demo adapter path.
  - `webhook/decision.py` содержал explicit demo alias key в `_POLICY_HANDLERS`.
  - `webhook/policy.py` содержал legacy demo alias helper functions.
- `Detected drift (docs vs code)`:
  - Phase9 был `planned`, фактический runtime decoupling для B09 не закрыт.

## One web search (mandatory before implementation)
- **Query (exact):** `Python importlib import_module documentation dynamic module loading`
- **Date/time (local):** `2026-02-28 06:35 (+05)`
- **Why this query is precise:** проверяет официальный механизм dynamic module resolution для plugin-like adapter discovery.
- **Sources opened (from this query):**
  - Python docs `importlib`: https://docs.python.org/3/library/importlib.html
- **Existing solutions found:**
  - runtime-safe dynamic module loading через `importlib.import_module` с fail-closed handling `ModuleNotFoundError`.
- **Decision:**
  - Убрать hardcoded slug map и перейти на slug-based adapter discovery `pack_runtime_{slug}_adapter` с fallback в neutral adapter.
- **Rejected options:**
  - Оставить explicit slug registry в core как default path, причина: это фиксирует demo-specific coupling в core runtime.
- **Open questions:**
  - Нужен ли в следующем шаге отдельный contract-test на discovery для нескольких non-demo slug.

## Root cause (mandatory)
- **Symptom:** `UCPV1-PHASE9` не закрыт, demo-specific routing остаточно присутствовал в core runtime boundary.
- **Minimal reproduction:**
  - `rg -n "_PACK_ADAPTER_BY_SLUG|demo_salon" truffles-api/app/services/pack_runtime_default.py truffles-api/app/routers/webhook/decision.py`
- **Evidence to capture:**
  - diff runtime adapter resolution,
  - deterministic tests `pack_runtime/policy/message_endpoint/booking/demo_eval`,
  - short runtime smoke на отдельном порту.
- **Five Whys (or equivalent):**
  1. Почему phase9 не закрыт: в core runtime оставались explicit demo-specific точки маршрутизации.
  2. Почему они оставались: предыдущие dedemo шаги оставили backward-compat alias без финального cleanup в B09.
  3. Почему cleanup не был завершен: фокус прошлых блоков был на governance/registry, не на финальном runtime adapter discovery.
  4. Почему это важно: explicit demo key в core нарушает pack-agnostic invariant и повышает риск drift для новых ниш.
  5. Почему нужен отдельный блок: B09 DoD требует доказуемого удаления demo-coupling и adapter-boundary тестов.
- **Root cause statement:**
  - core runtime boundary имел остаточный demo-specific routing через hardcoded slug map и explicit demo alias.
- **Fix mechanism:**
  - slug-based adapter discovery в `pack_runtime_default` плюс dedicated slug adapter module для demo pack, удаление explicit demo alias из policy handler map.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - reuse existing `pack_runtime_generic_adapter`, `pack_runtime_demo_adapter`, and webhook policy flow.
- **External reuse:**
  - Python `importlib` official mechanism for dynamic module loading.
- **Why not reinvent the wheel:**
  - используем текущий adapter stack и меняем только resolution boundary вместо rewrite runtime.

## Invariant
- Каждый inbound завершает один outcome: `FACT/COLLECT/HANDOFF`.
- Hard-law/safety/tenant gates остаются fail-closed.
- Core runtime не содержит demo-specific default branching.

## Scope
- Перевести adapter resolution на dynamic slug discovery.
- Убрать explicit demo alias mapping в webhook policy boundary.
- Обновить deterministic tests на новое adapter имя и boundary.

## Out of scope
- Переписывание LLM core.
- Новый domain-pack функционал.
- Migration wave/production rollout beyond current branch scope.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `docs/SESSIONS/SESSION-2026-02-28-ucpv1-phase9-a521.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/tests/test_pack_runtime_service.py`

## Plan (1..N)
1. Выполнить FACT pre-check и зафиксировать coupling points.
2. Реализовать slug-based adapter discovery + demo slug adapter module.
3. Удалить explicit demo alias routing в webhook policy boundary.
4. Обновить/добавить deterministic тесты на runtime boundary.
5. Прогнать обязательные deterministic suites и short runtime smoke.
6. Синхронизировать docs/report/state и передать блок на финальный acceptance gate.

## DoD
- `pack_runtime_default` не содержит hardcoded demo slug map.
- Demo pack резолвится через slug-based adapter module, не через core map.
- `_POLICY_HANDLERS` не содержит explicit demo key.
- Deterministic core tests green.
- Canonical long `llm-quality` acceptance run выполнен и валиден.

## Checks
- `cd truffles-api && ruff check app/services/pack_runtime_default.py app/services/pack_runtime_demo_salon_adapter.py app/routers/webhook/decision.py app/routers/webhook/policy.py tests/test_pack_runtime_service.py tests/test_policy_handler_runtime.py`
- `cd truffles-api && pytest -q tests/test_pack_runtime_service.py tests/test_policy_handler_runtime.py`
- `cd truffles-api && pytest -q tests/test_pack_query_engine_contract.py tests/test_pack_query_engine_abstain.py`
- `cd truffles-api && pytest -q tests/test_message_endpoint.py`
- `cd truffles-api && pytest -q tests/test_booking_chaos_dialogs.py tests/test_booking_quality_response_guard.py tests/test_demo_salon_eval.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:8031 --mode llm --count 1 --min-turns 2 --max-turns 2 --scenario-coverage none --tool-hooks off --tool-evidence-policy off --judge-mode sample --judge-sample 1 --allow-non-allowlist --skip-outbox --manager-mode skip --pending-mode skip --manual-audit-gate off --run-economy-gate off --run-id phase9-short-a521-r9`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md --report docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md --graph docs/BLOCK_GRAPH.yaml`

## Evidence
- Runtime adapter boundary diff:
  - `truffles-api/app/services/pack_runtime_default.py`
  - `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/policy.py`
- Deterministic test outputs:
  - `265 passed` for `test_message_endpoint.py`
  - `70 passed` for booking/demo eval trio
  - `22 passed` for pack runtime + policy handler tests
- Short runtime smoke artifacts:
  - `/tmp/booking_quality/phase9-short-a521-r9/summary.json`
  - `/tmp/booking_quality/phase9-short-a521-r9/brief.md`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** start from deterministic suites, then short smoke, then canonical acceptance run.
- **Stop condition:** 2 runs without new evidence then root-cause refresh.
- **Escalation path:** Brain/Top Architect for acceptance-lane budget.

## Release safety (mandatory for non-doc changes)
- **Strategy:** merge behind normal rollout controls with monitor-first.
- **Go/no-go signals:** adapter import errors, policy handler regressions, outcome contract drift.
- **Rollback:** revert phase9 commit and restore prior adapter resolution.
- **Post-release monitoring window:** 24h trace/meta watch on runtime decision path.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - no block closure without sync of code/tests/report/graph/state.

## Rollback
- `git revert` phase9 commit(s).
- Re-run targeted runtime suites to confirm previous behavior.

## No-go
- No semantic hardcode in core runtime.
- No weakening of acceptance gates for final block pass.
- No unrelated refactors outside listed touch-list.

## Risks/Blockers
- Canonical acceptance lane for core behavior still requires full `llm-quality` profile.
- Short smoke run is non-canonical and cannot be used as final DoD closure.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `Do not touch`: unrelated UCP blocks and non-runtime tracks.
- `Open risks`: full acceptance lane pending.
- `First command to verify`: `cd truffles-api && pytest -q tests/test_pack_runtime_service.py tests/test_policy_handler_runtime.py`
