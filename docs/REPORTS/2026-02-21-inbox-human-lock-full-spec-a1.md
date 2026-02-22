# ТЗ: «Заявки» — Manual Messaging + Human Lock (production-grade)

Дата: 2026-02-21
Agent: a1
Статус: Draft for implementation

## 1) Цели и критерии успеха
Цель: сделать механизм ручных сообщений и паузы бота в «Заявках» предсказуемым, управляемым и наблюдаемым, без скрытых состояний и UX‑ловушек.

Критерии успеха (SLO):
- 95%+ кейсов: оператор понимает, почему бот молчит, и может снять паузу в 1 действие.
- 0 случаев: бот остается «немым» после явного «Вернуть боту».
- 0 случаев: выбранные минуты паузы игнорируются.
- 100% inbound сообщений при активной паузе фиксируются в decision_trace + decision_meta.
- Нет кросс‑конфликтов между разными заявками одного клиента.

## 2) Термины
- Manual Reply: сообщение менеджера внутри активной заявки.
- Outreach: ручное сообщение клиенту вне контекста заявки (cold outreach).
- Human Lock: блокировка ответов бота на заданный TTL, управляемая менеджером.

## 3) UX требования (visual)
### 3.1 В шапке заявки
- Явный индикатор: `Бот на паузе: 12 мин` или `Бот активен`.
- Под индикатором: `Кто поставил`, `Причина`, `Источник`.

### 3.2 В списке заявок
- Badge/иконка `Paused` рядом с SLA, фильтр “На паузе”.

### 3.3 В блоке управления
- Тумблер: `Ставить паузу после отправки`.
- Поле длительности активируется только при включенном тумблере.
- Предустановки: `15`, `30`, `60`, `120` минут.
- CTA: `Снять паузу` всегда доступен при активной паузе.
- Отдельная зона для Outreach, с пояснением, что это отдельный сценарий.

### 3.4 UX ошибки
- Ошибки валидации должны показывать конкретную причину (номер недоступен, интеграция не настроена, лимит минут).

## 4) Функциональные требования
### 4.1 Manual Reply
- По умолчанию `pause_enabled = true` и `pause_minutes = 30`.
- Если `pause_enabled = false` или `pause_minutes = 0`, пауза не ставится.

### 4.2 Outreach
- Если нет `conversation_id`, система создает новую conversation + case (`manual_outreach`).
- Возвращается `conversation_id` и `case_id` для управления и UI.

### 4.3 Human Lock
- Lock привязан к `conversation_id` (primary).
- `return_case` и `resolve` автоматически снимают lock.
- Lock не ставится, если сообщение не доставлено/не поставлено в очередь.

### 4.4 Inbound handling
- Если lock активен, inbound:
  - сохраняется;
  - в trace записывается `routing:human_lock_silent`;
  - bot_response=null.

## 5) Data Model
### 5.1 conversation_human_locks (update)
Добавить:
- `lock_scope` ENUM(`conversation`,`remote_jid`) default `conversation`.
- `locked_by_id`, `locked_by_name` уже есть — обязать заполнение для всех lock через UI.

Индексы:
- Unique `(client_id, conversation_id)` WHERE `conversation_id IS NOT NULL`.
- (опционально) Unique `(client_id, remote_jid)` WHERE `lock_scope='remote_jid'`.

### 5.2 Case API
Добавить в `ConsoleCase`:
- `human_lock_active: bool`
- `human_lock_until: datetime|null`
- `human_lock_remaining_seconds: int|null`
- `human_lock_source: string|null`
- `human_lock_reason: string|null`
- `human_lock_by: string|null`

## 6) API изменения
### 6.1 Send manager message
Расширить `ConsoleManagerMessageRequest`:
- `pause_enabled?: boolean = true`
- `pause_minutes?: int = 30`
- `pause_reason?: string`

### 6.2 Outreach
`POST /console/v1/outreach/messages`
- если conversation_id отсутствует → создать conversation + case
- возвращать `case_id`, `conversation_id`

### 6.3 Human lock API
- `POST /conversations/{id}/human-lock` → установить/обновить
- `DELETE /conversations/{id}/human-lock` → release

## 7) Backend логика
- `get_active_human_lock` принимает `conversation_id`, проверяет conversation‑lock; fallback по remote_jid только если conversation_id нет.
- `send_manager_message` ставит lock только при `pause_enabled && pause_minutes > 0`.
- `return_case`/`resolve` → `release_human_lock`.

## 8) Observability
- `decision_trace` включает:
  - `stage: routing`, `decision: human_lock_silent`, `lock_id`, `lock_until`, `source`.
- `decision_meta.human_lock`:
  - `active`, `until`, `source`, `reason`, `locked_by`.
- Метрика: active locks count, blocked inbound count.

## 9) RBAC
- `outreach:write` → только `manager`, `admin`, `owner`, `platform_admin`.
- `human-lock` endpoints доступны тем же ролям.

## 10) Тесты
- Unit: `get_active_human_lock` (conversation‑first), auto‑release on return.
- Integration: send_manager_message with pause toggle, outreach without conversation.
- UI: E2E — pause badge, release, return-to-bot clears pause.
- Trace: human_lock_silent сохраняется в DB‑trace.

## 11) Rollout
- Feature flag `HUMAN_LOCK_V2_ENABLED`.
- Backfill existing locks: assign conversation_id where possible.
- Rollout: staging → limited tenants → full.

## 12) No-go
- Любые silent states без UI индикатора.
- Любые lock на remote_jid без возможности release.
- Любые auto‑pause без объяснения и управления.

