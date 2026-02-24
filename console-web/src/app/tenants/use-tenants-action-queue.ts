"use client";

import { useCallback, useMemo } from "react";
import type { components } from "@/types/api.generated";
import type { TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetAttentionLevel = "high" | "medium" | "low";

type ActionQueueIntent =
    | "set_context"
    | "open_cases"
    | "open_integrations"
    | "workspace_portfolio"
    | "workspace_onboarding"
    | "workspace_changes"
    | "workspace_decommission"
    | "none";

export type TenantsActionQueueWorkflowItem = TenantsActionQueueItem & {
    intent: ActionQueueIntent;
};

type UseTenantsActionQueueParams = {
    tenantLifecycle: TenantLifecycleMode;
    fleetAttention: components["schemas"]["ConsoleFleetAttentionResponse"] | null | undefined;
    operationalKpi: {
        publishFailedChanges: number;
        goLiveReadinessPct: number;
        decommissionSharePct: number;
    };
    clientsSummary: {
        onboarding_clients?: number;
        archived_clients?: number;
    } | null | undefined;
};

export function useTenantsActionQueue({
    tenantLifecycle,
    fleetAttention,
    operationalKpi,
    clientsSummary,
}: UseTenantsActionQueueParams) {
    const isClientArchived = useCallback((client: components["schemas"]["ConsoleClient"]) => {
        const lifecycleValue = (client.lifecycle_state ?? "").trim().toLowerCase();
        if (lifecycleValue) {
            return lifecycleValue === "archived";
        }
        return (client.status ?? "").trim().toLowerCase() !== "active";
    }, []);

    const actionQueue = useMemo<TenantsActionQueueWorkflowItem[]>(() => {
        if (tenantLifecycle !== "active") {
            return [
                {
                    id: "lifecycle-mode-tip",
                    priority: "low",
                    title: "Фокус на архиве",
                    detail: "Для операционной очереди переключите режим списка на «Активные».",
                    intent: "workspace_portfolio",
                    actionLabel: "Открыть портфель",
                },
            ];
        }

        const items: TenantsActionQueueWorkflowItem[] = [];
        const attentionItems = fleetAttention?.items ?? [];
        const attentionTop = attentionItems.slice(0, 4);

        attentionTop.forEach((item) => {
            const defaultIntent: ActionQueueIntent = item.pending_handovers > 0 ? "open_cases" : "open_integrations";
            const defaultActionLabel = item.pending_handovers > 0 ? "Открыть заявки" : "Открыть интеграции";
            items.push({
                id: `attention-${item.client_id}`,
                priority: item.attention_level as FleetAttentionLevel,
                title: `${item.client_name ?? item.client_slug} · score ${item.attention_score}`,
                detail: `Следующее действие: ${item.next_action}. Причины: ${item.reasons?.slice(0, 2).join(", ") || "—"}`,
                intent: defaultIntent,
                actionLabel: defaultActionLabel,
                clientId: item.client_id,
                companyId: item.company_id ?? null,
            });
        });

        const pendingHandoversTotal = fleetAttention?.summary?.pending_handovers_total ?? 0;
        if (pendingHandoversTotal > 0) {
            items.push({
                id: "summary-pending-handovers",
                priority: pendingHandoversTotal > 10 ? "high" : "medium",
                title: `Ожидают передачи менеджеру: ${pendingHandoversTotal}`,
                detail: "Проверьте очередь HANDOFF и обработайте блокирующие кейсы.",
                intent: "workspace_portfolio",
                actionLabel: "Открыть риск-панель",
            });
        }

        if (operationalKpi.publishFailedChanges > 0) {
            items.push({
                id: "summary-publish-failed",
                priority: operationalKpi.publishFailedChanges >= 3 ? "high" : "medium",
                title: `Ошибки публикации изменений: ${operationalKpi.publishFailedChanges}`,
                detail: "Нужен разбор причин перед следующими publish/rollback.",
                intent: "workspace_changes",
                actionLabel: "Открыть Change Management",
            });
        }

        if ((clientsSummary?.onboarding_clients ?? 0) > 0 && operationalKpi.goLiveReadinessPct < 80) {
            items.push({
                id: "summary-go-live-readiness",
                priority: operationalKpi.goLiveReadinessPct < 60 ? "high" : "medium",
                title: `Go-Live readiness: ${operationalKpi.goLiveReadinessPct}%`,
                detail: "Есть филиалы в онбординге без закрытых обязательных критериев.",
                intent: "workspace_onboarding",
                actionLabel: "Открыть Onboarding",
            });
        }

        if ((clientsSummary?.archived_clients ?? 0) > 0 && operationalKpi.decommissionSharePct > 20) {
            items.push({
                id: "summary-decommission-share",
                priority: "low",
                title: `Доля decommission: ${operationalKpi.decommissionSharePct}%`,
                detail: "Проверьте архивные клиенты и восстановите тех, кто готов вернуться в актив.",
                intent: "workspace_decommission",
                actionLabel: "Открыть Decommission",
            });
        }

        if (items.length === 0) {
            items.push({
                id: "queue-healthy",
                priority: "low",
                title: "Операционная очередь пуста",
                detail: "Критичных/важных блокеров не найдено. Можно продолжать плановый онбординг.",
                intent: "workspace_onboarding",
                actionLabel: "Открыть Onboarding",
            });
        }

        const priorityOrder: Record<FleetAttentionLevel, number> = { high: 0, medium: 1, low: 2 };
        return items
            .sort((left, right) => priorityOrder[left.priority] - priorityOrder[right.priority])
            .slice(0, 8);
    }, [tenantLifecycle, fleetAttention, operationalKpi, clientsSummary]);

    return {
        actionQueue,
        isClientArchived,
    };
}
