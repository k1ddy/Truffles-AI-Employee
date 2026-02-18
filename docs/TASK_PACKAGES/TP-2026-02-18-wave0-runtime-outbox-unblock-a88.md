# TP-2026-02-18-wave0-runtime-outbox-unblock-a88

- Название/цель: Остановить `critical` деградацию runtime (outbox backlog), при этом строго отделить внешние billing-блоки (`ChatFlow unpaid`) от реальных runtime/contract сбоев.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP (outbox critical), `SPECS/CONTROL_PLANE.md` (fail-closed + Ops evidence), `TECH.md` (outbox/env contract), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-08 runtime health), `docs/REPORTS/2026-02-17-console-postmerge-acceptance-p95-wave123-v1.md`.
- CA_ID: N/A (platform runtime remediation wave).

## Invariant
- Не менять user-facing бизнес-логику консультанта/booking/policy.
- Не делать DB cleanup/trace cleanup ради "красивых" метрик.
- Все массовые execute-действия только через `dry_run -> confirmation -> execute`.
- Ошибки класса `ChatFlow unpaid` считать `expected_external_block`, а не runtime incident.

## Scope
- Запустить `Wave 0.1` integrity gate до remediation loop (`docs/TASK_PACKAGES/TP-2026-02-18-wave0-1-integrity-gate-a88.md`).
- Зафиксировать и отработать outbox remediation loop через текущий Ops контур.
- Ввести и применить классификацию причин outbox сбоев:
  - `expected_external_block` (например, `ChatFlow unpaid`),
  - `unexpected_failure` (runtime/contract/provider drift, требующий remediation/incident).
- Выявить основные причины `FAILED`/`PENDING` и закрыть именно `unexpected_failure` блокеры (provider/auth/instance routing/retry path).
- Обновить runtime guard evidence для Platform Admin и Owner/Admin (`T+0`, `T+24`).

## Out of scope
- Рефактор core webhook/decision.
- Новые продуктовые фичи (marketing/campaign/visit UI).
- Масштабная архитектурная перестройка (без DEC).

## Touch-list
- `ops/console_platform_admin_kpi_snapshot.py`
- `ops/console_owner_admin_kpi_snapshot.py`
- `ops/diagnose.py` (только если нужен диагностический фикс)
- `truffles-api/app/routers/console.py` (только если нужен API-level reason classification output)
- `truffles-api/app/schemas/console.py` (только если нужен contract for classification fields)
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `docs/REPORTS/` (новый remediation report)
- `STATE.md` (FACT/GAP update)

## Plan
1. Выполнить integrity checks по `Wave 0.1` и зафиксировать отсутствие конфликтов/дубликатов как precondition.
2. Снять baseline: health + outbox queue + guard snapshots (`platform_admin`, `owner/admin`).
3. Разложить backlog по причинам (status/last_error/age/branch/client/provider) с меткой `expected_external_block` vs `unexpected_failure`.
4. Прогнать remediation loop только по `unexpected_failure` (dry-run, затем подтвержденный execute для безопасных операций).
5. Переснять `T+0` и `T+24` snapshots, сравнить с baseline.
6. Зафиксировать evidence + stop-the-line verdict в `STATE.md`.

## DoD
- `console health` не `unhealthy` в контрольном окне.
- Outbox guard выходит из `critical` минимум в `warning` (target: `pending < 1000`, `failed < 300`; stretch: `pending < 500`, `failed < 100`).
- В отчете причины outbox сбоев разнесены по классам:
  - `expected_external_block` (billing/provider account issues, включая `ChatFlow unpaid`),
  - `unexpected_failure` (реальные инциденты платформы).
- `expected_external_block` не триггерит ложный platform incident, но считается операционным ограничением в отчете.
- Есть reproducible evidence по baseline/replay (`T+0`/`T+24`) и список принятых/отклоненных remediation actions.
- Нет побочных регрессий по tenant isolation и RBAC.

## Checks
- `curl -sS https://console.truffles.kz/api/health/full`
- `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_<run>.json`
- `python3 ops/console_owner_admin_kpi_snapshot.py --client-slug demo_salon --pretty --output /tmp/owner_admin_kpi_<run>.json`
- `python3 ops/console_platform_admin_kpi_snapshot.py --fail-on-breach --fail-level critical --output /tmp/platform_admin_kpi_<run>_gate.json`
- `python3 ops/console_owner_admin_kpi_snapshot.py --client-slug demo_salon --fail-on-breach --fail-level critical --output /tmp/owner_admin_kpi_<run>_gate.json`
- SQL/diag breakdown with classification mapping for `outbox_messages.last_error`

## Evidence
- health payload with timestamp (`/tmp/console_health_<run>.json`)
- platform snapshot + gate output
- owner/admin snapshot + gate output
- SQL/diag breakdown for `outbox_messages` (`pending/failed age, reason, scope, class`)
- classification table for reasons (`expected_external_block` vs `unexpected_failure`)
- report artifact in `docs/REPORTS/<date>-wave0-runtime-outbox-unblock-a88.md`
- `STATE.md` FACT/GAP entry (before merge for behavior/core impact)

## Rollback
- Остановить execute-remediation, вернуть режим `dry_run` only.
- Откатить только измененные ops/runbook скрипты/доки (git revert).
- Если remediation даёт ухудшение, зафиксировать incident и вернуться к последнему стабильному runbook шагу.

## No-go
- Нельзя считать wave закрытым при `guard.status=critical`.
- Нельзя запускать продуктовые rollout (marketing/visit wave) до выхода из critical runtime.
- Нельзя смешивать runtime remediation с не связанными UI/feature изменениями в одном PR.
- Нельзя смешивать `ChatFlow unpaid` с runtime defect-class инцидентами.

## Риски/блокеры
- Provider-side outages/auth drift могут удерживать backlog в critical.
- Неочевидные retry storms при частичной деградации канала.
- Ограниченный доступ к owner/admin auth-state может замедлить acceptance evidence.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave0-runtime-outbox-unblock-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave0-runtime-outbox-unblock-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
