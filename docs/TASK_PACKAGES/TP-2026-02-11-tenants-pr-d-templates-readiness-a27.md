# TP-2026-02-11 Tenants PR-D Domain Templates + Readiness Score (a27)

## Название/цель
Добавить следующий product-слой во вкладку Tenants: domain template presets для ускоренного онбординга любой ниши и прозрачный readiness score с блокерами перед Go/No-Go.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: tenants onboarding domain-agnostic + operator clarity)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`

## Invariant
- Existing onboarding flow (autopilot/manual) не ломается.
- `Advanced JSON` fallback сохраняется.
- Existing API contracts unchanged; изменения только UI/validation/presentation.
- Go/No-Go и trace semantics остаются прозрачными.

## Scope
- Domain templates (preset) для `onboarding_contract.purchased` + `domain_slug` (минимум: beauty, clinic, legal, ecom).
- Safe apply template в wizard (явное действие, без скрытых side effects).
- Readiness score panel и явный список блокеров на шаге Go/No-Go.
- Обновление smoke/e2e и документации Tenants.

## Out of scope
- Изменение backend схем, миграции БД.
- Полная переработка IA страницы Tenants.
- Изменение бизнес-правил Go/No-Go на backend.

## Touch-list (files/tables)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-d-templates-readiness-a27.md`
- `docs/SESSION_INDEX.md`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-d-templates-readiness-a27`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-d-templates-readiness-a27`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Добавить типизированные domain templates и UI выбора/применения template в Go/No-Go.
2. Встроить readiness score (процент + blockers + status band) поверх существующих readiness items.
3. Добавить/обновить smoke тесты на templates/readiness.
4. Обновить Tenants audit doc.

## DoD
- Оператор может выбрать template и применить его в draft contract без ручного JSON.
- Readiness score отображается в Go/No-Go и показывает понятные blockers.
- Existing flows и backward compatibility smoke зелёные.

## Checks
- `scripts/session_check.sh`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=http://localhost:3100 E2E_USE_STORAGE_STATE=0 npx --prefix console-web playwright test console-web/e2e/smoke.spec.ts --project=chromium --grep "Tenants"`

## Evidence
- PR URL
- `git status -sb`
- `git diff --stat`
- вывод checks (lint/build/e2e)
- обновлённые docs/session artifacts

## Rollback
- `git revert` последнего PR-D commit (или серии commit'ов PR-D).

## No-go
- Не удалять JSON fallback.
- Не менять backend contracts/DB.
- Не добавлять hardcoded tenant-specific logic.

## Риски/блокеры
- UI complexity в Go/No-Go может вырасти.
- Митигация: компактные блоки, data-testid, ясные подписи и fallback.
