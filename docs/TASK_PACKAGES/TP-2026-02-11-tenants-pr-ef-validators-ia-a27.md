# TP-2026-02-11 Tenants PR-EF Validators + IA Uplift (a27)

## Название/цель
Укрепить вкладку Tenants для production-onboarding: строгие input-контракты и immutable-guards на backend + более явная операторская IA/подсказки на UI для безопасного и понятного онбординга.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: tenants onboarding clarity + contract strictness)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Invariant
- Existing tenants CRUD/lifecycle/change-management flows не ломаются.
- Lifecycle для клиента остаётся только через `archive/restore` endpoints.
- Branch-change draft/validate/publish/rollback contract остаётся backward-compatible.
- UI остаётся role-safe (`platform_admin` / provisioning write), без ослабления guardrails.

## Scope
- Backend:
  - усилить strict validation для tenant-edit payloads (без неявных coercions),
  - добавить точечные immutable guards для полей, которые не должны меняться через generic patch,
  - улучшить error-сообщения для операторов (expected format).
- Frontend:
  - явные input contracts/format hints в Tenants edit forms,
  - IA uplift верхнего уровня (операционный guide-блок + clearer action semantics),
  - согласовать UI с backend strictness.
- Tests/docs:
  - добавить/обновить unit+smoke проверки под новые контракты,
  - синхронизировать `docs/CONSOLE_AUDIT/pages/tenants.md`.

## Out of scope
- Миграции БД и изменение таблиц.
- Изменение runtime booking/policy core логики.
- Полный редизайн Tenants page.

## Touch-list (files/tables)
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `console-web/src/app/tenants/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-ef-validators-ia-a27.md`
- `docs/SESSION_INDEX.md`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-ef-validators-ia-a27`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-ef-validators-ia-a27`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Backend contract hardening: strict model/input checks + immutable guards in tenants patch flows.
2. Backend tests update/add for strict validators and immutable behavior.
3. Frontend IA uplift and explicit field format contracts in Tenants forms.
4. Smoke/docs sync for dual-contract stability and operator clarity.
5. Validate (`session_check`, pytest, lint/build, targeted smoke) and prepare PR evidence.

## DoD
- Invalid tenant edit inputs fail fast with deterministic `INVALID_PARAM`.
- Immutable lifecycle-sensitive fields are protected from generic patch misuse.
- UI clearly показывает expected format и ограничения для ключевых полей.
- Targeted backend/frontend checks green; docs synced.

## Checks
- `scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `E2E_USE_STORAGE_STATE=1 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USERNAME=admin E2E_PASSWORD=admin npx --prefix console-web playwright test console-web/e2e/smoke.spec.ts --grep "Tenants" --project=chromium`

## Evidence
- PR URL
- `git status -sb`
- `git diff --stat`
- outputs of checks above
- updated audit doc + session artifacts

## Rollback
- `git revert` PR-EF commit(s) in reverse order.

## No-go
- Не менять DB schema/миграции.
- Не ослаблять текущие lifecycle safety guards.
- Не добавлять tenant-specific hardcoded logic.

## Риски/блокеры
- Слишком агрессивная strictness может поломать текущие payloads.
- Митигация: локальные тесты + targeted smoke + backward-compatible error handling.
