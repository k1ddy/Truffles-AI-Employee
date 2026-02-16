# Owner/Admin UX Simplify v1 (2026-02-16)

Status
- `FACT` (UI diff + smoke-list evidence)
- Scope: owner/admin business-first UX simplification in Console Plane.
- Branch/worktree: `feat/2026-02-16-owner-admin-ux-simplify-a88` / `/home/zhan/worktrees/2026-02-16-owner-admin-ux-simplify-a88`

## 1) Problem

Business users reported that Console is overloaded with technical sections and unclear first actions.

## 2) What changed

### 2.1 Business-first navigation (owner/admin)
- Added default reduced left menu for owner/admin roles.
- Added explicit toggle: `Показать расширенное меню` / `Скрыть расширенное меню`.
- Advanced sections remain available via toggle (no RBAC change, no route removal).
- File: `console-web/src/components/ConsoleShell.tsx`.

### 2.2 Clear next-step plan on `/business`
- Added `Что делать сейчас` block with max 3 prioritized steps.
- Step severity labels translated into business terms: `Срочно | Важно | Планово`.
- Status chip translated into business labels while preserving technical status detail.
- File: `console-web/src/app/business/page.tsx`.

### 2.3 Plain-language settings copy
- Primary settings card text simplified for non-technical owner/admin operators.
- File: `console-web/src/app/settings/page.tsx`.

### 2.4 Smoke adaptation
- Updated owner/admin smoke flow for new toggle and business shortcuts labels.
- File: `console-web/e2e/owner-admin-business.spec.ts`.

## 3) Validation

Commands
- `npm --prefix console-web run lint -- --file src/components/ConsoleShell.tsx --file src/app/business/page.tsx --file src/app/settings/page.tsx --file e2e/owner-admin-business.spec.ts`
- `cd console-web && npx tsc --noEmit --incremental false`
- `npm --prefix console-web run test:e2e:smoke -- --list`

Result
- Lint: pass (`No ESLint warnings or errors`).
- Typecheck: pass.
- Smoke list: owner/admin suite includes updated tests; list generated successfully.

## 4) User-facing effect

- Owner/Admin starts in focused business mode by default (less cognitive noise).
- First actions on `/business` are explicit and role-oriented.
- Core actions remain fast-access; advanced surfaces still reachable without role escalation.

## 5) Risks / Next

- This wave improves UX clarity, but runtime incident pressure (`outbox pending/failed`) still impacts perceived speed and should be resolved in parallel.
- Next UX wave should add quantitative adoption metrics (click-path completion for owner/admin first-session flow).
