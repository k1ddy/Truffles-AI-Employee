# TP-2026-02-16-console-nav-click-hotfix-a88

- Название/цель: P0 hotfix для Console navigation. В роли Platform Admin и Owner/Admin клики по sidebar tabs не переводят на нужную страницу (`/business`, `/settings`, `/subscription`). Цель: восстановить гарантированную навигацию по вкладкам без изменения RBAC/данных.
- Canon refs: `STATE.md` NOW (owner/admin UX critical), `AGENTS.md` §6 Stop-the-line, `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_AUDIT/pages/subscription.md`.

## Invariant
- Не менять RBAC/правила `canAccessConsole`.
- Не менять API контракты и данные страниц.
- Исправить только механизм перехода по вкладкам.

## Scope
- `console-web/src/components/ConsoleShell.tsx`:
  - убрать зависимость nav-tabs от внутреннего client-router поведения,
  - сделать deterministic браузерный переход (`window.location.assign`) по desktop/mobile nav,
  - сохранить семантику обычных модифицированных кликов (Ctrl/Meta/Alt/Shift).

## Out of scope
- Переписывание глобального роутинга приложения.
- Изменение контента страниц `business/settings/subscription`.
- Изменения backend и billing logic.

## Touch-list
- `console-web/src/components/ConsoleShell.tsx`
- `docs/TASK_PACKAGES/TP-2026-02-16-console-nav-click-hotfix-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-console-nav-click-hotfix-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Воспроизвести инцидент локально/через e2e и подтвердить, что клики не меняют URL.
2. Внести минимальный hotfix в sidebar/mobile nav.
3. Проверить lint/build и выполнить runtime-проверку клика на локальном https runtime.
4. Подготовить PR с evidence.

## DoD
- Клик `nav-business` переводит на `/business`.
- Клик `nav-settings` переводит на `/settings`.
- Клик `nav-subscription` переводит на `/subscription`.
- Lint зелёный, diff ограничен nav hotfix.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- Runtime check script (Playwright): `nav-business` -> `/business`, `nav-settings` -> `/settings` на локальном `https://localhost:3300`.

## Evidence
- Playwright failure (до фикса): `owner-admin-business.spec.ts` — URL остаётся `/`.
- Runtime check после фикса: URL меняется `/ -> /business -> /settings`.
- `git diff` ограничен `ConsoleShell` + session docs.

## Rollback
- Revert hotfix commit (`ConsoleShell` navigation handler) и вернуть предыдущий nav behavior.

## No-go
- Не трогать бизнес-логику подписки/биллинга.
- Не добавлять временные хардкоды ролей.
- Не менять backend/DB для UI hotfix.

## Risks/блокеры
- Full navigation может быть медленнее client-router на 1 клик, но снимает P0 блокер переходов.
- Нужна пост-мердж проверка на проде для всех ролей.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `fix/2026-02-16-console-nav-click-hotfix-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-console-nav-click-hotfix-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks
- Cleanup: Brain/Top Architect после merge
