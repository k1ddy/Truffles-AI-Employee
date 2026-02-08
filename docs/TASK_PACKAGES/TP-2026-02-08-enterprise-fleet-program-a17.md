# TP-2026-02-08 Enterprise Fleet Program (PR-0 foundation, a17)

## Название/цель
Зафиксировать каноничную операционную модель Enterprise Fleet для управления 100000+ компаний (existing + new), связать её с текущим кодом/доками, и подготовить исполнимый план внедрения (5 PR) с ручной приемкой, рисками и митигациями.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: Control Plane контур частично реализован; enterprise fleet lifecycle не оформлен как единая модель)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `docs/PROCESSES.md`
- `docs/CONSOLE_GUIDE.md`
- `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`

## Invariant
- Не меняем runtime-поведение API/webhook/outbox/RBAC в этом срезе.
- Не ослабляем tenant isolation и fail-closed принципы.
- Не меняем продуктовые обещания (`FACT/COLLECT/HANDOFF`, policy/LAW границы).

## Scope
- Собрать единый Enterprise Fleet blueprint: роли, контуры управления, lifecycle, KPI/SLI, acceptance gates.
- Явно описать управление:
  - уже подключенными компаниями,
  - новыми подключениями,
  - филиалами и филиальными учетками,
  - массовыми операциями,
  - коммерческим состоянием (contract/payment/service state).
- Подготовить PR map (5 PR) с четким DoD и ручной проверкой Owner.
- Зафиксировать risk register + mitigations + evidence model.

## Out of scope
- Реализация backend/frontend фич из PR-1..PR-5.
- Миграции БД и деплой runtime-кода.
- Изменения legacy `/admin/*` поведения.

## Touch-list
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md` (new)
- `docs/PROCESSES.md`
- `SPECS/CONTROL_PLANE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/IMPERIUM_GAPS.yaml`
- `STRUCTURE.md` (если добавится новый постоянный документ)

## Plan
1. Провести canon-audit по текущим боли/ограничениям управления fleet.
2. Сформировать целевую enterprise operating model (state machine + owner actions + KPIs).
3. Разложить реализацию в 5 PR с точным scope/DoD/rollback/no-go.
4. Подготовить owner manual acceptance checklist по каждому PR.
5. Обновить canon-доки и GAP-реестр ссылками на evidence.

## DoD
- Есть единый документ программы с:
  - проблемами/рисками,
  - целевой моделью,
  - 5-PR roadmap,
  - ручной приемкой Owner по каждому шагу,
  - ценностью по ролям (Owner, Platform Admin, Support, Client Owner/Admin, Manager).
- `docs/PROCESSES.md` и `SPECS/CONTROL_PLANE.md` не конфликтуют с новым blueprint.
- Все новые/измененные документы добавлены в `STRUCTURE.md` при необходимости.

## Checks
- `rg -n "Enterprise Fleet|Fleet Registry|Lifecycle|PR-1|PR-5" docs/REPORTS/2026-02-08-enterprise-fleet-program.md docs/PROCESSES.md SPECS/CONTROL_PLANE.md docs/CONSOLE_GUIDE.md`
- `scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- Список обновленных канон-доков с ключевыми секциями
- Ссылка на сессионный лог `docs/SESSIONS/SESSION-2026-02-08-enterprise-fleet-program-a17.md`

## Rollback
- Revert doc-only commit с этим blueprint и восстановить предыдущие версии документов.

## No-go
- Не объявлять runtime-ready фичи без кода/тестов/evidence.
- Не менять policy/LAW/product promises под документ.
- Не добавлять расплывчатые статусы без owner-action и measurable KPI.

## Риски/блокеры
- Риск "документ ради документа" без исполнимости.
  - Митигация: каждое требование должно иметь PR-owner, DoD и ручную проверку.
- Риск конфликтов между `PROCESSES` и `CONTROL_PLANE`.
  - Митигация: cross-reference матрица и явные source-of-truth пометки.
- Риск завышенных ожиданий reliability без SLO.
  - Митигация: фиксировать только измеримые SLI/SLO + evidence pipeline.
