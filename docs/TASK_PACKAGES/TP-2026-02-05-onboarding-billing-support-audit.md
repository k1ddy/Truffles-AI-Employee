# TP-2026-02-05-onboarding-billing-support-audit

- Название/цель: Завершить процессный контур "согласие → оплата → онбординг → go-live → регулярная оплата → техподдержка" и финализировать юридические/онбординг/поддержка шаблоны, а также канонизировать правила биллинга.
- Canon refs: `STATE.md` (NOW: minimum data contract + SAFE_MODE; GAP RU/KZ variants; GAP safe-mode semantics conflict; DONE: draft legal/support/onboarding templates), `docs/PROCESSES.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/SYSTEM_REFERENCE.md` (Onboarding Test SOP), `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`, `Business/Sales/BILLING_COUNTING.md`.

## Invariant
- Не добавлять новых обещаний/обязательств вне `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`.
- Без изменений поведения/кода; только документация/шаблоны.
- Сохранять канон LAW/policy/эскалации.

## Scope
- Актуализировать `docs/PROCESSES.md`: процессный раздел + обновлённый список GAP после финализации документов.
- Финализировать шаблоны: `Business/Legal/*.md` (договор/NDA/политика/счёт), `Business/Onboarding/*`, `Business/Support/Регламент_техподдержки.md`.
- Канонизировать правила биллинга: `Business/Sales/BILLING_COUNTING.md` (DRAFT → CANON или явный "not in scope").
- Обновить статусный реестр: `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`.

## Out of scope
- Любые изменения в коде/схемах/DB.
- Изменение Control Plane UI/RBAC/логики.
- Автоматизация биллинга/оплаты.

## Touch-list
- `docs/PROCESSES.md`
- `Business/Legal/ДОГОВОР.md`
- `Business/Legal/NDA.md`
- `Business/Legal/ПОЛИТИКА_ОБРАБОТКИ_ДАННЫХ.md`
- `Business/Legal/СЧЕТ_ШАБЛОН.md`
- `Business/Onboarding/Чеклист_запуска.md`
- `Business/Onboarding/Инструкция_клиента.md`
- `Business/Support/Регламент_техподдержки.md`
- `Business/Sales/BILLING_COUNTING.md`
- `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`

## Plan
1) Проверить шаблоны legal/onboarding/support и убрать плейсхолдеры Truffles там, где есть факты.
2) Привести документы к канону (без новых обещаний; ссылки на `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`).
3) Решить статус биллинга: CANON или явный "not in scope", обновить `Business/Sales/BILLING_COUNTING.md`.
4) Обновить `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md` статусы.
5) Актуализировать GAP и ссылки в `docs/PROCESSES.md`.

## DoD
- Шаблоны legal/onboarding/support содержат подтверждённые реквизиты Truffles и не содержат новых обещаний.
- `Business/Sales/BILLING_COUNTING.md` имеет финальный статус (CANON или explicit out-of-scope).
- `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md` отражает актуальные статусы.
- `docs/PROCESSES.md` обновлённый GAP список соответствует факту.

## Checks
- Manual review (docs only).

## Evidence
- Обновлённые документы в `Business/*` и `docs/PROCESSES.md`.
- Обновление `STATE.md` не требуется (doc/process), если не фиксируются новые факты выполнения продукта.

## Rollback
- Откатить изменения в `docs/PROCESSES.md` и `Business/*`.

## No-go
- Добавление неканоничных обещаний/SLA.
- Любые изменения кода или данных.

## Риски/блокеры
- Конфликт SAFE_MODE семантики (FACT/COLLECT/HANDOFF vs COLLECT/HANDOFF) в каноне.
- RU/KZ варианты для user-facing строк не формализованы (GAP).
- Юридические формулировки могут требовать дополнительной валидации owner/legal.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-05-onboarding-billing-support-a11`
- Worktree: `/home/zhan/worktrees/2026-02-05-onboarding-billing-support-a11`
- Base ref: `origin/main`
- Merge policy: PR required (changes outside `docs/**`).
- Cleanup: удалить worktree/branch после merge.
