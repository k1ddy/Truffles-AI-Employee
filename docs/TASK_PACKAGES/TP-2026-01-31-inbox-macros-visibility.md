# Task Package: Inbox macros visibility + refresh fix

Title/Goal
- Исправить видимость кнопок добавления макросов в Inbox на 1920x1080/100%.
- Обеспечить появление нового макроса в списке сразу после создания.

Canon refs
- `STATE.md` (NOW: Inbox UX v3 fixes; добавить GAP по этой проблеме в ходе сессии)
- `SPECS/CONTROL_PLANE.md`

Invariant
- Без изменений backend/DB/контрактов; только Console UI/стейт.
- Выбор клиента/филиала остаётся fail-closed.
- Респонсивность Inbox не деградирует на меньших ширинах.

Scope
- UI layout/scroll для блока быстрых ответов и кнопок добавления.
- Обновление списка макросов после успешного create.

Out of scope
- Любые изменения в `truffles-api` или миграции.
- Новые фичи макросов (RBAC, автогенерация, теги, фильтры).
- Изменения других разделов Console.

Touch-list
- console-web/src/components/InboxMacros.tsx
- console-web/src/components/InboxView.tsx
- console-web/src/components/CaseConversation.tsx
- console-web/src/app/globals.css (если понадобится)
- STATE.md
- docs/SESSIONS/SESSION-2026-01-31-inbox-macros-visibility-a1.md
- docs/SESSION_INDEX.md

Plan
1) Проверить текущий prod build (commit/time) и воспроизвести проблему.
2) Если воспроизведение подтверждено — обновить `STATE.md` как GAP.
3) Исправить layout/overflow блока макросов, чтобы кнопки всегда видимы.
4) Исправить refresh списка после create (invalidate/refetch/optimistic update), если нужно.
5) Проверить lint + собрать evidence (скрин/логи), обновить `STATE.md`.

DoD
- Кнопки добавления видимы на 1920x1080/100% без зума.
- Новый макрос появляется в списке без ручной перезагрузки.
- Поведение на меньших ширинах не ломается.

Checks
- npm --prefix console-web run lint

Evidence
- Лог lint в `/tmp/console_web_lint_inbox_macros_visibility_20260131.txt`.
- Скрин Inbox 1920x1080 с видимыми кнопками и добавленным макросом.
- Запись в `STATE.md` с ссылками на evidence (Brain/Top Architect).

Rollback
- git revert COMMIT_SHA

No-go
- Любые изменения decision/core и backend API.
- Скрытые CSS-хак фиксы без объяснимого поведения.

Branch
- feat/2026-01-31-inbox-macros-visibility-a1

Worktree path
- /home/zhan/worktrees/2026-01-31-inbox-macros-visibility-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- Возможен конфликт с текущей версткой Inbox v3.
- Нужно аккуратно не сломать sticky/scroll области чата.
