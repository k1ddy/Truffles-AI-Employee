# TP-2026-02-21-inbox-human-lock-v2-a1

- Название/цель: Реализовать TЗ `SPECS/INBOX_HUMAN_LOCK.md` — стабильный manual messaging + human lock в «Заявках» (UX+API+trace+RBAC) без скрытых состояний.
- Canon refs: `SPECS/INBOX_HUMAN_LOCK.md`, `STATE.md` (NOW: human lock wave + GAP trace), `STRATEGY/REQUIREMENTS.md`, `SPECS/ESCALATION.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant:
  - Нельзя ломать trace/meta/outbox инварианты (P0/P1).
  - Никаких silent states без UI-индикатора.
  - Не ухудшать безопасность RBAC.
- Scope:
  - Backend: human_lock model+service, console endpoints, case list/detail payloads, trace/meta.
  - Frontend: CaseList badge+filter, CaseConversation header/status, outreach panel fixes, manual reply pause toggle.
  - Contracts: OpenAPI + generated types.
- Out of scope:
  - Холодный outreach без заявки (Campaigns).
  - Переписывание webhook pipeline.
- Touch-list:
  - `SPECS/INBOX_HUMAN_LOCK.md`
  - `STRUCTURE.md`
  - `STATE.md`
  - `truffles-api/migrations/034_human_lock_v2.sql` (new)
  - `truffles-api/app/models/conversation_human_lock.py`
  - `truffles-api/app/services/human_lock_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/components/ChatInterface.tsx`
  - `console-web/src/components/InboxView.tsx`
  - `console-web/src/components/CaseView.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/lib/inbox-workspace.ts`
  - `console-web/src/types/index.ts`
  - `truffles-api/tests/test_console_outreach.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_webhook_trace.py`
- Plan:
  1) Обновить модель+миграцию human_lock v2 (scope/индексы) и сервисы.
  2) Обновить console API: pause toggle, auto-release on return/resolve, lock status in case list/detail.
  3) Обновить trace/meta.
  4) Обновить фронтенд: отображение pause, фильтр, toggle паузы, исправить outreach minutes/disable pause.
  5) Обновить OpenAPI и generated types.
  6) Тесты и sanity-check.
- DoD:
  - UI показывает состояние паузы в списке и шапке заявки.
  - pause toggle влияет на отправку.
  - return/resolve снимают lock.
  - human_lock_silent записывается в trace/meta.
  - Все измененные контракты и типы синхронизированы.
- Checks (local):
  - `pytest -q truffles-api/tests/test_console_outreach.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_webhook_trace.py`
  - `python3 truffles-api/scripts/generate_openapi.py --check`
  - `npm --prefix console-web run lint -- --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/components/ChatInterface.tsx --file src/lib/api-client.ts`
  - `npm --prefix console-web run build`
- Evidence:
  - Логи тестов + diff + указание новых/измененных файлов.
  - При изменении поведения core — запись в `STATE.md` с evidence.
- Rollback:
  - Откат миграции `034_human_lock_v2.sql` и revert commit.
- No-go:
  - Любой lock без release.
  - Любой silent state в UI.
  - Любой direct DB edit ради evidence.
- Branch: `feat/2026-02-21-inbox-human-lock-v2-a1`
- Worktree: `/home/zhan/worktrees/2026-02-21-inbox-pause-bot-a1`
- Base ref: `origin/main`
- Merge policy: PR required (non-doc changes)
- Cleanup: после merge удалить ветку (Brain/Top Architect).

