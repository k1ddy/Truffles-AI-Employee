# TP-2026-02-18-wave0-1-integrity-gate-a88

- Название/цель: Ввести обязательный data-integrity gate перед remediation/feature rollout: выявлять и блокировать дубли, конфликты и орфаны в ключевых runtime таблицах.
- Canon refs: `AGENTS.md` (FACT vs PLAN, stop-the-line, no manual DB cleanup for optics), `STATE.md` NOW/GAP (runtime blockers), `SPECS/ARCHITECTURE.md` (outbox idempotency, trace/meta contracts), `TECH.md` (core tables/outbox), `SPECS/CONTROL_PLANE.md` (tenant fail-closed).
- CA_ID: N/A.

## Invariant
- Gate только читает и диагностирует данные; не "лечит" базу автоматически.
- Никаких destructive/manual cleanup команд без отдельного подтвержденного TP.
- Результат gate воспроизводим и используется как блокирующий precondition для Wave 0/1/2/3.

## Scope
- Определить и внедрить набор integrity checks по таблицам:
  - `outbox_messages` (idempotency/duplicate send risk),
  - `handovers` + `conversations` (state consistency/open handover uniqueness),
  - `appointments` + `visits` + `appointment_audit` (status/visit consistency, overlap anomalies),
  - `agent_memberships` (duplicate active memberships and scope conflicts),
  - orphan references в операционных таблицах.
- Сформировать единый gate report: `PASS/WARN/FAIL` с детальными violation-кодами.

## Out of scope
- Автоматический data repair.
- Изменение бизнес-логики диалогов.
- Добавление новых продуктовых сущностей (marketing/campaign).

## Touch-list
- `ops/diagnose.py` (или отдельный integrity runner в `ops/`)
- `ops/sql/` (новые SQL check templates)
- `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `docs/REPORTS/<date>-wave0-1-integrity-gate-a88.md`
- `STATE.md`

## Plan
1. Формализовать integrity contract (check-id, severity, sql, pass criteria).
2. Реализовать runner, который выполняет checks и выводит machine-readable summary.
3. Подключить gate в preflight Wave 0 remediation runbook.
4. Прогнать gate на текущем runtime и сохранить baseline evidence.
5. Зафиксировать violations как GAP или PASS как precondition для дальнейших wave.

## Integrity checks (minimum set)
1. `OUTBOX_DUPLICATE_IDEMPOTENCY`
  - поиск конфликтных дублей по idempotency ключам/повторной доставке.
2. `OUTBOX_STUCK_PROCESSING`
  - зависшие `PROCESSING` старше порога.
3. `HANDOVER_OPEN_UNIQUENESS`
  - более одного open handover на диалог (`pending/active`).
4. `CONVERSATION_STATE_CONSISTENCY`
  - `manager_active/pending` без валидного handover контекста.
5. `APPOINTMENT_TIME_CONFLICT`
  - конфликтующие active appointments на одного специалиста/слот.
6. `APPOINTMENT_VISIT_CONSISTENCY`
  - несогласованность `appointments.status` и фактов в `visits`.
7. `MEMBERSHIP_DUPLICATE_ACTIVE`
  - дубли активных memberships одного scope/role для одного агента/target.
8. `ORPHAN_REFERENCE_CHECK`
  - сообщения/аудит/операционные записи с битой ссылкой на родительские сущности.

## DoD
- Есть reproducible integrity runner и отчет с `PASS/WARN/FAIL`.
- Для каждого FAIL: violation code, SQL evidence, affected rows, severity.
- Wave 0 remediation и все дальнейшие wave запускаются только после `FAIL=0` или явного waiver в TP.
- Никаких несанкционированных data edits в рамках gate.

## Checks
- `python3 ops/diagnose.py integrity-gate --client-slug <slug> --pretty --output /tmp/integrity_gate_<run>.json`
- `python3 ops/diagnose.py integrity-gate --client-slug <slug> --fail-on-critical --output /tmp/integrity_gate_<run>_gate.json`
- SQL spot-check по каждому `FAIL` из отчета (сохранить в `/tmp/sql_integrity_<check>_<run>.txt`)

## Evidence
- integrity summary JSON + gate JSON
- SQL outputs по violations
- report artifact `docs/REPORTS/<date>-wave0-1-integrity-gate-a88.md`
- `STATE.md` запись:
  - `FACT` при `FAIL=0`,
  - `GAP` при `FAIL>0` с violation list

## Rollback
- Отключить gate integration в runbook/CI только через явный waiver и запись GAP.
- Revert изменения runner/runbook (git revert).

## No-go
- Нельзя продолжать feature rollout при `FAIL` в critical integrity checks.
- Нельзя "чинить" данные вручную ради прохождения gate без отдельного approved TP.
- Нельзя игнорировать duplicate/conflict findings как "шум".

## Риски/блокеры
- На больших объемах SQL checks могут быть тяжелыми без оптимизации/индексов.
- Часть historical данных может требовать отдельного remediation пакета.
- Без четкой severity-модели gate может быть либо слишком шумным, либо слепым.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave0-1-integrity-gate-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave0-1-integrity-gate-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
