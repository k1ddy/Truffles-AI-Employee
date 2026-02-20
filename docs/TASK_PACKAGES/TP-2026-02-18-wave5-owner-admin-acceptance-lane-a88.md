# TP-2026-02-18-wave5-owner-admin-acceptance-lane-a88

- Название/цель: Зафиксировать стабильный owner/admin acceptance lane (auth state + e2e + CI gate), чтобы бизнес-роли проверялись доказуемо и без platform_admin-перекоса.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP (owner/admin acceptance blocked), `SPECS/CONTROL_PLANE.md` (roles/RBAC), `TECH.md` (CI contracts), `docs/REPORTS/2026-02-17-console-postmerge-acceptance-p95-wave123-v1.md`.
- CA_ID: N/A.

## Invariant
- Права/ограничения RBAC не ослабляются.
- Никаких секретов/паролей/токенов в репозитории.
- Platform-admin acceptance lane не деградирует.

## Scope
- Auth fixtures:
  - выделенный owner/admin auth-state для Playwright (отдельно от platform_admin),
  - воспроизводимый login/setup для e2e.
- Test lane:
  - стабильный запуск `owner-admin-business.spec.ts` в local и CI,
  - явный gating в CI для owner/admin-critical UX.
- Reporting:
  - отдельный acceptance артефакт с owner/admin pass/fail + причины.

## Out of scope
- Переписывание owner/admin страниц и бизнес-логики.
- Общий рефактор всего e2e набора.
- Изменение runtime booking/consultant flow.

## Touch-list
- `console-web/e2e/owner-admin-business.spec.ts`
- `console-web/e2e/auth.setup.ts`
- `console-web/e2e/login.spec.ts` (при необходимости)
- `console-web/playwright.config.ts` (если требуется отдельный project/fixture)
- `.github/workflows/ci.yml`
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `docs/REPORTS/2026-02-20-wave5-owner-admin-acceptance-lane-a500.md`
- `STATE.md`

## Plan
1. Формализовать owner/admin auth fixture и отделить его от platform_admin state.
2. Обновить e2e сценарии owner/admin на стабильные test ids и deterministic ожидания.
3. Подключить CI lane с явным fail condition для owner/admin acceptance.
4. Зафиксировать runbook команды (как запускать локально/в CI, как triage).
5. Прогнать local + CI проверки и сохранить evidence.

## DoD
- `owner-admin-business.spec.ts` стабильно проходит в среде с owner/admin auth-state.
- CI содержит отдельный owner/admin gate и не пропускает регресс owner/admin UX.
- Убрана неоднозначность "suite blocked by platform_admin auth state" в acceptance отчетах.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --no-deps --reporter=list`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/platform-admin.spec.ts --project=chromium --no-deps --reporter=list`
- CI workflow run for owner/admin lane (URL evidence required)

## Evidence
- local playwright outputs for owner/admin + platform_admin suites
- CI run URL + failed/passed job/step details
- updated runbook section for owner/admin lane
- `docs/REPORTS/2026-02-20-wave5-owner-admin-acceptance-lane-a500.md`
- `STATE.md` FACT/GAP update

## Rollback
- Откатить CI lane/fixture изменения (git revert).
- Временно вернуть owner/admin gate в advisory mode (документированно и с GAP в `STATE.md`).

## No-go
- Нельзя считать acceptance закрытым только platform_admin suite.
- Нельзя использовать общую auth-state как замену owner/admin credentials.
- Нельзя коммитить реальные credential artifacts/секреты.

## Риски/блокеры
- Нестабильность внешнего auth провайдера (Keycloak/SSO) может давать flaky setup.
- Неполный тестовый owner/admin аккаунт в окружении ломает deterministic lane.
- Runtime degradation может маскировать UX регрессии как infra flake.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave5-owner-admin-acceptance-lane-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave5-owner-admin-acceptance-lane-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
