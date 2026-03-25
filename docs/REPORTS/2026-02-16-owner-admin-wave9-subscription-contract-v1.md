# Owner/Admin Wave-9 Report (Subscription Contract = Plan + Fact + Action)

Date
- 2026-02-16

Goal
- Убрать неоднозначность вкладки `Подписка` для owner/admin и связать её с реальным бизнес-контрактом:
  - что включено по плану,
  - что реально использовано,
  - что делать сейчас, если есть риск.

Delivered
- Backend (`GET /console/v1/subscription/summary`):
  - Добавлены платежные факты из onboarding-contract:
    - `payment_status`, `payment_confirmed_at`, `payment_status_source`, `payment_status_message`.
  - Добавлен блок базового стандарта плана:
    - `plan_defaults` (`Starter`, `1000` сообщений, `1` WhatsApp).
  - Добавлен единый read-model по лимитам и факту:
    - `meters[]` для сообщений, каналов (`whatsapp/telegram/instagram`) и доп. интеграций (`calendar/crm/knowledge_upload/analytics/auto_learn`).
    - Статусы: `ok|warning|limit_reached|over_limit|not_included|included_not_configured|unknown`.
  - Добавлен блок действий:
    - `recommended_actions[]` с severity и безопасными CTA без auto-execute.
  - Добавлена диагностика источников:
    - лимиты каналов резолвятся из `company.billing_info` / `client.config.billing`, fallback в onboarding purchased;
    - если явного контракта нет, используется прозрачный fallback стандартного плана с note.
- Frontend (`/subscription`):
  - Добавлены owner-friendly блоки:
    - `Контракт и статус оплаты`,
    - `Лимиты по направлениям`,
    - `Что делать сейчас`.
  - Сохранены существующие блоки квоты/прогноза/evidence.
- Tests:
  - Расширены backend unit tests для новых резолверов и статусов.
  - Smoke e2e расширен проверками новых subscription-секций.

Validation
- Backend:
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py` -> OK.
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `72 passed`.
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py` -> OK.
  - `python3 truffles-api/scripts/generate_openapi.py --check` -> OK (path/method drift отсутствует).
- Frontend:
  - `npm --prefix console-web run lint` -> OK.
  - `npm --prefix console-web run build` -> OK.
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> OK (список smoke suite получен, включает owner-admin subscription flow).

Key files
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/subscription/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`

Result
- Owner/Admin теперь видит подписку как управляемый бизнес-контур, а не как набор «сырых цифр»:
  - контракт плана,
  - платежный статус,
  - фактическое потребление по каждому направлению,
  - приоритетные следующие шаги.
