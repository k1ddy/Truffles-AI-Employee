# TP-2026-02-15-owner-admin-business-deep-audit-a1

- Название/цель: Провести глубокий business-first аудит Console Plane для роли `Owner/Admin` (неопытные владельцы), зафиксировать критичные UX/операционные/коммерческие разрывы и выдать исполнимый 30/60/90-day план с KPI-контрактом.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW: platform admin baseline + runtime unhealthy), `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `Business/Sales/BILLING_COUNTING.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`.

## Invariant
- Не менять runtime business logic/API contracts: только аналитика, backlog и управленческие артефакты.
- Не нарушать hard-policy/LAW обещания из `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`.
- Все выводы разделять на `FACT` (с evidence) и `INFERENCE` (помечено явно).

## Scope
- Аудит owner/admin критических business-jobs в Console: подписка, прозрачность данных, контроль менеджеров, простые настройки.
- Сбор фактов из текущей реализации UI/API и runtime snapshot.
- Формирование приоритизированного improvement-плана и KPI-contract.

## Out of scope
- Изменения backend/frontend кода продукта.
- Изменения тарифной политики/юридических обязательств.
- Production миграции/деплой.

## Touch-list
- `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-02-15-owner-admin-business-deep-audit-a1.md`
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-business-deep-audit-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать фактический baseline owner/admin (UI/API/runtime + billing/ops transparency).
2. Дополнить baseline внешними источниками по SME digital maturity и service design principles.
3. Сформировать severity-ordered problem map и target operating model для неопытного owner/admin.
4. Сформировать 30/60/90 execution plan + KPI-contract + experiment matrix.
5. Обновить UX backlog owner/admin пунктами P0/P1 с evidence links.

## DoD
- Есть новый report с фактами, приоритизацией, KPI и поэтапным планом.
- В report для каждого крупного вывода указан тип (`FACT`/`INFERENCE`) и источники.
- UX backlog содержит owner/admin проблемы, влияющие на бизнес управление/прозрачность.
- Session артефакты (`SESSION-*`, `SESSION_INDEX`) обновлены.

## Checks
- `rg -n "Owner/Admin|подписк|billing|данн|менеджер|KPI|P0|P1" docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `git diff --stat`

## Evidence
- Runtime snapshot: `https://console.truffles.kz/api/health/full`, `https://api.truffles.kz/admin/version`.
- Internal code/docs references from `docs/CONSOLE_AUDIT/*`, `console-web/src/*`, `truffles-api/app/routers/console.py`, `Business/Sales/BILLING_COUNTING.md`.
- External primary references (OECD, GOV.UK Service Standard, Google SRE, Google HEART).
- Session log updated in `docs/SESSIONS/SESSION-2026-02-15-owner-admin-business-deep-audit-a1.md`.

## Rollback
- `git restore docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md docs/CONSOLE_AUDIT/UX_BACKLOG.md docs/TASK_PACKAGES/TP-2026-02-15-owner-admin-business-deep-audit-a1.md docs/SESSIONS/SESSION-2026-02-15-owner-admin-business-deep-audit-a1.md docs/SESSION_INDEX.md`

## No-go
- Не добавлять невалидированные продуктовые обещания.
- Не менять production данные/trace ради evidence.
- Не выдавать метрики без явного источника/датировки.

## Риски/блокеры
- Runtime metrics volatile; snapshots дают точку во времени, не долгосрочный тренд.
- Часть owner/admin боли требует интервью; без них часть выводов остаётся inference.
- В `main` были локальные конфликтные изменения после stash-pop при sync; текущая работа изолирована в отдельном worktree.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-business-audit-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-business-audit-a1`
- Base ref: `origin/main`
- Merge policy: PR (doc-only допустим как fast-forward в `main` по решению Brain/Top Architect)
- Cleanup: после merge удалить ветку и worktree (Brain/Top Architect)
