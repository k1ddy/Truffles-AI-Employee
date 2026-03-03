import type { ProviderOpsAction } from "@/lib/api-client";

const PROVIDER_OPS_ACTIONS: readonly ProviderOpsAction[] = [
    "integration_reconcile",
    "provider_start_rebind",
    "provider_complete_rebind",
    "provider_renewal_confirmed",
    "provider_webhook_updated",
    "provider_send_reminder",
];

const PROVIDER_OPS_REASON_LABELS: Record<string, string> = {
    provider_binding_rebind_required: "нужна перепривязка канала",
    provider_binding_expired: "подписка канала истекла",
    provider_binding_expiring_soon: "подписка канала скоро истекает",
    provider_binding_alert_critical: "критичный сигнал у канала",
    provider_binding_alert_warn: "предупреждение у канала",
    no_recent_inbound: "давно нет входящих сообщений",
    instance_id_mismatch: "не совпадает instance_id канала",
    invalid_webhook_url: "некорректный webhook URL",
    integration_degraded: "интеграция нестабильна",
    outbox_backlog: "очередь отправки растет",
    readiness_blocked: "не закрыт чек-лист запуска",
};

function normalizeCode(value: string): string {
    return value.replaceAll("_", " ");
}

export function parseProviderOpsAction(value?: string | null): ProviderOpsAction | null {
    if (!value) {
        return null;
    }
    const normalized = value.trim();
    if (!normalized) {
        return null;
    }
    if (!PROVIDER_OPS_ACTIONS.includes(normalized as ProviderOpsAction)) {
        return null;
    }
    return normalized as ProviderOpsAction;
}

export function providerOpsActionLabel(action: ProviderOpsAction): string {
    if (action === "provider_start_rebind") {
        return "Старт перепривязки";
    }
    if (action === "provider_complete_rebind") {
        return "Завершить перепривязку";
    }
    if (action === "provider_renewal_confirmed") {
        return "Подтвердить продление";
    }
    if (action === "provider_webhook_updated") {
        return "Webhook обновлен";
    }
    if (action === "provider_send_reminder") {
        return "Отправить напоминание";
    }
    return "Сверка интеграции";
}

export function providerOpsActionHint(action: ProviderOpsAction): string {
    if (action === "provider_start_rebind") {
        return "Начать перенос канала на корректную связку instance и webhook.";
    }
    if (action === "provider_complete_rebind") {
        return "Подтвердить, что перепривязка завершена и канал снова стабилен.";
    }
    if (action === "provider_renewal_confirmed") {
        return "Обновить данные продления, чтобы отправка не остановилась из-за оплаты.";
    }
    if (action === "provider_webhook_updated") {
        return "Зафиксировать обновление webhook и проверить корректный прием событий.";
    }
    if (action === "provider_send_reminder") {
        return "Отправить напоминание ответственному, чтобы закрыть блокер по каналу.";
    }
    return "Проверить связку интеграции и состояние канала перед выполнением записи.";
}

export function providerOpsActionCodeLabel(actionCode?: string | null): string {
    if (!actionCode) {
        return "Нет действия";
    }
    const parsed = parseProviderOpsAction(actionCode);
    if (parsed) {
        return providerOpsActionLabel(parsed);
    }
    return normalizeCode(actionCode);
}

export function providerOpsReasonLabel(reason?: string | null): string {
    if (!reason) {
        return "не указано";
    }
    return PROVIDER_OPS_REASON_LABELS[reason] ?? normalizeCode(reason);
}

export function providerOpsReasonLabels(
    reasons: string[] | null | undefined,
    limit = 3,
): string[] {
    if (!reasons?.length) {
        return [];
    }
    return reasons.slice(0, limit).map((reason) => providerOpsReasonLabel(reason));
}
