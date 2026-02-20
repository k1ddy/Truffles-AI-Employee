# TP-2026-02-20-outreach-human-lock-a200

## Название/цель
Надёжный outreach из Console по номеру WhatsApp + индивидуальная пауза бота на 30 минут по клиенту. Реализовать единый outbox-first путь для ручных текстовых отправок, human-lock gate в webhook и UI-опции в Inbox (вкладка «Заявки»).

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: delivery/outbox reliability, console inbox ops)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/ESCALATION.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Бот не отвечает клиенту при активном human-lock или `manager_active`.
- Отправка ручных сообщений не теряется при временных сбоях провайдера (idempotent + retry через outbox).
- Branch/tenant isolation и RBAC не ослабевают.

## Scope
1. Backend: human-lock модель/сервис + gate в webhook routing.
2. Backend: outbox-first для текстовых сообщений из Console.
3. Backend: outreach API (send-by-phone/jid + pause 30m + unpause/status).
4. Backend/Policy: provider error hardening для invalid recipient (non-retryable).
5. Frontend: Inbox UI в «Заявки» для outreach и управления паузой бота.
6. RBAC: новая секция `outreach` с проверками в API/UI.
7. Контракты/типы: OpenAPI + generated client types.
8. Тесты: unit/contract tests на backend + минимальный frontend type/lint/build.

## Out of scope
- Полная массовая рассылка/кампании (остаются в marketing).
- Изменение provider layer/DEC-level архитектуры.
- Изменение SLA/policy продукта вне точек human-lock/outreach.

## Touch-list
- `truffles-api/app/models/*` (+ новый model)
- `truffles-api/migrations/*` (+ новая migration)
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/services/manager_message_service.py`
- `truffles-api/app/services/outbox_service.py`
- `truffles-api/app/services/provider_error_policy.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_rbac.py`
- `truffles-api/tests/test_console_outreach.py` (new)
- `truffles-api/tests/test_provider_error_policy.py` (update/new cases)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить human-lock persistence + сервисный слой (normalize jid/phone, upsert/release/status).
2. Встроить human-lock gate в webhook routing до mute/reengage логики.
3. Перевести console text send на outbox-first path (fallback direct only when worker disabled).
4. Добавить outreach endpoints в console router + pydantic schemas + audit/idempotency.
5. Расширить provider error policy (`invalid_recipient` non-retryable) и подключить в retry behavior.
6. Расширить RBAC (`outreach`) и UI capability checks.
7. Добавить UI controls в Inbox/CaseConversation: send-by-phone + pause/unpause/status.
8. Обновить OpenAPI/typed client, добавить и прогнать тесты/проверки.

## DoD
- Из Console можно отправить WhatsApp сообщение по телефону/JID через новый outreach endpoint.
- Для клиента можно включить `pause 30m`, продлить и снять паузу.
- При активном human-lock webhook возвращает `bot_response=None` и пишет trace/meta (`human_lock_silent`).
- Текстовые Console replies идут через outbox event при включённом worker.
- Ошибки invalid recipient классифицируются как non-retryable permanent failure.
- RBAC и branch access проверяются для outreach API.
- OpenAPI и frontend typed API синхронизированы.
- Тесты для нового поведения зелёные.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/guards.py truffles-api/app/services/provider_error_policy.py`
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_outreach.py truffles-api/tests/test_provider_error_policy.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint -- --file src/lib/api-client.ts --file src/components/CaseConversation.tsx --file src/components/InboxView.tsx`
- `npm --prefix console-web run build`

## Evidence
- git diff + test outputs выше.
- OpenAPI check output.
- Для webhook gate: unit evidence (`human_lock_silent` trace payload assertion).
- Для outbox-first: unit evidence enqueue payload (`event_type=whatsapp.send_text`).
- Session log + update в `STATE.md` (делает Brain/Top Architect до merge для поведенческих изменений).

## Rollback
- Отключение UI controls (feature toggle via permission check).
- Возврат текстовой отправки на прямой send path.
- Удаление/игнор human-lock gate (hotfix revert commit).
- SQL rollback: drop `human_locks` table/indexes (if needed via migration rollback script).

## No-go
- Не трогать `_legacy.py` оркестрацией.
- Не отключать pending/manager_active safety gates.
- Не менять policy/LAW контракты без отдельного решения.
- Не подгонять логику под тесты хардкодами.

## Риски/блокеры
- Консольные роли вне inbox-flow могут требовать отдельный UX вход.
- При выключенном outbox worker delivery mode зависит от fallback path.
- Неоплаченный тариф ChatFlow остаётся внешним блокером runtime delivery.

## Branch / Worktree
- Branch: `feat/2026-02-20-outreach-human-lock-a200`
- Worktree: `/home/zhan/worktrees/2026-02-20-outreach-human-lock-a200`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: после merge удалить worktree/branch по стандарту session_end
