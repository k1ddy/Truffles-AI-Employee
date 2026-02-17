import type { IncidentItem } from "@/lib/api-client";

export type ProviderReasonCode = Extract<
    IncidentItem["reason_code"],
    "provider_billing_blocked" | "provider_unavailable" | "provider_auth" | "provider_rate_limited"
>;

export type ProviderErrorContract = {
    reasonCode: ProviderReasonCode;
    shortLabel: string;
    businessImpact: string;
    operatorMeaning: string;
    runbook: [string, string, string];
    primaryActionHref: string;
};

const PROVIDER_ERROR_CONTRACTS: Record<ProviderReasonCode, ProviderErrorContract> = {
    provider_billing_blocked: {
        reasonCode: "provider_billing_blocked",
        shortLabel: "Оплата провайдера заблокирована",
        businessImpact: "Исходящие сообщения не отправятся, пока не подтверждена оплата/тариф у провайдера.",
        operatorMeaning: "Это не технический outage. Проблема в billing/renewal и требует финансового подтверждения.",
        runbook: [
            "Проверить оплату и статус тарифа в разделе Подписка.",
            "Проверить paid_until, next_renewal_at и webhook_status в Интеграциях.",
            "После оплаты выполнить dry-run outbox и убедиться, что failed не растет.",
        ],
        primaryActionHref: "/subscription",
    },
    provider_unavailable: {
        reasonCode: "provider_unavailable",
        shortLabel: "Провайдер временно недоступен",
        businessImpact: "Отправка деградирует из-за внешнего outage; требуется операционный контроль очереди.",
        operatorMeaning: "Это техническая недоступность внешнего сервиса, а не проблема тарифа.",
        runbook: [
            "Проверить health/инциденты провайдера и общий backlog outbox.",
            "Включить режим throttling или временную деградацию non-critical отправок.",
            "После восстановления повторно прогнать outbox_process в dry-run и execute.",
        ],
        primaryActionHref: "/ops",
    },
    provider_auth: {
        reasonCode: "provider_auth",
        shortLabel: "Ошибка авторизации провайдера",
        businessImpact: "Отправка блокируется из-за невалидных токенов, связки instance или webhook.",
        operatorMeaning: "Требуется проверка credentials и binding, иначе повторы не помогут.",
        runbook: [
            "Проверить ключи/токены и соответствие instance_id в Интеграциях.",
            "Проверить webhook endpoint и подписи.",
            "Запустить integration_reconcile в dry-run, затем execute при чистом результате.",
        ],
        primaryActionHref: "/integrations",
    },
    provider_rate_limited: {
        reasonCode: "provider_rate_limited",
        shortLabel: "Провайдер ограничил скорость",
        businessImpact: "Доставка замедляется и может расти очередь pending/failed.",
        operatorMeaning: "Это лимит скорости/объема. Нужны лимиты отправки и перераспределение нагрузки.",
        runbook: [
            "Проверить интенсивность отправки и рост outbox backlog.",
            "Снизить burst и распределить нагрузку по времени/филиалам.",
            "Согласовать лимиты с провайдером и пересчитать операционный budget.",
        ],
        primaryActionHref: "/ops",
    },
};

export function getProviderErrorContract(reasonCode: IncidentItem["reason_code"]): ProviderErrorContract | null {
    if (
        reasonCode !== "provider_billing_blocked"
        && reasonCode !== "provider_unavailable"
        && reasonCode !== "provider_auth"
        && reasonCode !== "provider_rate_limited"
    ) {
        return null;
    }
    return PROVIDER_ERROR_CONTRACTS[reasonCode];
}
