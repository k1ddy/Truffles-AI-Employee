# TP-2026-02-11 Tenants PR-H Quality Completion (a30)

## Название/цель
Довести вкладку `Tenants` до операционного уровня `onboarding + change + decommission` без потери текущих возможностей и без дрейфа канона.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants findings and follow-up)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-ef-validators-ia-a27.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-g-lifecycle-modal-a29.md`

## Invariant
- RBAC и tenant isolation не ослабляются.
- Lifecycle API semantics (`archive/restore`) не меняются.
- Branch-change и confirmation contracts не ломаются.
- Critical actions остаются только с явным подтверждением.

## Scope
- `Decommission` UX hardening:
  - lifecycle modal с четким pre-submit checklist,
  - explicit impact summary до отправки.
- Практичный audit trail:
  - понятный блок последних lifecycle действий (status/time/reason/trace).
- UX copy cleanup:
  - операторские формулировки CTA и подсказок без лишней техно-лексики.
- Smoke hardening для Tenants:
  - modal/checklist/audit contract selectors и проверки.
- Доки в sync с фактическим UI/API.

## Out of scope
- Новый backend service layer/миграции без явной необходимости.
- Массовые bulk lifecycle операции.
- Перестройка core runtime/message pipeline.

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-h-quality-completion-a30.md`
- `docs/SESSION_INDEX.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-h-quality-completion-a30.md`
- Optional if backend update is required:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_admin_provisioning.py`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-h-quality-completion-a30`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-h-quality-completion-a30`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Зафиксировать UX-контракт modal/checklist/audit (state + data-testid).
2. Реализовать checklist и расширенный audit trail в `Tenants`.
3. Обновить copy и CTA для operator-first читаемости.
4. Обновить smoke-тесты Tenants по новому контракту.
5. Синхронизировать `tenants.md`, прогнать проверки и собрать evidence.

## DoD
- Lifecycle action выполняется только через modal с checklist + reason + confirm.
- Audit trail показывает action/result/time/reason/trace_id (если есть).
- Тексты и CTA понятны оператору без чтения кода.
- Обязательные проверки зелёные.

## Checks
- `scripts/session_check.sh`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USE_STORAGE_STATE=1 E2E_USERNAME=admin E2E_PASSWORD=admin npx --prefix console-web playwright test console-web/e2e/smoke.spec.ts --project=chromium --grep "Tenants"`
- Optional if backend touched:
  - `pytest -q truffles-api/tests/test_console_admin_provisioning.py`

## Evidence
- PR URL
- `git status -sb`
- `git diff --stat`
- outputs of checks
- updated docs/session artifacts

## Rollback
- `git revert` commit(s) PR-H by touch-list.

## No-go
- Не возвращать browser-native `prompt/confirm`.
- Не ослаблять validators/immutable guards из PR-EF.
- Не подгонять поведение hardcode'ами ради smoke.

## Риски/блокеры
- Риск перегрузки экрана деталями.
- Митигация: compact checklist/audit blocks, clear hierarchy, stable `data-testid`.
