# Отчет: «Заявки» — ручная отправка + пауза бота (human lock)

Дата: 2026-02-21
Agent: a1
Тип: visual + technical audit (read-only)

## Что просмотрено (evidence)
UI:
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/index.ts`

API/логика:
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/services/human_lock_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/console_auth.py`

Контракты/DB:
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/migrations/033_add_conversation_human_locks.sql`

Тесты:
- `truffles-api/tests/test_console_outreach.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_webhook_trace.py`

## Визуальный (UX) анализ
### Как это выглядит пользователю
1) В шапке заявки есть кнопка `Связаться с клиентом`. Она открывает блок “Ручное сообщение клиенту (WhatsApp)”.
2) Внутри блока:
   - статус “Бот активен / Бот на паузе (N мин)”
   - поля: WhatsApp номер/JID, “Пауза (мин)”, текст сообщения
   - действия: “Отправить клиенту”, “Пауза бота”, “Снять паузу”.
3) Блок по умолчанию свернут; статус паузы не виден, пока блок не открыт.
4) В списке заявок нет индикатора “бот на паузе”.

### UX проблемы (визуальные/поведенческие)
1) Статус паузы спрятан внутри сворачиваемого блока.
   - Последствие: менеджер может не понять, почему бот молчит.
2) В UI смешаны две разные операции:
   - “Сообщение в чате заявки” (через основную форму отправки)
   - “Outreach” (отдельный канал отправки, с опциональной паузой)
   Разделения/объяснения нет → неверный выбор пути.
3) “Пауза (мин)” визуально относится сразу к двум действиям (“Отправить” и “Пауза”), но фактически работает только в одной кнопке.
4) Нет явного источника/причины паузы и кто поставил.
5) Ошибки валидации (неверный номер, превышение лимита минут, отсутствие интеграции) показываются общими тостами без причины.

## Технический анализ (end-to-end)
### Потоки и API
1) Отправка сообщения из чата заявки:
   - UI: `messagesApi.send()` → `POST /console/v1/conversations/{id}/messages`
   - Backend: `send_manager_message()`
   - Доставка: outbox или direct send
   - Побочный эффект: ставит `human_lock` на 30 минут (always) при успешной доставке.

2) Outreach (ручное сообщение по номеру/JID):
   - UI: `outreachApi.sendMessage()` → `POST /console/v1/outreach/messages`
   - Backend: `send_outreach_message()`
   - Доставка: outbox или direct send
   - Побочный эффект: ставит `human_lock` на `pause_bot_minutes` (если > 0).

3) Пауза / снятие:
   - `POST /console/v1/conversations/{id}/human-lock/pause`
   - `DELETE /console/v1/conversations/{id}/human-lock`

4) Webhook guard:
   - При inbound и state=BOT_ACTIVE, если есть активный `human_lock` → `decision_trace` с `routing:human_lock_silent`, бот не отвечает.

### Ключевые технические наблюдения
- `human_lock` хранится на уровне `client_id + remote_jid`, а не conversation → затрагивает все диалоги с этим номером.
- `return_case` и `manager_resolve` возвращают бота, но не снимают `human_lock`.
- В контракте outreach поддерживает `pause_bot_minutes = 0`, но UI это не позволяет.
- `send_manager_message` всегда ставит pause=30, UI не может отключить.
- `send_outreach_message` не связан с `case`-метриками (SLA/first_response_at), только запись `Message`.
- RBAC: `viewer`/`specialist` имеют `outreach:write` и могут писать клиентам и ставить паузу.
- Отсутствует статус паузы в API модели `Case`, поэтому невозможно показать “paused” на уровне списка без отдельного запроса.

## Баги и проблемы (severity)
### Critical
- Нет.

### High
1) UI игнорирует выбранные минуты при outreach-отправке.
   - Факт: `pause_bot_minutes` всегда 30 в `CaseConversation.tsx`.
   - Риск: неверное ожидание и фактическая пауза всегда 30.

2) Нельзя отправить outreach без паузы (хотя API поддерживает 0).
   - Факт: min=1 и `Number(...) || 30` в UI.
   - Риск: “опциональная пауза” фактически обязательна.

3) Возврат заявки боту не снимает `human_lock`.
   - Факт: `return_case` → `state_manager_return` не вызывает release.
   - Риск: бот молчит после “Вернуть боту”, SLA падает.

### Medium
4) `human_lock` глобален на client+remote_jid.
   - Риск: одна пауза может затронуть другие ветки/заявки того же клиента.

5) Outreach без conversation_id создает lock, который нельзя снять через UI.
   - Риск: “немой бот” без простого способа снять паузу.

6) Observability GAP по `human_lock_silent` в DB-trace.
   - Факт зафиксирован в `STATE.md`.
   - Риск: невозможно объяснить “почему бот молчал”.

7) Роли `viewer/specialist` могут выполнять outreach.
   - Риск: нарушение контроля доступа.

### Low
8) Ошибки валидации/интеграции скрыты общими тостами.
   - Риск: менеджер не понимает причину отказа.

## Анализ ценности
- Фича повышает скорость реагирования: менеджер пишет напрямую и может “заморозить” бота, устраняя конфликтные ответы.
- TTL lock защищает от вечного “молчания”.
- Механизм особенно ценен для ночных/сложных кейсов, где нужна ручная коммуникация.

## Профессиональные решения (уровень production)
### Быстрые фиксы (P0/P1)
1) Привязать `pause_bot_minutes` к UI и разрешить 0.
2) При “Вернуть боту” автоматически снимать `human_lock` или требовать подтверждения.
3) В UI показывать источник паузы (`source`), причину (`reason`), кто поставил (`locked_by_name`).
4) Показать “Бот на паузе” в списке заявок (badge/иконка + фильтр).

### Среднесрочные решения
5) Развести “Manual Reply” и “Outreach”.
   - Внутри заявки использовать только `send_manager_message`.
   - Outreach вынести в отдельный модуль/экран, с явной целью: cold lead, напоминания.

6) Добавить release по `remote_jid` или `lock_id`.
   - Решает кейс outreach без conversation_id.

7) Привести RBAC к минимальным привилегиям:
   - `outreach:write` только `manager/admin/owner`.

### Долгосрочное (best practice)
8) Ввести “Manual Handling Mode” как состояние диалога:
   - Явное состояние `manual_pause` или `manual_handling`, хранится на уровне conversation/handovers.
   - Inbound сообщения в этом состоянии всегда создают/обновляют кейс и уведомляют менеджера.
   - Возврат в bot-active снимает режим автоматически.

9) Обсервабилити и контроль:
   - Гарантировать сохранение `human_lock_silent` в decision_trace.
   - Отдельная метрика: active human locks, avg TTL, stale locks.

## Итог
Фича ценная, но текущая реализация имеет UX-конфуз и несколько high-рисков (игнор выбранных минут, неизбежная пауза, отсутствие auto-release). Эти проблемы создают “тихий отказ” бота и непредсказуемое поведение для менеджера.

