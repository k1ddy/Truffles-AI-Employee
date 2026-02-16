# TP-2026-02-16-owner-admin-wave9-subscription-contract-a88

- Название/цель: Wave-9 (Owner/Admin) — перевести вкладку «Подписка» в полный бизнес-контракт: что куплено по онбордингу (лимиты/каналы/доп. интеграции), что фактически потреблено, и какие действия нужны сейчас.
- Canon refs: `STATE.md` NOW/GAP (commercial transparency gap), `Business/Sales/BILLING_COUNTING.md`, `STRATEGY/PRODUCT.md`, `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md`, `SPECS/CONTROL_PLANE.md`.

## Invariant
- Не менять биллинговую формулу (billable bot outbox messages) и source-of-truth.
- Не ослаблять RBAC owner/admin vs platform_admin.
- Не показывать выдуманные значения: каждый KPI должен иметь fact/meta источник (`kind/source/as_of`).

## Scope
- Backend:
  - расширить `GET /subscription/summary` контрактом entitlements:
    - plan baseline (включено сообщений),
    - channels (включено/используется по типу, начально `whatsapp`),
    - integrations/addons (включено/используется/статус).
  - вычислять usage по сообщениям как сейчас (outbox billable), и добавить usage по каналам/интеграциям из фактического конфигурационного состояния.
  - добавить явные business alerts и recommended actions для owner/admin (без auto-execute).
- Frontend:
  - переработать `/subscription` под 3 блока: «Контракт плана», «Факт использования», «Что делать сейчас».
  - заменить неоднозначные подписи на бизнес-термины на русском.
- Contracts/Tests/Docs:
  - обновить OpenAPI/TS client;
  - покрыть backend + UI smoke сценариями новой структуры.

## Out of scope
- Полная новая invoice/payment engine.
- Автоматическое списание/оплата/провайдер billing sync.
- Изменение core decision pipeline.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_owner_admin.py` (если потребуется helper)
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_rbac.py` (при необходимости)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/subscription/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/REPORTS/2026-02-16-owner-admin-wave9-subscription-contract-v1.md` (new)
- `STATE.md`
- `STRUCTURE.md` (если новые артефакты)
- `docs/SESSIONS/SESSION-2026-02-16-owner-admin-wave9-subscription-contract-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Запустить новую сессию в отдельном worktree от `origin/main`.
2. Добавить backend contract для subscription entitlements/usage/alerts/actions.
3. Обновить frontend `/subscription` для contract+fact+action UX.
4. Обновить OpenAPI и тесты (backend + smoke).
5. Подготовить report + evidence и открыть PR.

## DoD
- Owner/Admin видит подписку как бизнес-контракт: включено, использовано, остаток/перерасход по каждому счётчику.
- Для стандартного плана явно отражено `1000` сообщений и `1 WhatsApp` (если онбординг не переопределил).
- Доп. интеграции отображаются с понятным статусом и действием.
- Никаких выдуманных чисел: всё имеет `fact_meta` или `estimate` с указанием источника.
- Тесты и OpenAPI обновлены, smoke не деградирует.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- API sample: `/tmp/owner_admin_wave9_subscription_summary.json`
- UI smoke list output
- test/lint/build outputs
- report `docs/REPORTS/2026-02-16-owner-admin-wave9-subscription-contract-v1.md`

## Rollback
- Revert wave-9 commit(s), вернуть contract `/subscription/summary` до wave-9.

## No-go
- Нельзя считать manager/system сообщения как billable.
- Нельзя показывать «оплачено/не оплачено» без фактического billing источника.
- Нельзя auto-apply remediation/upgrade без явного подтверждения пользователя.

## Risks/блокеры
- Источники channels/integrations могут быть неполными по части entitlement, нужен safe fallback `unknown`.
- OpenAPI/TS генерация может добавить шум, держать diff точечным.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-owner-admin-wave9-subscription-contract-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-owner-admin-wave9-subscription-contract-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` after green checks.
- Cleanup: Brain/Top Architect after merge.
