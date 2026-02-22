# TP-2026-02-22-outreach-auto-case-a200

## Название/цель
Автоматически создавать и сопровождать операционный кейс для `no-case outreach` (когда менеджер отправляет сообщение без существующей заявки/чата), чтобы работа менеджера не терялась в «внеочередном» режиме и была полностью наблюдаемой в Inbox.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: outreach/human-lock wave завершена, GAP: операционный follow-up для no-case outreach)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/ESCALATION.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Human-lock safety не ослабевает: при активной паузе бот не отвечает.
- Branch isolation, RBAC и tenant boundaries сохраняются.
- Outbox idempotency не деградирует.
- Создание auto-case не дублирует кейсы и не ломает существующий case lifecycle.
- Все критические пути пишут `decision_meta/decision_trace` и доступны для диагностики.

## Scope
1. Определить контракт auto-case для `conversation_id=null` outreach.
2. Добавить backend flow: `outreach -> auto-case bootstrap -> inbox visibility`.
3. Добавить дедупликацию/идемпотентность, чтобы повторные отправки не плодили кейсы.
4. Добавить link-back в UI: менеджер видит созданный кейс сразу после отправки.
5. Добавить observability: trace/meta + аудит действий для расследования инцидентов.
6. Добавить runbook для incident triage (missing case, duplicate case, orphan outreach).

## Out of scope
- Массовые кампании (marketing).
- Полный redesign inbox или ролей.
- Изменение provider gateway архитектуры.
- Изменение продуктовых SLA вне outreach/case lifecycle.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/human_lock_service.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/*` (если нужен отдельный linking marker)
- `truffles-api/migrations/*` (если появляется новый persistence-атрибут)
- `truffles-api/tests/test_console_outreach.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_webhook_trace.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/smoke.spec.ts`

## Plan
1. Зафиксировать state machine auto-case: `no_case_sent -> case_created -> active|resolved`.
2. Добавить deterministic case creation hook в `send_outreach_message` при `conversation_id=null`.
3. Добавить dedupe key (`client_id + remote_jid + branch_id + time_bucket`) с безопасным upsert.
4. Привязать результат к Inbox list/detail (response возвращает `auto_case_id`/`conversation_id`).
5. Добавить trace/meta stages: `outreach_auto_case_bootstrap` + outcome reason.
6. Добавить unit tests (happy path, duplicate send, branch mismatch, fallback path).
7. Добавить e2e smoke (UI отправка no-case -> кейс появился в Inbox).
8. Обновить runbook по triage и rollback.

## DoD
- `POST /console/v1/outreach/messages` с `conversation_id=null` создаёт (или переиспользует) операционный кейс.
- Ответ API содержит идентификатор созданного/переиспользованного кейса.
- Менеджер сразу видит этот кейс в Inbox без ручного refresh-hack.
- Повторные одинаковые outreach не создают дубликаты кейсов.
- `decision_trace` и audit фиксируют путь auto-case bootstrap.
- RBAC/branch guard покрыты тестами.
- OpenAPI и frontend API типы синхронизированы.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/trace.py truffles-api/app/schemas/console.py`
- `pytest -q truffles-api/tests/test_console_outreach.py truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_webhook_trace.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint -- --file src/components/InboxView.tsx --file src/lib/api-client.ts`
- `npm --prefix console-web run test:e2e -- --grep "standalone outreach|auto-case" --project=chromium`

## Evidence
- PR link + CI link.
- `summary` по тестам и `git diff --stat`.
- Скрин/trace evidence: no-case outreach создал кейс и виден в Inbox.
- `decision_trace` snapshot с `outreach_auto_case_bootstrap`.

## Rollback
- Feature flag `OUTREACH_AUTO_CASE_ENABLED=0` (или revert commit) возвращает старое поведение no-case outreach без auto-case.
- DB rollback: удалить новые optional поля/индексы отдельной rollback migration.
- UI fallback: скрыть auto-case link badge, оставить обычную отправку.

## No-go
- Не добавлять магические хардкоды по branch/role.
- Не писать orchestration в `_legacy.py`.
- Не ломать текущий outreach/human-lock контракт.
- Не заменять contract tests на текстовые must_include оркестрации.

## Риски/блокеры
- Нужен строгий дедуп-контракт, иначе burst-сценарии дадут дубликаты кейсов.
- Нужна согласованность между outbox enqueue и case bootstrap при частичных сбоях.
- Для live диагностики нужен явный stage в trace, иначе инциденты будут трудно расследуемы.

## Branch / Worktree
- Branch: `feat/2026-02-20-outreach-human-lock-a200`
- Worktree: `/home/zhan/worktrees/2026-02-20-outreach-human-lock-a200`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после merge удалить worktree/branch по стандарту `session_end`
