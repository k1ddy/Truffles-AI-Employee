# Task Package: Inbox UX v2 + макросы (персональные/командные)

Title/Goal
- Сделать Inbox “чат‑first” и понятным для менеджеров: шире чат, ясный контекст, RU‑лейблы.
- Добавить управляемые быстрые ответы (персональные и командные) с хранением в БД.

Invariant
- Не менять core‑пайплайн (decision/trace/outbox), только Console API/DB/UX.
- Жёсткая изоляция tenants (client/branch selection остаётся fail‑closed).
- Диагностика остаётся скрытой по умолчанию для операторов.

Scope
- Backend: новая сущность console_macros (CRUD), привязка к client/branch/agent.
- OpenAPI + типы console‑web.
- UI: чат шире, детали в drawer; RU‑копия; быстрые ответы рядом с вводом; управление макросами.

Out of scope
- Изменения в LLM/decision/core.
- Автогенерация макросов из паков/AI.
- Изменения других вкладок (Knowledge/Team/Settings) кроме точечной копии.

Touch-list
- truffles-api/migrations/017_add_console_macros.sql
- truffles-api/app/models/console_macro.py
- truffles-api/app/models/__init__.py
- truffles-api/app/schemas/console.py
- truffles-api/app/routers/console.py
- truffles-api/tests/test_console_inbox_macros.py
- contracts/console_api/openapi.v1.yaml
- console-web/src/lib/api-client.ts
- console-web/src/types/api.generated.ts (generated)
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseView.tsx
- console-web/src/components/CaseConversation.tsx
- console-web/src/components/CaseDetailsPanel.tsx
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/InboxMacros.tsx
- SPECS/CONTROL_PLANE.md
- docs/REPORTS/2026-01-30-inbox-ux-v2.md
- STRUCTURE.md
- STATE.md
- docs/SESSIONS/SESSION-2026-01-30-inbox-ux-v2-macros-a1.md
- docs/SESSION_INDEX.md

Plan
1) Backend: модель + миграция + API (list/create/update/disable) с RBAC и branch selection.
2) Контракт: OpenAPI + генерация типов для console‑web.
3) UI: чат‑first layout + drawer деталей; RU‑лейблы; макросы и управление.
4) Тесты: backend unit tests; UI lint; доказательства (скрин/логи).

DoD
- Чат занимает максимум ширины, детали открываются по кнопке.
- Быстрые ответы редактируются персонально и видны командные (RBAC).
- Английские лейблы в Inbox заменены на RU.
- Новые API и тесты проходят.

Checks
- pytest -q truffles-api/tests/test_console_inbox_macros.py
- npm --prefix console-web run lint
- (опционально) PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USERNAME=admin E2E_PASSWORD=admin npm --prefix console-web run test:e2e -- e2e/inspect_case.spec.ts

Evidence
- Вывод pytest + lint (сохранить в /tmp).
- Скрины Inbox/Case после изменений (путь в /tmp).
- Обновить STATE.md с ссылками на evidence.

Rollback
- git revert MERGE_COMMIT_SHA

No-go
- Любые изменения decision/core или смягчение selection‑gate.
- Удаление диагностики полностью.

Branch
- feat/2026-01-30-inbox-ux-v2-macros-a1

Worktree path
- /home/zhan/worktrees/2026-01-30-inbox-ux-v2-macros-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Возможен конфликт с существующим Inbox layout.
- Нужен консенсус по RBAC для командных макросов.
