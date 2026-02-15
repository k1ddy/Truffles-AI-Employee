# TP-2026-02-15-owner-admin-wave4-action-loop-a1

- Название/цель: Выполнить Wave-4 owner/admin control loop целиком: пост-merge 24h контроль (evidence), closed-loop действие из Team KPI, onboarding-lite в Settings и subscription transparency v2.
- Canon refs: `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `Business/Sales/BILLING_COUNTING.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/REPORTS/2026-02-15-owner-admin-wave3-simple-settings-v1.md`.

## Invariant
- Не ослаблять RBAC/tenancy gates (`business:read`, `settings:write`, branch scope).
- Не менять billing формулу: источник истины по-прежнему `outbox_messages` + канон `BILLING_COUNTING.md`.
- Не подменять runtime evidence тестами: обязателен `livecheck-auto + explain`.

## Scope
- Backend:
  - расширить `GET /console/v1/subscription/summary` полями прозрачности v2:
    - next billing date, alert level/message, projected overage semantics.
- Frontend:
  - `Team Performance`: добавить closed-loop CTA "Применить быстрый профиль 5/30/60" с confirm.
  - `Settings`: onboarding-lite default (SLA, эскалация, Telegram, подписка), сложные блоки под `Расширенные`.
  - `Subscription`: alert band (80/100), next billing date, projected overage block, explicit overage policy message.
- QA:
  - обновить e2e smoke для нового UX.
  - выполнить live-check evidence (`ca10-outbox` + explain).

## Out of scope
- Полный redesign `ProvisioningWizard`.
- Изменение reminder/escalation бизнес-алгоритмов.
- Новая invoice/subscription DB модель.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/business/team-performance/page.tsx`
- `console-web/src/app/settings/page.tsx`
- `console-web/src/app/subscription/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/pages/settings.md`
- `docs/CONSOLE_AUDIT/pages/subscription.md`
- `docs/CONSOLE_AUDIT/pages/business-team-performance.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/CONSOLE_AUDIT/INDEX.md`
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave4-action-loop-v1.md`
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-wave4-action-loop-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить backend contract для subscription transparency v2 и unit tests.
2. Реализовать closed-loop CTA в Team KPI.
3. Перевести Settings в onboarding-lite default + advanced toggle.
4. Обновить Subscription page под v2 alert/projection semantics.
5. Обновить e2e smoke на новый UX.
6. Прогнать проверки + livecheck evidence + задокументировать результат.

## DoD
- `Team KPI` позволяет owner/admin применить `5/30/60` с подтверждением.
- `Settings` по умолчанию показывает только 4 бизнес-поля: SLA, эскалация, Telegram, подписка; сложное скрыто в `Расширенные`.
- `Subscription` показывает дату следующего списания, 80/100 alert, и понятное правило overage.
- Есть `livecheck-auto + explain` evidence и KPI snapshot.
- Проверки `ruff`, `pytest`, `next lint`, `next build`, e2e smoke list зелёные.

## Checks
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`
- `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca10-outbox --client-slug demo_salon --base-url http://localhost:8000 --noise none --reset-before-suite --poll-timeout 30 --timeout 20`
- `python3 ops/diagnose.py explain --client-slug demo_salon --message-id LC-DEDUP-20260215-104354-4cbfd75e --minutes 60 --limit 1`

## Evidence
- Livecheck logs:
  - `/tmp/livecheck_owner_wave4_20260215-154354.log`
  - `/tmp/livecheck_owner_wave4_explain_LC-DEDUP-20260215-104354-4cbfd75e.log`
- KPI snapshot:
  - `/tmp/owner_admin_wave4_kpi_snapshot_20260215-154458.json`
- PR diff + CI checks.

## Rollback
- Revert Wave-4 commit(s) on this branch; fallback remains Wave-3 behavior from `main`.

## No-go
- Нельзя публиковать "следующее списание/перерасход" как финансовый инвойс-движок.
- Нельзя открывать write path в Team KPI без backend `settings:write` permission.
- Нельзя показывать advanced provisioning как default для owner/admin lite-mode.

## Risks/блокеры
- `console.py` и `ProvisioningWizard.tsx` остаются крупными; приоритет на безопасные локальные изменения.
- KPI runtime на проде уже `unhealthy`; post-merge monitoring обязателен для интерпретации бизнес-метрик.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-wave4-action-loop-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-business-audit-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после зелёных checks.
- Cleanup: Brain/Top Architect после merge.
