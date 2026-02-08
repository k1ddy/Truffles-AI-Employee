# TP-2026-02-08 — Integration Guardrails (Single PR)

- Название/цель: закрыть silent-failure контур Chatflow webhook интеграции одним архитектурным PR: detect -> degrade -> alert -> recover без хардкодов и без ручных prod-операций.
- Canon refs:
  - `AGENTS.md` (Fitness Functions P0/P1, stop-the-line, one-issue flow)
  - `STATE.md` NOW/GAP: `TODO: Автоматизация онбординга ... mapping instanceId/phone, генерация webhook, go/no-go gate`;
    evidence по drift/instance mismatch и webhook_secret mismatch в разделах интеграции/ops
  - `SPECS/SYSTEM_REFERENCE.md` (instanceId/webhook_secret contract, simulation semantics, live-check evidence)
  - `SPECS/ARCHITECTURE.md` (canonical instanceId per branch, routing and outbox invariants)

## Invariant
- `instanceId` routing остаётся детерминированным и branch-aware; оркестрация не уходит в `_legacy.py`/entrypoints.
- Каждое inbound-сообщение сохраняет trace/meta контракт; нет silent drop без сигналов для ops.
- Production conversations не могут быть переведены в simulation outbound skip внешним флагом.

## Scope
- DB guardrails для интеграции branch-to-instance.
- Runtime integration guardrail service (drift detection, degraded transitions, alert/audit signals).
- Webhook preflight hardening для incident сигналов.
- Simulation/live isolation в webhook pipeline.
- Sentinel watchdog + auto-remediate по branch integration status.
- Тесты (unit/integration) для новых guardrails.

## Out of scope
- Полная внешняя оркестрация Chatflow конфигов через новый control-plane сервис.
- UI redesign/новые страницы beyond текущих API полей.
- Изменение продуктового контракта FACT/COLLECT/HANDOFF.

## Touch-list
- `truffles-api/migrations/*` (новая миграция integration guardrails + unique index)
- `truffles-api/app/models/branch.py`
- `truffles-api/app/schemas/console.py` (минимально нужные поля статуса)
- `truffles-api/app/routers/console.py` (read path/status reuse)
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/health_service.py`
- `truffles-api/app/services/runtime_safety.py`
- `truffles-api/app/services/*integration*` (новый сервис)
- `truffles-api/app/workers/sentinel.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `truffles-api/tests/test_branch_routing_instance.py`
- `truffles-api/tests/test_message_endpoint.py`
- новые тесты guardrails в `truffles-api/tests/`
- `STATE.md` (FACT + evidence before merge for behavior/core)
- `STRUCTURE.md` (если добавляются новые модули)

## Plan
1. Добавить migration + model поля для integration lifecycle (`ok/degraded`) и DB unique guard for `branches.instance_id`.
2. Реализовать integration guardrail service: classify incidents, transition state, audit/alert hooks, dedupe.
3. Интегрировать guardrail hooks в webhook preflight (`unknown_instance_id`, `invalid_secret`) и runtime signal for `inbound_without_outbound`.
4. Усилить simulation isolation: production inbound не может выставить simulation режим; сохранить легальный test path.
5. Подключить периодический watchdog в sentinel worker (interval env, branch scan, auto-remediate state/secret consistency on our side).
6. Обновить console read-model статусов, чтобы отображался factual degraded reason/time.
7. Добавить/обновить тесты + прогоны target test suite.
8. Зафиксировать evidence + обновить `STATE.md` как FACT.

## DoD
- Drift/incident автоматически фиксируется и переводит branch в `degraded` с причиной и timestamp.
- Recovery переводит branch обратно в `ok` только после успешной проверки.
- `Unknown instanceId` и invalid webhook secret дают явные alert/audit сигналы.
- Simulation флаги не влияют на production conversation outbound.
- DB не допускает дубликат `instance_id` между branch (non-null).
- Все новые/изменённые тесты проходят локально в test container.

## Checks
- `scripts/test_api_container.sh`
- `docker exec -i truffles-api pytest /app/tests/test_console_integrations_registry.py -q`
- `docker exec -i truffles-api pytest /app/tests/test_branch_routing_instance.py -q`
- `docker exec -i truffles-api pytest /app/tests/test_message_endpoint.py -q`
- `docker exec -i truffles-api pytest /app/tests/test_integration_guardrails.py -q`

## Evidence
- CI run URL (green) + jobs for affected tests.
- SQL snapshot: branch integration state transitions + unique instance constraint check.
- Trace/decision_meta sample for incident and recovery.
- Audit events sample: detect/degraded/recovered.
- `STATE.md` update before merge (behavior/core change).

## Rollback
- Revert PR commit.
- Apply rollback migration for new columns/index if needed.
- Restart `truffles-api` + `truffles-sentinel` workers.

## No-go
- Никаких hardcoded client_slug/instance_id.
- Никаких ручных DB edits ради "красивого" evidence.
- Никакой логики оркестрации в `_legacy.py` и webhook entrypoints.
- Никаких изменений контракта FACT/COLLECT/HANDOFF.

## Branch / Worktree
- Branch: `feat/2026-02-08-integration-guardrails-a19`
- Worktree: `/home/zhan/worktrees/2026-02-08-integration-guardrails-a19`
- Base ref: `origin/main`
- Merge policy: non-rebase, via PR
- Cleanup: after merge by Brain/Top Architect (`session_end`, remove worktree/branch)

## Риски/блокеры
- Migration может упасть при исторических duplicate `instance_id` -> нужен precheck и безопасное падение с явной причиной.
- Возможны false-positive degraded при кратких сетевых проблемах -> hysteresis/threshold.
- Если Chatflow-side webhook не управляется API, auto-remediate ограничивается нашим контуром и fail-closed режимом.
