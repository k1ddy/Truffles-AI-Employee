# Owner/Admin Wave-10 Report (Subscription Truth Mode: Fail-Closed Contract)

Date
- 2026-02-16

Goal
- Объединить пункты `1/2/3` в один пакет и убрать ложную уверенность во вкладке `Подписка`:
  - не подставлять Starter-лимиты как фактические contract-значения,
  - явно показывать пробелы контракта,
  - давать owner/admin конкретные следующие шаги.

Delivered
- Backend (`GET /console/v1/subscription/summary`):
  - Added `contract_health` block with:
    - `status`: `ok|partial|missing`,
    - `summary`,
    - `gaps[]` (`code/message/severity`),
    - source hints (`quota_source`, `whatsapp_source`, `payment_status_source`),
    - `has_active_onboarding_contract`.
  - Switched subscription limits to fail-closed mode:
    - no automatic fallback of monthly quota/WhatsApp limits from Starter to client contract metrics,
    - missing contract values stay `missing/unknown` in metrics and meters.
  - Kept Starter as reference only (`plan_defaults.reference_only=true`) without affecting overage/remaining calculations.
  - Expanded recommended actions for concrete contract gaps:
    - missing monthly quota,
    - missing WhatsApp limit,
    - missing payment status,
    - missing/partial contract state.
- Frontend (`/subscription`):
  - Added clear diagnostics surface:
    - `Состояние контракта` (`subscription-contract-health`) with status + gaps.
  - Added explicit reference block:
    - `Справка: стандартный Starter` (`subscription-reference-plan`) marked as reference-only.
  - Updated labels to reduce ambiguity (`Нет контракта`, source labels in Russian, severity labels in Russian).
- Tests:
  - Added backend unit tests for contract-health states (`missing/partial/ok`).
  - Extended owner/admin smoke checks to assert new subscription diagnostics sections.

Validation
- Backend:
  - `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py` -> OK.
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py` -> OK.
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `75 passed`.
  - `python3 truffles-api/scripts/generate_openapi.py --check` -> OK.
- Frontend:
  - `npm --prefix console-web ci` -> OK.
  - `npm --prefix console-web run lint` -> OK.
  - `npm --prefix console-web run build` -> OK.
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> OK.

Key files
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/subscription/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/pages/subscription.md`

Result
- Subscription tab now behaves as a business-trust surface:
  - factual usage remains visible,
  - contract gaps are explicit,
  - reference plan is clearly marked as non-factual,
  - owner/admin receives deterministic next actions instead of hidden fallback assumptions.
