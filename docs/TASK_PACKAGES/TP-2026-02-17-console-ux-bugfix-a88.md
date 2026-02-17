# TP-2026-02-17-console-ux-bugfix-a88

- Название/цель: устранить ключевые UX/UI боли в Console Plane (контекст, branch gating, бизнес-понятность инцидентов) и стабилизировать `console-contract-live` preflight.
- Canon refs: `STATE.md` (console UX + contract-live failures), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (`UX-26`, owner/admin simplification), `AGENTS.md`, `docs/CONSOLE_GUIDE.md`.

## Invariant
- Не ломать RBAC и текущие контракты `/console/v1/*`.
- Не ухудшить owner/admin и platform-admin smoke flow.
- Не ослаблять `console-contract-live`; только сделать preflight стабильнее.

## Scope
- Оптимизировать UX переключения контекста в shell и улучшить контекстные подсказки.
- Улучшить Knowledge branch gate и обработку gateway/selection ошибок.
- Сделать business incidents более понятными для owner/admin (типизация причин).
- Устранить флаки в CI шаге `Resolve console selection headers`.

## Out of scope
- Полный редизайн Console.
- Изменения backend бизнес-логики маршрутизации сообщений.
- Изменение политики CI-гейтов (skip/remove jobs).

## Touch-list
- `.github/workflows/ci.yml`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/app/business/page.tsx`

## Plan
1. Убрать блокирующий invalidate/refetch паттерн при смене контекста; оставить фоновое обновление.
2. Добавить ясную UX-обратную связь по выбранному контексту и доступным опциям.
3. Уточнить ошибки Knowledge (gateway, context-required) и branch empty-state.
4. Добавить owner/admin пояснения для provider incident reason codes.
5. Закрыть preflight edge-cases в `console-contract-live` header resolver.
6. Прогнать локальные `lint`, `tsc`, `build`, `smoke --list`.

## DoD
- Context switch в shell не блокирует UI на массовом refetch.
- Пользователь видит понятный applied-context notice и понятные gate-подсказки.
- Knowledge ошибки дают конкретное действие (контекст/ops), а не общий fail.
- Business incidents различают billing block vs provider outage/auth/rate-limit.
- `console-contract-live` умеет резолвить `X-Client-Id`/`X-Branch-Id` при пустом `/me.client`.
- Локальные проверки проходят.

## Checks
- `npm --prefix console-web run lint -- --file src/components/ConsoleShell.tsx --file src/app/knowledge/page.tsx --file src/app/business/page.tsx`
- `cd console-web && npx tsc --noEmit --incremental false`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`
- `./scripts/session_check.sh`

## Evidence
- `git diff --stat`
- Логи команд lint/tsc/build/smoke-list.
- Изменения в UI/CI файлах по touch-list.

## Rollback
- `git revert SHA_МERGE_КОММИТА_ЭТОГО_PR` для PR этого пакета.
- Проверить повторно `console-contract-live` preflight и console smoke list.

## No-go
- Не убирать `console-contract-live`.
- Не вносить несвязанные backend refactor.
- Не хардкодить tenant/client/branch id в UI.

## Риски/блокеры
- Возможны различия прав аккаунтов в CI токене для `/me` и `/admin/branches`.
- Возможны расхождения copy в e2e snapshot/asserts при дальнейших UX правках.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-17-console-ux-bugfix-a88`
- Worktree: `/tmp/truffles-main-console-ux`
- Base ref: `origin/main`
- Merge policy: PR -> main (no rebase)
- Cleanup: Brain/Top Architect после merge
