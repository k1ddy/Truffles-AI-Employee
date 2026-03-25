# UVC Stage 2 Language Glossary (a705)

Date: `2026-03-03`
Scope: `Tenants`, `Settings`, `Knowledge`, `Ops`, `Marketing`

## Purpose
Зафиксировать единый слой plain-language для primary user-facing панелей без изменения API-ключей и runtime контрактов.

## Language Contract

| Internal / legacy term | UI label (plain-language) | Hint / business meaning | Location |
|---|---|---|---|
| `execution-flow remediation/go-live` | `Канонический рабочий поток` | Исправления и допуск к запуску выполняются в `Company Workspace`. | `Tenants`, `Settings` |
| `Verify` | `Проверить связь` | Проверка доступности канала без бизнес-изменений. | `Settings`, `Ops` |
| `Send test` | `Отправить тест` | Контрольная отправка сообщения в выбранный канал. | `Settings`, `Ops` |
| `client` (scope label) | `компания` | Операция применяется на уровне компании. | `Settings` |
| `instance_id:` | `ID канала WhatsApp (instance_id):` | Показываем понятное назначение поля, сохраняя технический ключ в скобках. | `Settings` |
| `Branch Knowledge Readiness` | `Готовность знаний по филиалу` | Оперативная готовность знаний и часов работы филиала. | `Knowledge` |
| `go-live` | `Готовность к запуску` | Текущее состояние допуска к запуску. | `Knowledge` |
| `audit trail` | `журнал аудита` | Причина изменения обязательна для трассируемости. | `Knowledge` |
| `Fleet Knowledge Control` | `Управление знаниями по сети клиентов` | Единая точка выбора клиента/филиала для операторов платформы. | `Knowledge` |
| `risk/score/stale/outbox_failed_24h` | `уровень риска/оценка/устаревшие филиалы/ошибки отправки за 24ч` | Технические метрики раскрываются в бизнес-терминах. | `Knowledge` |
| `Critical / Warn / Info` | `Критичные / Предупреждения / Инфо` | Приоритеты инцидентов для оператора. | `Ops` |
| `Failed / Pending / Processing / All` | `С ошибкой / Ожидает / В обработке / Все` | Единая терминология очередей. | `Ops` |
| `Retry failed` | `Повторить ошибки` | Повтор только ошибочных отправок. | `Ops` |
| `Reminder Queue` | `Очередь напоминаний` | Панель статусов напоминаний по отправке. | `Ops` |
| `Console Jobs` | `Операционные задания` | Исполняемые задачи поддержки без смены продуктового контура. | `Ops` |
| `Dry-run` | `Проверка без записи` | Безопасная проверка действия перед выполнением. | `Ops` |
| `Execute` | `Выполнить` | Фактическое выполнение действия. | `Ops` |
| `Legacy: ready/executed` | `Готова к запуску / Запуск завершен (исторический статус)` | Статусы кампаний без технического жаргона. | `Marketing` |
| `Template gate / approved template` | `Шаблон не согласован` | Перед отправкой требуется подтвержденный шаблон. | `Marketing` |

## Guardrails
- API keys (`instance_id`, `outbox_failed_24h`, `incident_state`, etc.) остаются без изменений.
- Технические термины допустимы в debug/sensitive зонах, но не в primary CTA/labels.
- Execute-действия остаются в существующих вкладках; Stage 2 не добавляет новые top-level страницы.

## Source of truth
- `console-web/src/app/tenants/tenants-page-view.tsx`
- `console-web/src/app/settings/page.tsx`
- `console-web/src/app/knowledge/page.tsx`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/marketing/page.tsx`
