# TP-2026-02-22-universal-control-plane-v1-phase6-a500

## Block identity
- `BLOCK_ID`: UCPV1-PHASE6
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE5
- `UNLOCKS`: UCPV1-PHASE7

## Название/цель
Universal Control Plane v1 / Phase 6: реализовать Tool Registry Certification так, чтобы несертифицированные инструменты не могли активироваться в effective capabilities и runtime, с управлением через Console (Platform Admin only).

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/CONSULTANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase5-a500.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/app/services/capability_manifest_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/capabilities.py`
  - `truffles-api/tests/test_booking_appointments.py`
  - `truffles-api/tests/test_capability_manifest_service.py`
- `Baseline commands`:
  - `rg -n "tool_registry|resolve_tool_protocol_decision|tool_action_disabled|capability_blocked" truffles-api/app/services truffles-api/app/routers/webhook`
  - `rg -n "admin/capabilities|domain-catalog|policy-registry" truffles-api/app/routers/console.py`
  - `rg -n "certif|tool registry|tool_registry" truffles-api/app/models truffles-api/migrations`
- `FACT findings`:
  - Runtime gate уже блокирует tool-action по capability allow/deny (`resolve_tool_protocol_decision`), но не имеет registry-level certification статуса.
  - В БД/моделях нет сущности Tool Registry Certification.
  - Console не содержит `/admin/tool-registry*` CRUD для platform-admin.
  - `PATCH /admin/capabilities` не валидирует tool allow tokens против сертификационного каталога.
- `Detected drift (docs vs code)`: `yes` (B06 ожидает certification+health+scope rules, в коде есть только allow/deny token gate).

## One web search (mandatory before implementation)
- **Query (exact):** `software supply chain policy enforcement certified artifacts allowlist health checks best practices`
- **Date/time (local):** `2026-02-27 18:45, Asia/Almaty`
- **Why this query is precise:** фокус на fail-closed policy enforcement и health-validation, чтобы перенести практики в tool certification contract без broad refactor.
- **Sources opened (from this query):**
  - Google Cloud Binary Authorization overview: https://cloud.google.com/binary-authorization/docs/overview
  - Google Cloud Binary Authorization key concepts: https://cloud.google.com/binary-authorization/docs/key-concepts
- **Existing solutions found:** allowlist/attestation-based admission, explicit policy evaluation before execution, default-deny for untrusted artifacts.
- **Decision:** `reuse + integrate` — расширяем текущий tool-protocol gate и capabilities path через DB-backed certification registry, не меняя архитектуру runtime ядра.
- **Rejected options:**
  - Новый внешний policy engine: отклонено (DEC-level change, вне scope Phase6).
  - Временный regex hardcode на tool_action в decision core: отклонено (нарушение semantic-first и no-shortcut gate).
- **Open questions:** нет.

## Root cause (mandatory)
- **Symptom:** B06 не закрыт: несертифицированный tool теоретически может быть активирован token-политикой или default path.
- **Minimal reproduction:**
  - Проверить отсутствие таблицы/модели tool certification.
  - Проверить, что `PATCH /admin/capabilities` не учитывает certification status.
  - Проверить runtime `execute_tool_action` — нет DB-based certification decision.
- **Evidence to capture:** migration/model/service diff, API contract, deterministic tests (`service + console + runtime`).
- **Five Whys (or equivalent):**
  1. Why? Phase5 закрыл policy governance, но не tool certification governance.
  2. Why? Tool gate опирается только на capability allow/deny и env flags.
  3. Why? Нет canonical registry c `certification_status/health_status/scope`.
  4. Why? Console provisioning path не имеет endpoint и валидации под registry.
  5. Why? Отсутствует единый fail-closed enforcement before tool execution.
- **Root cause statement:** отсутствует DB-backed сертификационный реестр инструментов и связанный fail-closed enforcement в capabilities/runtime слоях.
- **Fix mechanism:** добавить tool registry model+migration+service и внедрить два enforcement слоя: (1) console capabilities validation, (2) runtime execution gate.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `TOOL_ACTIONS`/`execute_tool_action` flow,
  - existing `resolve_tool_protocol_decision` capability gate,
  - existing Console RBAC/audit patterns,
  - existing capabilities schema/merge path.
- **External reuse:** policy enforcement principles (Binary Authorization docs) как reference для fail-closed admission.
- **Why not reinvent the wheel:** расширяем текущий workflow и contracts; не вводим новый runtime engine или новую orchestration subsystem.

## Invariant
- Любой inbound остаётся в outcome-контракте `FACT/COLLECT/HANDOFF`.
- Hard-law и tenant guards не ослабляются.
- Tool enforcement остаётся fail-closed для `uncertified/down/scope-blocked`.
- Управление certification только через platform-admin.

## Scope
- Добавить Tool Registry Certification persistence (`tool_registry_entries`).
- Добавить Console API (platform-admin): list/upsert tool registry records.
- Добавить validation в `PATCH /admin/capabilities` для allow tokens против registry (certification + scope).
- Добавить runtime gate в `execute_tool_action` (certification + health + scope).
- Покрыть deterministic tests для service/console/runtime.

## Out of scope
- Изменение LLM policy core маршрутизации.
- Массовый рефактор `decision.py`.
- Новые каналы/providers beyond tool certification contract.

## Touch-list
- `truffles-api/app/models/tool_registry_entry.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/migrations/045_add_tool_registry_entries.sql`
- `truffles-api/app/services/tool_certification_service.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_tool_certification_service.py`
- `truffles-api/tests/test_console_tool_registry.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `contracts/console_api/openapi.v1.yaml`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase6-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase6-a500.md`
- `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase6-a500.md`
- `docs/SESSION_INDEX.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `STATE.md`

## Plan (1..N)
1. Создать phase6 TP/Report + связать session metadata с `UCPV1-PHASE6`.
2. Реализовать DB model+migration для tool registry certification.
3. Реализовать service layer для registry decisions (certification/health/scope).
4. Добавить Console API list/upsert (platform-admin only + audit).
5. Подключить capabilities patch validation и runtime gate к registry decisions.
6. Добавить/обновить deterministic tests.
7. Прогнать checks, синхронизировать docs/graph/state, закрыть блок в `passed`.

## DoD
- Есть DB-backed tool registry с certification/health/scope status и seed для known tool actions.
- Platform Admin может читать/обновлять tool registry через Console API.
- `PATCH /admin/capabilities` отвергает allow tokens, которые ведут к `uncertified/down/scope-blocked` tools.
- Runtime блокирует tool execution для `uncertified/down/scope-blocked` с trace/meta reason.
- Deterministic tests зелёные по новым и затронутым контрактам.
- `docs/BLOCK_GRAPH.yaml`: `UCPV1-PHASE6 -> passed`, `UCPV1-PHASE7` unlocked.

## Checks
- `python3 -m py_compile truffles-api/app/models/tool_registry_entry.py truffles-api/app/services/tool_certification_service.py truffles-api/app/services/tool_registry_service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `pytest -q truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_console_tool_registry.py truffles-api/tests/test_booking_appointments.py -k "tool_registry" truffles-api/tests/test_console_admin_provisioning.py -k "capabilities"`
- `pytest -q truffles-api/tests/test_apply_sql_migrations.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`

## Evidence
- Migration/model/service/API diffs for tool certification.
- Green deterministic tests from `Checks`.
- Phase6 report with explicit verdict and residual risks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `3`
- **Fail-fast / scenario lock:** только targeted deterministic suites по touch-list.
- **Stop condition:** 2 подряд без новых сигналов -> stop and RCA update.
- **Escalation path:** Brain/Top Architect approval для расширения до broader suites.

## Release safety (mandatory for non-doc changes)
- **Strategy:** phased rollout через platform-admin registry updates (tenant scoped behavior).
- **Go/no-go signals:** все checks green + runtime reason-codes корректны + openapi drift green.
- **Rollback:** revert commit + registry upsert back to `certified/healthy` состояния.
- **Post-release monitoring window:** 24h наблюдение trace/meta (`tool_registry_decision`, `capability_reason`, `tool_decision`).

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase6-a500.md`
  - `docs/SESSIONS/SESSION-2026-02-27-ucpv1-phase6-a500.md`
  - `docs/SESSION_INDEX.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
- `Drift closeout rule`:
  - block считается `passed` только после code+tests+report+graph/state sync.

## Rollback
- Откатить commit(ы) блока.
- Перевести affected tool entries обратно в `certified/healthy`.
- Повторно прогнать targeted checks.

## No-go
- Не вводить обходные hardcode в runtime core.
- Не ослаблять tenant/RBAC/hard-law boundaries.
- Не смешивать этот блок с параллельными unrelated треками.
- Не закрывать блок без report/evidence.

## Risks/Blockers
- Возможен drift между статическими `TOOL_ACTIONS` и registry seed при будущих tool additions.
- Высокая связность `tool_registry_service.py` может усложнить granular тестирование.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml` (`UCPV1-PHASE7` после pass)
- `Do not touch`: unrelated onboarding/policy/marketing tracks
- `Open risks`: sync risk between tool catalog constants and registry rows
- `First command to verify`: `pytest -q truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_console_tool_registry.py`
