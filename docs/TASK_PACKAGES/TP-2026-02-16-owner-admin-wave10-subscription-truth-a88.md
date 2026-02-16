# TP-2026-02-16-owner-admin-wave10-subscription-truth-a88

- Название/цель: Wave-10 (Owner/Admin) — объединить пункты `1/2/3` в один production-пакет для вкладки `Подписка`: убрать любые «выдуманные» лимиты, показывать только подтвержденный контракт/факт, и давать диагностируемые следующие действия при отсутствии или неполноте данных.
- Canon refs: `STATE.md` NOW (wave-9 done, trust gap in user feedback), `Business/Sales/BILLING_COUNTING.md`, `STRATEGY/PRODUCT.md`, `docs/REPORTS/2026-02-16-owner-admin-wave9-subscription-contract-v1.md`, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_AUDIT/pages/subscription.md`.

## Invariant
- Не менять биллинговую формулу (`outbox_messages` + billable filters) и source-of-truth.
- Не ослаблять RBAC для owner/admin/platform_admin.
- Не подставлять дефолтные числа как факт по клиенту: при отсутствии контракта показывать `unknown/missing` + action.

## Scope
- Backend (`GET /subscription/summary`):
  - fail-closed contract mode: если лимит не зафиксирован в контрактных источниках, поля quota/meter limits не автозаполняются Starter-значениями как факт;
  - добавить явный `contract_health` блок (status, gaps, source hints) для диагностики причин missing/partial contract;
  - сохранить Starter baseline только как справочный эталон (`reference`), не влияющий на расчёт статусов/overage;
  - усилить `recommended_actions`: при `missing/partial` контракте выдавать точные шаги (где исправить и что именно отсутствует).
- Frontend (`/subscription`):
  - явно развести секции `Факт`, `Контракт`, `Справка`;
  - убрать UX-двусмысленность: где `missing`, показывать русский статус «Нет подтвержденного значения», а не numeric fallback;
  - добавить диагностическую карточку `Состояние контракта` с gap-списком.
- Tests/contracts/docs:
  - unit tests на fail-closed поведение и contract-health;
  - smoke e2e ожидания новых блоков;
  - обновить docs report + `STATE.md` evidence.

## Out of scope
- Новая invoice/subscription DB модель.
- Автозаполнение contract-данных миграциями в БД.
- Изменение runtime messaging/outbox pipeline.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/subscription/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/pages/subscription.md`
- `docs/REPORTS/2026-02-16-owner-admin-wave10-subscription-truth-v1.md` (new)
- `STATE.md`
- `STRUCTURE.md` (если добавится новый report)
- `docs/SESSIONS/SESSION-2026-02-16-owner-admin-wave10-subscription-truth-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Создать сессию/ветку в отдельном worktree от `origin/main`.
2. Внести backend fail-closed changes + contract-health schema/response.
3. Обновить frontend `/subscription` (факт/контракт/справка + diagnostics).
4. Обновить unit/e2e тесты и проверить openapi/lint/build.
5. Обновить report/STATE/STRUCTURE и подготовить PR.

## DoD
- При отсутствии contract quota/channels нет подстановки Starter в рабочие метрики и статус overage.
- В UI есть отдельный диагностический блок, который объясняет причину missing/partial contract и следующий шаг.
- Starter (`1000`, `1 WhatsApp`) отображается только как reference baseline, а не как факт клиента.
- Все новые поля/секции покрыты тестами и не ломают smoke.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- test/lint/build outputs
- API contract sample (subscription summary with missing contract path)
- report: `docs/REPORTS/2026-02-16-owner-admin-wave10-subscription-truth-v1.md`
- `STATE.md` запись с фактическими checks/evidence

## Rollback
- Revert commit(ы) wave-10, вернуться к wave-9 subscription contract.

## No-go
- Нельзя использовать справочный Starter как billing fact по клиенту.
- Нельзя показывать `payment confirmed/pending` без источника.
- Нельзя скрывать missing-data причины от owner/admin.

## Risks/блокеры
- Возможен UI-шум при большом количестве contract gaps; держать список коротким и детерминированным.
- OpenAPI/typegen drift при добавлении новых response полей.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-owner-admin-wave10-subscription-truth-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-owner-admin-wave10-subscription-truth-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` after green checks
- Cleanup: Brain/Top Architect after merge
