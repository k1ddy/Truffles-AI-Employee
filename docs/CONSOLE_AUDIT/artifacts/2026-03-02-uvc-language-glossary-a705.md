# UVC Language Glossary (a705)

Date: `2026-03-02`
Scope: `Tenants`, `Integrations`, `Company Workspace`

## Purpose
Единый словарь для бизнес-формулировок в UVC, чтобы одинаковые действия и причины назывались одинаково во всех вкладках.

## Actions

| Internal code | UI label | Hint |
|---|---|---|
| `integration_reconcile` | `Сверка интеграции` | Проверка связки интеграции и состояния канала перед выполнением записи. |
| `provider_start_rebind` | `Старт перепривязки` | Начать перенос канала на корректную связку instance и webhook. |
| `provider_complete_rebind` | `Завершить перепривязку` | Подтвердить, что перепривязка завершена и канал снова стабилен. |
| `provider_renewal_confirmed` | `Подтвердить продление` | Обновить данные продления, чтобы отправка не остановилась из-за оплаты. |
| `provider_webhook_updated` | `Webhook обновлен` | Зафиксировать обновление webhook и проверить корректный прием событий. |
| `provider_send_reminder` | `Отправить напоминание` | Отправить напоминание ответственному, чтобы закрыть блокер по каналу. |

## Reasons

| Internal code | UI label |
|---|---|
| `provider_binding_rebind_required` | `нужна перепривязка канала` |
| `provider_binding_expired` | `подписка канала истекла` |
| `provider_binding_expiring_soon` | `подписка канала скоро истекает` |
| `provider_binding_alert_critical` | `критичный сигнал у канала` |
| `provider_binding_alert_warn` | `предупреждение у канала` |
| `no_recent_inbound` | `давно нет входящих сообщений` |
| `instance_id_mismatch` | `не совпадает instance_id канала` |
| `invalid_webhook_url` | `некорректный webhook URL` |
| `integration_degraded` | `интеграция нестабильна` |
| `outbox_backlog` | `очередь отправки растет` |
| `readiness_blocked` | `не закрыт чек-лист запуска` |

## Source of truth
- `console-web/src/lib/provider-ops-language.ts`
