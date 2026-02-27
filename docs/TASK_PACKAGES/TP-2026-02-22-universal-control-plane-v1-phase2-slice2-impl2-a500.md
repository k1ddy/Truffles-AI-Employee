# TP-2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE2-SLICE2-IMPL2
- `PARENT_BLOCK_ID`: UCPV1-PHASE2
- `DEPENDS_ON`: UCPV1-GATES-SANITARY
- `UNLOCKS`: UCPV1-PHASE3

## Название/цель
Universal Control Plane v1 / Phase 2 slice 2 (implementation wave 2): завершить нормализацию governance-role boundary для onboarding governance endpoint-ов (`onboarding-contract`, `webhook-secret`, `onboarding/autopilot`) в модели Platform Admin First без деградации tenant-изоляции и audit semantics.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-analysis-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl1-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_onboarding_contract_api.py`
  - `truffles-api/tests/test_console_access_admin_pr2.py`
  - `SPECS/CONTROL_PLANE.md`
- `Baseline commands`:
  - `rg -n '"/admin/(onboarding-contract|webhook-secret|onboarding/autopilot)"|require_console_permission\\(|_require_platform_admin\\(' truffles-api/app/routers/console.py`
  - `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "run_onboarding_autopilot or webhook_secret"`
- `FACT findings`:
  - `GET /admin/onboarding-contract` использует только `require_console_permission(... provisioning read ...)`, без явного `_require_platform_admin` (`truffles-api/app/routers/console.py:20709`).
  - `PATCH /admin/onboarding-contract` использует `provisioning write`, при этом `platform_admin` требуется только для `payment_status`, а не для всего governance endpoint (`truffles-api/app/routers/console.py:20820`).
  - `GET /admin/webhook-secret` использует `provisioning read`, без platform-only gate (`truffles-api/app/routers/console.py:20920`).
  - `POST /admin/onboarding/autopilot` использует `provisioning write`, без platform-only gate (`truffles-api/app/routers/console.py:20978`).
  - Baseline test status: `9 passed` для `test_console_onboarding_contract_api.py`, `6 passed, 38 deselected` для `test_console_access_admin_pr2.py -k "run_onboarding_autopilot or webhook_secret"`.
- `Detected drift (docs vs code)`: docs фиксируют Platform Admin First governance intent, но часть onboarding governance endpoint-ов еще контролируется через более широкий provisioning scope.

## One web search (mandatory before implementation)
- **Query (exact):** `OWASP ASVS access control deny by default least privilege`
- **Date/time (local):** `2026-02-27 14:54 (+05), Asia/Almaty`
- **Why this query is precise:** подтверждает внешним стандартом выбранный контракт для admin-governance endpoint-ов: centralized access control, least privilege, deny-by-default, fail-secure.
- **Sources opened (from this query):**
  - OWASP ASVS 4.1 General Access Control Design: https://owasp-aasvs4.readthedocs.io/en/latest/V4.1.html
  - OWASP Top 10 2025 A01 Broken Access Control: https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/
  - OWASP Top 10 Proactive Controls C1 Access Control: https://top10proactive.owasp.org/the-top-10/c1-accesscontrol/
- **Existing solutions found:** reuse centralized server-side permission gates, deny-by-default for sensitive endpoints, single trusted enforcement point.
- **Decision:** `reuse + integrate` existing `_require_platform_admin` in console-router for target endpoints; не вводить новый auth-layer и не дублировать semantics regex/keyword hardcode.
- **Rejected options:**
  - Оставить текущий `provisioning` guard и добавить только локальные исключения: отклонено из-за дрейфа governance semantics и риска неявной role-эскалации.
  - Ввести новый custom guard только для onboarding: отклонено, так как уже есть reusable `_require_platform_admin`.
- **Open questions:** `none` (для этого блока policy-решение зафиксировано как Platform Admin First governance).

## Root cause (mandatory)
- **Symptom:** onboarding governance endpoint-ы остаются доступны шире, чем целевой platform-admin boundary.
- **Minimal reproduction:**
  - Проинспектировать handlers `onboarding-contract`, `webhook-secret`, `onboarding/autopilot` в `console.py`.
  - Проверить, что в них нет явного `_require_platform_admin` на уровне endpoint.
- **Evidence to capture:** diff handler guards, deny tests for non-platform roles, pass tests для platform-admin сценариев.
- **Five Whys (or equivalent):**
  1. Почему boundary дрейфует? Потому что endpoints исторически использовали общий `provisioning` permission.
  2. Почему это не выровнено раньше? Потому что slice 2 impl1 закрывал только `onboarding-blueprints` и `reference-packs`.
  3. Почему общий permission недостаточен? Потому что governance endpoints управляют чувствительными onboarding policy/секретами.
  4. Почему это риск? Потому что role surface шире platform-admin intent и повышает вероятность unintended changes.
  5. Почему нужен фикс именно здесь? Потому что это последняя planned волна Phase 2 slice 2 перед переходом к Phase 3.
- **Root cause statement:** governance-contract дрейф возник из-за неполного перехода от generic `provisioning` guard к explicit platform-admin gate на чувствительных onboarding endpoint-ах.
- **Fix mechanism:** добавить explicit `_require_platform_admin(context)` в целевые handlers + обновить deterministic deny tests и canon doc.

## Reuse-first plan (mandatory)
- **Internal reuse:** `_require_platform_admin`, `require_console_permission`, существующие test patterns `*_requires_platform_admin`, existing console RBAC helpers.
- **External reuse:** не требуется; задача решается внутри текущего policy-core/console boundary.
- **Why not reinvent the wheel:** нужный enforcement primitive уже есть в runtime (`_require_platform_admin`), поэтому новая прослойка только увеличит технический долг.

## Invariant
- Tenant isolation fail-closed сохраняется.
- Никаких cross-tenant side effects при onboarding actions.
- Audit events и trace semantics по onboarding остаются валидными.
- Никакого semantic hardcode; только deterministic boundary enforcement.

## Scope
- Harden endpoint access contract для:
  - `GET /admin/onboarding-contract`
  - `PATCH /admin/onboarding-contract`
  - `GET /admin/webhook-secret`
  - `POST /admin/onboarding/autopilot`
- Добавить/обновить deterministic tests на non-platform deny + platform-admin allow.
- Синхронизировать canonical doc для onboarding governance boundaries.
- Сформировать phase report с FACT/GAP/evidence.

## Out of scope
- Изменение branch change workflow (`/admin/branch-changes*`) и go-live approve/reject/waive.
- Перепроектирование identity/membership model.
- Любые runtime decision-core / LLM behavior changes.
- CI workflow changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`

## Plan (1..N)
1. Добавить explicit `_require_platform_admin(context)` в 4 target handlers.
2. Обновить/добавить deterministic tests для deny non-platform ролей и allow platform-admin.
3. Прогнать targeted checks и зафиксировать результаты.
4. Обновить canon (`SPECS/CONTROL_PLANE.md`) по onboarding governance boundaries.
5. Обновить block report + `STATE.md` FACT/GAP (через Brain/Top Architect) и перевести block status в `passed` только после evidence.

## DoD
- Все 4 target endpoints fail-closed для non-platform ролей (`owner/admin/manager/support`).
- Platform-admin happy-path на target endpoints остается green.
- Нет regressions в existing onboarding/console tests, затронутых scope.
- Canon синхронизирован с фактическим enforcement.
- Report содержит команды, результаты, evidence и residual risks.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_contract_api.py truffles-api/tests/test_console_access_admin_pr2.py`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "run_onboarding_autopilot or webhook_secret or onboarding_contract"`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "platform_admin or onboarding"`

## Evidence
- Router diff с platform-admin gates.
- Test outputs с pass/deny cases.
- Canon delta (`SPECS/CONTROL_PLANE.md`).
- Block report: `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** сначала targeted pytest по touch-list, full regression только при fail/дрифте.
- **Stop condition:** после 2 итераций без нового сигнала остановка и обновление RCA в TP/report.
- **Escalation path:** Brain/Top Architect подтверждает расширение прогонов сверх лимита.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout (platform-admin canary tenant first), затем broader rollout.
- **Go/no-go signals:** 403/200 contract checks на target endpoints, отсутствие новых auth regressions в provisioning tests, стабильный audit trail.
- **Rollback:** revert block commit, восстановление предыдущего guard behavior.
- **Post-release monitoring window:** 24h наблюдение admin audit событий по onboarding governance endpoints.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `SPECS/CONTROL_PLANE.md`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl2-a500.md`
- `Drift closeout rule`:
  - если код и canon расходятся по governance boundary, блок не закрывается и помечается `Blocked` до синхронизации.

## Rollback
- Revert commit блока.
- Перезапустить targeted tests и зафиксировать rollback evidence в report.

## No-go
- Не расширять scope в branch-change/membership domains.
- Не смягчать acceptance thresholds ради скорости.
- Не вводить новый custom guard при наличии reusable platform-admin guard.
- Не выполнять правки в `main` как рабочем дереве (только отдельная worktree блока).

## Risks/Blockers
- Возможна операционная зависимость отдельных owner/admin flow от текущего onboarding governance доступа; требуется явный fail-closed rollout и коммуникация.
- При неучтенных тестовых сценариях возможны regressions в autopilot happy-path; минимизируется targeted + regression checks.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `truffles-api/app/routers/console.py` around `onboarding-contract`/`webhook-secret`/`onboarding/autopilot` handlers
- `Do not touch`: unrelated `/admin/branch-changes*`, live-check protocols, CI workflows
- `Open risks`: owner/admin operational dependency on onboarding governance endpoints
- `First command to verify`: `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`

## Branch / Worktree / Base
- Branch: `feat/2026-02-27-ucpv1-phase2-slice2-impl2-a500`
- Worktree: `/home/zhan/worktrees/2026-02-27-ucpv1-phase2-slice2-impl2-a500`
- Base: `origin/main`
