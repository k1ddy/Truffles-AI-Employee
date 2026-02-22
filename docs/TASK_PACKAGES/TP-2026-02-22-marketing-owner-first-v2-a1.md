# TP-2026-02-22-marketing-owner-first-v2-a1

- Название/цель: Перевести вкладку Marketing в owner-first режим для бизнес-пользователей: понятные сегменты и правила отбора, редактируемые параметры сегментов без кода, прозрачное объяснение причин попадания/исключения, и упрощённый UX-поток кампании.
- Canon refs: `AGENTS.md`, `STATE.md` (marketing NOW/GAP), `STRUCTURE.md`, `TECH.md`, `SPECS/SYSTEM_REFERENCE.md`, `contracts/console_api/openapi.v1.yaml`, `docs/TASK_PACKAGES/TP-2026-02-21-marketing-pro-v1-a300.md`.
- CA_ID: N/A.

## Invariant
- No cross-tenant leakage (`client_id` + `branch_id` everywhere).
- Execute guard stays fail-closed (approval/preflight/runtime health/provider billing).
- No duplicate recipient per campaign.
- Audit trail remains complete for create/update/preview/approval/execute.

## Scope
- Backend:
  - сегменты получают owner-facing catalog (описания + editable параметризация);
  - create/update campaign принимает и валидирует `segment_params`;
  - preview использует effective segment params;
  - audience/preview/preflight возвращают owner-readable explainers.
- API/Contracts:
  - новый endpoint каталога сегментов;
  - расширение campaign/preview/audience схем под segment params + explainers.
- Console UI:
  - owner-first wording (без перегруза инженерными терминами);
  - выбор цели/сегмента + редактируемые параметры;
  - блок "как считается";
  - таблица audience с понятными причинами и suppressions.
- Tests:
  - backend unit/router tests на segment params + catalog + explainers;
  - frontend lint/build + e2e smoke update.

## Out of scope
- Полный visual redesign всей Console.
- Новые каналы кроме WhatsApp.
- ML personalization/content generation.

## Touch-list
- `truffles-api/app/services/marketing/service.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_marketing_service.py`
- `truffles-api/tests/test_console_marketing_campaigns.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/marketing/page.tsx`
- `console-web/e2e/marketing.spec.ts`
- `docs/CONSOLE_AUDIT/pages/marketing.md`
- `STATE.md`

## Plan
1. Добавить backend segment catalog + params validation + effective params resolver.
2. Встроить `segment_params` в create/update/preview и owner-readable explainers.
3. Расширить схемы/OpenAPI/client types.
4. Пересобрать marketing UI в owner-first flow (цель -> правила -> сообщение -> проверка/отправка).
5. Добавить/обновить тесты backend + e2e smoke.
6. Прогнать проверки, обновить docs/state, открыть PR.

## DoD
- Owner видит понятные названия сегментов, что они делают и какие параметры можно менять.
- Параметры сегментов можно редактировать из UI, они реально влияют на preview.
- Audience показывает human-readable причины inclusion/exclusion/suppression.
- API/OpenAPI/types синхронизированы.
- Все целевые тесты/проверки зелёные.

## Checks
- Backend:
  - `python3 -m py_compile truffles-api/app/services/marketing/service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
  - `ruff check truffles-api/app/services/marketing/service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_marketing_service.py truffles-api/tests/test_console_marketing_campaigns.py`
  - `pytest -q truffles-api/tests/test_marketing_service.py truffles-api/tests/test_console_marketing_campaigns.py -k "marketing"`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
- Frontend:
  - `npm --prefix console-web run lint -- --file src/app/marketing/page.tsx --file src/lib/api-client.ts`
  - `npm --prefix console-web run build`
  - `cd console-web && npx playwright test e2e/marketing.spec.ts --project=chromium --reporter=list --no-deps`

## Evidence
- PR URL + CI run URL.
- Diff + test outputs.
- Примеры owner-readable audience reasons в API response.
- Обновление `STATE.md` с FACT.

## Rollback
- `git revert` коммитов owner-first wave.

## No-go
- Нельзя оставлять сегменты непонятными для owner (только кодовые labels).
- Нельзя добавлять client-specific/niche-specific hardcode.
- Нельзя ослаблять execute/preflight safety gates.

## Риски/блокеры
- Для очень больших баз preview может быть тяжёлым: в этой волне закрываем UX/contract/readability; deep async-scale engine — отдельный TP.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-22-marketing-owner-first-v2-a1`
- Worktree: `/home/zhan/worktrees/2026-02-22-marketing-owner-first-v2-a1`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect after merge
