# TP-2026-03-23-console-selection-gate-stabilization-a1

- Block ID: `console-selection-gate-stabilization-a1`
- Название/цель: устранить повторное появление зависающего серого selection gate на `https://console.truffles.kz/` после логина под multi-company аккаунтами (`admin/admin`) и сделать поведение gate устойчивым к auth/session drift.
- Canon refs: `STATE.md` (`DONE: Console session refresh guard signs out on token refresh failure to unblock selection overlay`, `DONE: Console-web prod build refreshed after selection overlay fix`), `docs/SESSIONS/SESSION-2026-02-03-console-prod-overlay-a6.md`, `STRUCTURE.md` (`console-web/src/components/ConsoleShell.tsx`, `console-web/src/lib/console-context-storage.ts`, `console-web/src/lib/console-scope-gate.ts`, `console-web/e2e/`), `docs/CONSOLE_GUIDE.md`, `TECH.md`.

## Invariant

- RBAC и tenant isolation остаются fail-closed: не сохраняем недоступный `company/client/branch`.
- Явный logout продолжает очищать локальный console context.
- Auth/session failure не должен приводить к зависшему/stale gate или потере последнего валидного selection scope без серверного reason-code.

## Scope

- Frontend стабилизация `ConsoleShell` auth-failure path и selection-gate rendering path.
- Централизация поведения при auth failure: чистим query cache, но не уничтожаем последний валидный selection scope.
- UI hardening selection gate, чтобы он не выглядел как серое зависшее окно.
- Regression coverage для multi-company selection gate и auth/session drift path.

## Out of Scope

- Изменение server-owned session model или перенос scope из localStorage в backend persistence.
- Изменение backend auth contract, `console_auth.py` selection semantics и OIDC/Keycloak конфигурации.
- Полный redesign global shell/nav beyond selection-gate hotfix.

## Touch-list

- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/console-context-storage.ts`
- `console-web/src/lib/console-scope-gate.ts`
- `console-web/src/components/LoginButton.tsx`
- `console-web/e2e/smoke.spec.ts`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-stabilization-a1.md`

## Work mode

- `implementation`

## One web search (mandatory before implementation)

- **Query (exact):** `TanStack Query removeQueries clear cache sign out session docs`
- **Date/time (local):** `2026-03-23 15:45 Asia/Almaty`
- **Sources opened (from this query):**
  - TanStack Query official docs, `QueryClient`: `https://tanstack.com/query/latest/docs/reference/QueryClient`
- Found ready-made solutions:
  - `queryClient.removeQueries(...)` removes specific stale query cache entries.
  - `queryClient.clear()` clears all connected caches.
- **Decision:** `reuse/integrate`
  - Reuse TanStack Query cache primitives instead of inventing local stale-state cleanup logic.
  - Use targeted cache eviction/reset in auth failure path and keep tenant scope intact unless access mismatch is explicit.
- **Rejected options:**
  - `build`: manual stale-state flags in local component state were rejected because React Query already owns `console-me`.
  - `clear-all-first`: unconditional `queryClient.clear()` as the only path was rejected as too broad for routine selection updates; targeted removal/reset around auth failure is safer.

## Root cause (mandatory)

- Symptom:
  - После логина под `admin/admin` console периодически показывает full-screen серый overlay с текстом `Выберите компанию`; в пользовательском браузере это выглядит как зависшая страница без кликов.
- Minimal reproduction:
  - Логин на `https://console.truffles.kz/` под `admin/admin`.
  - Дождаться refresh/session drift или открыть вкладку после session/token drift.
  - UI возвращается в selection gate; из-за full-screen blurred overlay пользователь видит серое заблокированное окно.
- Evidence:
  - Live `/api/proxy/me` под `admin/admin` возвращает `company_selection_required=true`, `selection_required=true`, `companies=3`.
  - `truffles-console-web` logs contain `Error refreshing access token { error: 'invalid_grant', error_description: 'Token is not active' }` on `2026-03-23 08:09:52 +05:00` and `2026-03-23 14:03:19 +05:00`.
  - `ConsoleShell` auth guard clears console context on auth failure: `console-web/src/components/ConsoleShell.tsx`.
  - Selection gate is a fixed full-screen blurred overlay: `console-web/src/components/ConsoleShell.tsx`.
- Five Whys:
  - Why does the gray screen appear? Because the global selection gate is rendered as a fixed full-screen overlay.
  - Why does the gate reappear after the user already worked in console? Because auth/session refresh failures clear the saved scope.
  - Why does scope clearing matter for `admin`? Because backend correctly re-enters `company_selection_required` when there are multiple accessible companies.
  - Why does this feel like a freeze instead of a recoverable prompt? Because the overlay blocks the whole UI and uses blur, so the page looks inert/stuck.
  - Why can the state remain confusing/stale? Because auth failure currently clears local scope instead of first evicting stale `console-me` cache and re-establishing a truthful shell state.
- Root cause statement:
  - The previous Feb-3 auth-refresh fix addressed expired sessions by clearing local tenant scope, but for multi-company users that reintroduces `company_selection_required`; combined with the later full-screen blurred overlay, the truthful scope prompt now manifests as a gray, apparently frozen screen.
- Fix mechanism:
  - Keep last valid scope across auth failure/sign-out redirect unless the backend explicitly says the tenant scope is invalid.
  - Evict/reset stale `console-me` query state on auth failure.
  - Replace the heavy full-screen blurred overlay with a lighter non-blur blocking surface so the selection prompt remains obviously interactive.

## Reuse-first plan (mandatory)

- Strategy: `reuse -> integrate -> configure -> build`
- Internal reuse:
  - Existing `clearConsoleContextScope`, `setConsole*Context`, `applyConsoleScopeContext`, `queryClient` primitives, existing Playwright auth helpers.
- External reuse:
  - TanStack Query `QueryClient.removeQueries` / `cancelQueries` semantics from the official docs inform the auth-failure cache eviction path.
- Why no new framework/library:
  - The failure is in current shell/session/cache orchestration, not a missing capability.

## Token / run budget (mandatory for expensive suites)

- Max full runs: `1`
- Planned expensive runs:
  - one local `npm run build`
  - one local Playwright smoke lane against the worktree server
  - one local auth-failure simulation script
- Stop condition:
  - Stop after one green local proof bundle; if any check fails twice without new evidence, return to RCA instead of adding more runs.

## Plan

1. Create one dedicated worktree/session from `origin/main` and keep all code/docs/test work inside it.
2. Refactor `ConsoleShell` auth failure path so auth errors clear stale query state instead of wiping valid tenant scope.
3. Narrow context reset semantics to explicit invalid-scope cases and keep explicit logout behavior unchanged.
4. Simplify selection-gate rendering to a lighter non-blurred surface and verify it still blocks background actions while remaining obviously interactive.
5. Add regression coverage for multi-company selection gate persistence/recovery.
6. Run targeted lint/build/e2e/live reproduction checks.
7. Record evidence in session log and `STATE.md`.

## DoD

- `admin/admin` multi-company login still sees truthful company selection, but the gate no longer regresses into a gray “frozen” state after auth/session drift.
- Auth failure path removes stale shell data without erasing last valid scope by default.
- Explicit logout still clears scope.
- At least one regression test covers the selection-gate stabilization path.
- Targeted checks pass and live reproduction confirms the behavior.

## Checks

- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && npm run lint -- --file src/components/ConsoleShell.tsx --file src/lib/console-context-storage.ts --file src/lib/console-scope-gate.ts --file src/components/LoginButton.tsx --file e2e/smoke.spec.ts`
- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && npm run build`
- `cd /home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1/console-web && npx playwright test e2e/smoke.spec.ts --project chromium --workers 1 --grep 'multi-company selection gate'`
- Live proof script against `https://console.truffles.kz/` with `admin/admin` documenting `/api/proxy/me`, scope persistence, and gate interactivity.

## Evidence

- Session log: `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-stabilization-a1.md`
- Code diff in touch-list files
- Command outputs for lint/build/Playwright/live proof
- Updated `STATE.md` entry before merge because this changes console behavior

## Release safety (mandatory for non-doc changes)

- Strategy: single console-web deploy, no backend schema changes.
- Go/no-go signals:
  - lint/build green
  - targeted Playwright regression green
  - live login under `admin/admin` proves gate can be completed and survives reload/new tab
  - no new auth/signout loops in container logs during validation
- Rollback:
  - revert the hotfix commit and redeploy `console-web`
- Post-release monitoring window:
  - first 24 hours after deploy, with focus on `RefreshAccessTokenError`, repeated `selection-gate-overlay` complaints, and any new tenant-mismatch regressions.

## Rollback

- Revert the worktree commit(s) touching the shell/gate behavior and redeploy `console-web`.

## No-go

- Do not weaken tenant isolation or silently keep an invalid company/client/branch after backend mismatch.
- Do not add another ad-hoc localStorage path outside existing scope helpers.
- Do not change Keycloak/OIDC server config in this block.
- Do not create more than one worktree for this task.

## Risks / blockers

- Live-only browser-specific “unclickable blur overlay” may be hard to reproduce headlessly; mitigation is to remove the blur-heavy presentation while keeping deterministic gate logic.
- Existing pages may rely on current sign-out side effect; targeted regression around explicit logout is required.

## Residual architecture debt (mandatory)

- Current residuals accepted in this block:
  - Console scope still uses localStorage as the runtime source of truth on the client.
  - Backend does not persist selected scope as part of server-owned session.
- Why not in this block:
  - Moving scope ownership server-side is a broader auth/session architecture change than this bounded hotfix.
- Risk if deferred:
  - Future auth/session drift can still create edge cases around stale local scope, even after this fix.
- Linked follow-up Task Package(s):
  - Follow-up TP required for server-owned console scope/session state.
- Expiry/trigger to stop deferral:
  - Any повторение auth/session-driven scope drift after this hotfix or any new requirement for cross-device scope persistence.

## Next-block contract (mandatory)

- Next block objective:
  - Design server-owned console scope persistence so `/me` reflects authoritative selected company/client/branch without relying on localStorage.
- First deterministic check command:
  - `cd /home/zhan/truffles-main && rg -n "selected_company_id|selected_branch_id|x-company-id|x-client-id|x-branch-id" truffles-api/app/services/console_auth.py console-web/src/components/ConsoleShell.tsx console-web/src/lib/api-client.ts`
- Blocked-by conditions:
  - This hotfix must be live-validated first and any tenant-mismatch regressions must be absent.
- Owner role for closure:
  - Top Architect / Brain

## Branch + Worktree + Base ref + Merge policy + Cleanup

- Branch: `feat/2026-03-23-console-selection-gate-stabilization-a1`
- Worktree: `/home/zhan/worktrees/2026-03-23-console-selection-gate-stabilization-a1`
- Base ref: `origin/main`
- Merge policy: merge-only after local proof and `STATE.md` update
- Cleanup: remove worktree/branch after merge
