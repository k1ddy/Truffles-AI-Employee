# TP-2026-02-08 Console Proxy Methods for User Admin (a17)

## Название/цель
Убрать 405 в Console при user-management операциях (disable membership/user access), обеспечив корректный проксинг mutating HTTP-методов (`PATCH`/`PUT`/`DELETE`) в `console-web`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: PR-2/PR-2b merged; Team user-management enabled in UI)
- `STRUCTURE.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-02-08-membership-rbac-ui-pr2b-a17.md`

## Invariant
- Auth/session forwarding в proxy не ухудшается.
- Tenant headers (`X-Company-Id`, `X-Client-Id`, `X-Branch-Id`) корректно проксируются для всех mutating методов.
- Error envelope/traceability остаются единообразными (через существующий proxy error path).

## Scope
- `console-web` proxy route:
  - поддержать `PATCH`, `PUT`, `DELETE` для `/api/proxy/[...path]`;
  - сохранить существующие правила для JSON/multipart/idempotency headers;
  - минимизировать дублирование, чтобы не размножать баги по методам.
- Добавить проверку, воспроизводящую fixed behavior (метод больше не 405).

## Out of scope
- Изменения backend `/console/v1/admin/*` контрактов.
- Изменения RBAC-правил.
- Новый UX/валидации Team screen.

## Touch-list
- `console-web/src/app/api/proxy/[...path]/route.ts`
- `docs/TASK_PACKAGES/TP-2026-02-08-console-proxy-methods-user-admin-a17.md`
- `docs/SESSIONS/SESSION-2026-02-08-console-proxy-methods-user-admin-a17.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Рефактор proxy route в общий forward helper для mutating методов.
2. Добавить handlers `PATCH`, `PUT`, `DELETE` с теми же header/body правилами, что и `POST`.
3. Прогнать lint/build и ручной HTTP-check: до фикса `405`, после фикса не `405` (ожидаемо `401/4xx` от auth/upstream).
4. Подготовить PR с evidence.

## DoD
- `PATCH /api/proxy/...` больше не возвращает framework-level `405`.
- Team user-management операции, использующие `PATCH` через `adminApi`, проходят через proxy до backend.
- `console-web` lint/build зелёные.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && npm run build`
- `curl -si -X PATCH http://localhost:3000/api/proxy/admin/memberships/00000000-0000-0000-0000-000000000000` (ожидание: не `405`)
- `SESSION_AGENT=a17 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- вывод checks команд (lint/build/curl/session_check)
- PR URL

## Rollback
- Revert commit этого PR.

## No-go
- Не менять backend API/DB.
- Не ломать существующие `GET/POST` кейсы.
- Не ослаблять проверку session/auth в proxy.

## Риски/блокеры
- Риск: расхождение логики body/header между методами при ручном копипасте.
- Митигация: единый helper для mutating методов + единый путь обработки ошибок.

## Branch/Worktree
- Branch: `feat/2026-02-08-console-proxy-methods-user-admin-a17`
- Worktree: `/home/zhan/worktrees/2026-02-08-console-proxy-methods-user-admin-a17`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P2-14 (`PR Task Package gate`): соблюдается через TP + session artifacts.
- P0/P1 core pipeline fitness functions не затрагиваются (console-web proxy scope).
