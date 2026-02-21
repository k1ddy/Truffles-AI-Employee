# TP-2026-02-21-inbox-pause-bot-a1

- Название/цель: аудит механизма «Заявки» (ручная отправка сообщений + пауза бота/human lock) в Console и связанных backend потоков, выявление багов/рисков, анализ ценности и предложений улучшений.
- Canon refs: `STATE.md` (NOW: outreach + human lock; GAP: trace отсутствует для locked inbound), `docs/SESSION_START_PROMPT.txt`, `STRATEGY/REQUIREMENTS.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: только чтение и анализ; никаких изменений runtime/БД/поведения.
- Scope: UI/UX потоки в Console «Заявки» (send message + pause/resume), API/trace/outbox/guards, контрактные поверхности.
- Out of scope: исправления, рефакторинг, миграции, любые live-check/outbound, любые записи в БД.
- Touch-list (read-only):
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/utils/labels.ts`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/services/human_lock_service.py`
  - `truffles-api/app/services/provider_error_policy.py`
  - `truffles-api/migrations/033_add_conversation_human_locks.sql`
  - `contracts/console_api/openapi.v1.yaml`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/REPORTS/2026-01-30-inbox-ux-v2.md`
  - `docs/REPORTS/2026-01-26-control-plane-inbox.png`
- Plan:
  1) Создать сессию и лог.
  2) Прочитать канон и релевантные отчёты/аудит.
  3) Разобрать UI-поток send/pause/resume в коде и контракте.
  4) Разобрать backend-поток (API → guards → trace → outbox).
  5) Составить список багов/рисков/пробелов в наблюдаемости.
  6) Проанализировать ценность и сформировать улучшения.
  7) Выпустить отчёт.
- DoD:
  - Отчёт `docs/REPORTS/2026-02-21-inbox-pause-bot-a1.md` с разделами: поток, UI наблюдения, тех наблюдения, баги/риски (с критичностью), ценность/экономика, улучшения, блокеры.
  - В ответе — краткая выжимка и ссылки на ключевые файлы.
- Checks: N/A (analysis-only).
- Evidence: отчёт + ссылки на inspected files; при необходимости фиксация GAP/рисков в отчёте.
- Rollback: не применимо.
- No-go: любые изменения runtime/БД/поведения/политик; любые live-outbound; любые модификации `_legacy.py`.
- Branch: `audit/2026-02-21-inbox-pause-bot-a1`
- Worktree: `worktrees/2026-02-21-inbox-pause-bot-a1`
- Base ref: `origin/main`
- Merge policy: doc-only fast-forward в `main`
- Cleanup: удалить worktree/branch после завершения.

