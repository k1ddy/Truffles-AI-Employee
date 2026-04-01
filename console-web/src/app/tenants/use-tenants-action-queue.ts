"use client";

import { useCallback, useMemo } from "react";
import type { components } from "@/types/api.generated";
import type { TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";
import type { ProviderOpsAction } from "@/lib/api-client";
import {
    providerOpsActionHint,
    parseProviderOpsAction,
    providerOpsActionCodeLabel,
    providerOpsReasonLabels,
} from "@/lib/provider-ops-language";

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetAttentionLevel = "high" | "medium" | "low";

type ActionQueueIntent =
    | "set_context"
    | "open_cases"
    | "open_integrations"
    | "open_ops"
    | "open_workspace"
    | "open_workspace_execute"
    | "workspace_portfolio"
    | "workspace_onboarding"
    | "workspace_changes"
    | "workspace_decommission"
    | "none";

export type TenantsActionQueueWorkflowItem = TenantsActionQueueItem & {
    intent: ActionQueueIntent;
    branchId?: string | null;
    actionHref?: string | null;
    incidentId?: string | null;
    source?: "incident" | "provider_ops" | "readiness";
    providerAction?: ProviderOpsAction | null;
    mode?: "dry_run" | "execute" | null;
    reasons?: string[];
};

type UseTenantsActionQueueParams = {
    tenantLifecycle: TenantLifecycleMode;
    fleetAttention: components["schemas"]["ConsoleFleetAttentionResponse"] | null | undefined;
    controlTowerActionCenter:
        components["schemas"]["ConsoleAdminControlTowerActionCenterResponse"] | null | undefined;
    controlTowerMigrationProgram:
        components["schemas"]["ConsoleAdminControlTowerMigrationProgramResponse"] | null | undefined;
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

function resolveIntentByControlTowerItem(
    item: components["schemas"]["ConsoleAdminControlTowerActionItem"],
    providerAction: ProviderOpsAction | null,
): ActionQueueIntent {
    const href = (item.href ?? "").trim();
    if (item.kind === "provider_action" || providerAction) {
        return "open_workspace_execute";
    }
    if (href.startsWith("/company-workspace")) {
        return "open_workspace";
    }
    if (href.startsWith("/ops")) {
        return "open_ops";
    }
    if (href === "/" || href.startsWith("/?")) {
        return "open_cases";
    }
    if (href.startsWith("/integrations")) {
        return "open_integrations";
    }
    if (href.startsWith("/tenants") || item.source === "readiness") {
        return "workspace_onboarding";
    }
    if (item.source === "incident") {
        return "open_ops";
    }
    if (item.source === "provider_ops") {
        return "open_workspace";
    }
    return "set_context";
}

function resolveActionLabel(intent: ActionQueueIntent): string {
    if (intent === "open_cases") {
        return "Открыть заявки";
    }
    if (intent === "open_integrations") {
        return "Открыть Integrations";
    }
    if (intent === "open_ops") {
        return "Открыть Ops";
    }
    if (intent === "open_workspace" || intent === "open_workspace_execute") {
        return "Открыть Workspace";
    }
    if (intent === "workspace_onboarding") {
        return "Открыть Онбординг";
    }
    if (intent === "workspace_changes") {
        return "Открыть Изменения";
    }
    if (intent === "workspace_decommission") {
        return "Открыть Архив";
    }
    if (intent === "workspace_portfolio") {
        return "Открыть Портфель";
    }
    if (intent === "set_context") {
        return "Взять в контекст";
    }
    return "Открыть";
}

function mapPriority(priority: "p0" | "p1" | "p2"): FleetAttentionLevel {
    if (priority === "p0") {
        return "high";
    }
    if (priority === "p1") {
        return "medium";
    }
    return "low";
}

function priorityOrder(priority: FleetAttentionLevel): number {
    if (priority === "high") {
        return 0;
    }
    if (priority === "medium") {
        return 1;
    }
    return 2;
}

function toParamRecord(
    value: components["schemas"]["ConsoleAdminControlTowerActionItem"]["params"],
): Record<string, unknown> | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return null;
    }
    return value as Record<string, unknown>;
}

function readParamString(
    params: Record<string, unknown> | null,
    key: string,
): string | null {
    if (!params) {
        return null;
    }
    const value = params[key];
    if (typeof value !== "string") {
        return null;
    }
    const normalized = value.trim();
    return normalized.length > 0 ? normalized : null;
}

export function useTenantsActionQueue({
    tenantLifecycle,
    fleetAttention,
    controlTowerActionCenter,
    controlTowerMigrationProgram,
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
        const collected: TenantsActionQueueWorkflowItem[] = [];

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

        const controlTowerItems = controlTowerActionCenter?.items ?? [];
        for (const item of controlTowerItems) {
            const params = toParamRecord(item.params);
            const clientId = item.client_id ?? readParamString(params, "client_id");
            const branchId = item.branch_id ?? readParamString(params, "branch_id");
            const providerActionRaw =
                (typeof item.provider_action === "string" ? item.provider_action : null)
                ?? readParamString(params, "action");
            const providerAction = parseProviderOpsAction(providerActionRaw);
            const modeParam = readParamString(params, "mode");
            const intent = resolveIntentByControlTowerItem(item, providerAction);
            const reasonLabels = providerOpsReasonLabels(item.reasons, 3);
            const actionHint = providerAction ? providerOpsActionHint(providerAction) : null;
            collected.push({
                id: item.id,
                priority: mapPriority(item.priority),
                title: item.title,
                detail: reasonLabels.length
                    ? `${item.description}. Причины: ${reasonLabels.join(", ")}${actionHint ? `. Что делать: ${actionHint}` : ""}`
                    : `${item.description}${actionHint ? `. Что делать: ${actionHint}` : ""}`,
                intent,
                actionLabel: resolveActionLabel(intent),
                clientId: clientId ?? undefined,
                companyId: null,
                branchId: branchId ?? null,
                actionHref: item.href ?? null,
                incidentId: item.incident_id ?? null,
                source: item.source,
                providerAction,
                mode: modeParam === "dry_run" || modeParam === "execute" ? modeParam : null,
                reasons: item.reasons ?? [],
            });
        }

        const migrationSummary = controlTowerMigrationProgram?.summary;
        if (migrationSummary) {
            if (migrationSummary.waves_hold > 0) {
                collected.push({
                    id: "migration-wave-hold",
                    priority: migrationSummary.p0_actions > 0 ? "high" : "medium",
                    title: `План запуска на паузе: ${migrationSummary.waves_hold}`,
                    detail: `Блокировано филиалов: ${migrationSummary.blocked_branches}. Закройте p0/p1 блокеры перед следующим promotion.`,
                    intent: "workspace_onboarding",
                    actionLabel: "Проверить запуск",
                });
            } else if (migrationSummary.waves_go > 0) {
                collected.push({
                    id: "migration-wave-go",
                    priority: "low",
                    title: `План запуска готов: ${migrationSummary.waves_go} волн`,
                    detail: "Промоушен можно выполнять по регламенту после проверки evidence.",
                    intent: "workspace_onboarding",
                    actionLabel: "Открыть Онбординг",
                });
            }
        }

        if (collected.length > 0) {
            return collected
                .sort((left, right) => priorityOrder(left.priority) - priorityOrder(right.priority))
                .slice(0, 8);
        }

        const attentionItems = fleetAttention?.items ?? [];
        const attentionTop = attentionItems.slice(0, 4);
        for (const item of attentionTop) {
            const defaultIntent: ActionQueueIntent = item.pending_handovers > 0 ? "open_cases" : "open_integrations";
            const nextActionLabel = providerOpsActionCodeLabel(item.next_action);
            const reasonLabels = providerOpsReasonLabels(item.reasons, 2);
            collected.push({
                id: `attention-${item.client_id}`,
                priority: item.attention_level as FleetAttentionLevel,
                title: `${item.client_name ?? item.client_slug} · score ${item.attention_score}`,
                detail: `Следующее действие: ${nextActionLabel}. Причины: ${reasonLabels.join(", ") || "—"}`,
                intent: defaultIntent,
                actionLabel: resolveActionLabel(defaultIntent),
                clientId: item.client_id,
                companyId: item.company_id ?? null,
            });
        }

        const pendingHandoversTotal = fleetAttention?.summary?.pending_handovers_total ?? 0;
        if (pendingHandoversTotal > 0) {
            collected.push({
                id: "summary-pending-handovers",
                priority: pendingHandoversTotal > 10 ? "high" : "medium",
                title: `Ожидают передачи менеджеру: ${pendingHandoversTotal}`,
                detail: "Проверьте очередь HANDOFF и обработайте блокирующие кейсы.",
                intent: "workspace_portfolio",
                actionLabel: resolveActionLabel("workspace_portfolio"),
            });
        }

        if (operationalKpi.publishFailedChanges > 0) {
            collected.push({
                id: "summary-publish-failed",
                priority: operationalKpi.publishFailedChanges >= 3 ? "high" : "medium",
                title: `Ошибки публикации изменений: ${operationalKpi.publishFailedChanges}`,
                detail: "Нужен разбор причин перед следующим применением изменений.",
                intent: "workspace_changes",
                actionLabel: resolveActionLabel("workspace_changes"),
            });
        }

        if ((clientsSummary?.onboarding_clients ?? 0) > 0 && operationalKpi.goLiveReadinessPct < 80) {
            collected.push({
                id: "summary-go-live-readiness",
                priority: operationalKpi.goLiveReadinessPct < 60 ? "high" : "medium",
                title: `Готовность к запуску: ${operationalKpi.goLiveReadinessPct}%`,
                detail: "Есть филиалы без закрытых обязательных критериев запуска.",
                intent: "workspace_onboarding",
                actionLabel: resolveActionLabel("workspace_onboarding"),
            });
        }

        if ((clientsSummary?.archived_clients ?? 0) > 0 && operationalKpi.decommissionSharePct > 20) {
            collected.push({
                id: "summary-decommission-share",
                priority: "low",
                title: `Доля архивных: ${operationalKpi.decommissionSharePct}%`,
                detail: "Проверьте архив и восстановите клиентов, готовых вернуться в актив.",
                intent: "workspace_decommission",
                actionLabel: resolveActionLabel("workspace_decommission"),
            });
        }

        if (collected.length === 0) {
            collected.push({
                id: "queue-healthy",
                priority: "low",
                title: "Критичных задач нет",
                detail: "Можно продолжать плановый онбординг и контроль SLA.",
                intent: "workspace_onboarding",
                actionLabel: resolveActionLabel("workspace_onboarding"),
            });
        }

        return collected
            .sort((left, right) => priorityOrder(left.priority) - priorityOrder(right.priority))
            .slice(0, 8);
    }, [
        tenantLifecycle,
        controlTowerActionCenter?.items,
        controlTowerMigrationProgram?.summary,
        fleetAttention,
        operationalKpi,
        clientsSummary,
    ]);

    return {
        actionQueue,
        isClientArchived,
    };
}
