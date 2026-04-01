"use client";

import { useMemo } from "react";
import type { components } from "@/types/api.generated";
import type { TenantsOperationalSnapshotPayload } from "@/lib/api-client";
import {
    asPercent,
    buildOperationalKpiDrilldown,
    type OperationalKpiDrilldown,
    type OperationalKpiId,
} from "./operational-kpi";

type TenantLifecycleMode = "active" | "archived" | "all";
type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";

type UseTenantsOperationalModelParams = {
    clientsSummary:
        | {
            total_clients?: number;
            active_clients?: number;
            onboarding_clients?: number;
            go_live_ready_clients?: number;
            archived_clients?: number;
            degraded_clients?: number;
            onboarding_throughput?: unknown;
        }
        | null
        | undefined;
    fleetAttention: components["schemas"]["ConsoleFleetAttentionResponse"] | null | undefined;
    recentBranchChangesForKpi: components["schemas"]["ConsoleBranchChangeRecord"][];
    effectiveWorkspaceMode: TenantsWorkspaceMode;
    tenantLifecycle: TenantLifecycleMode;
};

export function useTenantsOperationalModel({
    clientsSummary,
    fleetAttention,
    recentBranchChangesForKpi,
    effectiveWorkspaceMode,
    tenantLifecycle,
}: UseTenantsOperationalModelParams) {
    const onboardingThroughput = useMemo(
        () => clientsSummary?.onboarding_throughput ?? null,
        [clientsSummary],
    );

    const operationalKpi = useMemo(() => {
        const summary = clientsSummary;
        const attentionSummary = fleetAttention?.summary;
        const totalClients = summary?.total_clients ?? 0;
        const activeClients = summary?.active_clients ?? 0;
        const onboardingClients = summary?.onboarding_clients ?? 0;
        const goLiveReadyClients = summary?.go_live_ready_clients ?? 0;
        const archivedClients = summary?.archived_clients ?? 0;
        const degradedClients = summary?.degraded_clients ?? 0;

        const totalChanges = recentBranchChangesForKpi.length;
        const publishedChanges = recentBranchChangesForKpi.filter((item) => item.status === "published").length;
        const publishFailedChanges = recentBranchChangesForKpi.filter((item) => item.status === "publish_failed").length;
        const rolledBackChanges = recentBranchChangesForKpi.filter((item) => item.status === "rolled_back").length;

        return {
            onboardingCoveragePct: asPercent(onboardingClients + goLiveReadyClients, totalClients),
            goLiveReadinessPct: asPercent(goLiveReadyClients, onboardingClients + goLiveReadyClients),
            serviceStabilityPct: asPercent(Math.max(activeClients - degradedClients, 0), activeClients),
            decommissionSharePct: asPercent(archivedClients, totalClients),
            changeFailurePct: asPercent(publishFailedChanges, totalChanges),
            rollbackSharePct: asPercent(rolledBackChanges, publishedChanges + rolledBackChanges),
            blockedSignalsCount:
                (attentionSummary?.outbox_failed_24h_total ?? 0)
                + (attentionSummary?.pending_handovers_total ?? 0)
                + publishFailedChanges,
            sourceWindow: totalChanges,
            publishedChanges,
            publishFailedChanges,
            rolledBackChanges,
        };
    }, [clientsSummary, fleetAttention, recentBranchChangesForKpi]);

    const operationalKpiValues = useMemo<Record<OperationalKpiId, number>>(() => ({
        onboardingCoverage: operationalKpi.onboardingCoveragePct,
        goLiveReadiness: operationalKpi.goLiveReadinessPct,
        serviceStability: operationalKpi.serviceStabilityPct,
        decommissionShare: operationalKpi.decommissionSharePct,
        changeFailure: operationalKpi.changeFailurePct,
        rollbackShare: operationalKpi.rollbackSharePct,
        blockedSignals: operationalKpi.blockedSignalsCount,
    }), [operationalKpi]);

    const operationalKpiDrilldown = useMemo<OperationalKpiDrilldown[]>(
        () => buildOperationalKpiDrilldown(operationalKpiValues),
        [operationalKpiValues],
    );

    const operationalKpiById = useMemo(() => {
        const map = new Map<OperationalKpiId, OperationalKpiDrilldown>();
        for (const item of operationalKpiDrilldown) {
            map.set(item.id, item);
        }
        return map;
    }, [operationalKpiDrilldown]);

    const criticalKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "critical").length,
        [operationalKpiDrilldown],
    );
    const warnKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "warn").length,
        [operationalKpiDrilldown],
    );

    const alertHookPayload = useMemo(() => {
        const breaches = operationalKpiDrilldown
            .filter((item) => item.status !== "ok")
            .map((item) => ({
                metric: item.id,
                label: item.label,
                status: item.status,
                value: item.value,
                reason: item.reason,
                action: item.action,
            }));
        const severity = breaches.some((item) => item.status === "critical")
            ? "critical"
            : breaches.length > 0
                ? "warning"
                : "ok";
        return {
            generated_at: new Date().toISOString(),
            severity,
            source_window: operationalKpi.sourceWindow,
            breaches,
            attention_summary: {
                active_clients_total: fleetAttention?.summary?.active_clients_total ?? 0,
                high_risk_clients: fleetAttention?.summary?.high_risk_clients ?? 0,
                medium_risk_clients: fleetAttention?.summary?.medium_risk_clients ?? 0,
                outbox_failed_24h_total: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
                pending_handovers_total: fleetAttention?.summary?.pending_handovers_total ?? 0,
            },
        };
    }, [operationalKpiDrilldown, operationalKpi.sourceWindow, fleetAttention?.summary]);

    const operationalReport = useMemo<TenantsOperationalSnapshotPayload>(() => ({
        generatedAt: new Date().toISOString(),
        sourceWindow: operationalKpi.sourceWindow,
        workspaceMode: effectiveWorkspaceMode,
        lifecycleMode: tenantLifecycle,
        kpi: operationalKpiValues,
        drilldown: operationalKpiDrilldown.map((item) => ({
            id: item.id,
            status: item.status,
            value: item.value,
            reason: item.reason,
        })),
        attentionSummary: {
            activeClientsTotal: fleetAttention?.summary?.active_clients_total ?? 0,
            highRiskClients: fleetAttention?.summary?.high_risk_clients ?? 0,
            mediumRiskClients: fleetAttention?.summary?.medium_risk_clients ?? 0,
            outboxFailed24hTotal: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
            pendingHandoversTotal: fleetAttention?.summary?.pending_handovers_total ?? 0,
        },
    }), [operationalKpi.sourceWindow, operationalKpiValues, operationalKpiDrilldown, fleetAttention?.summary, effectiveWorkspaceMode, tenantLifecycle]);

    return {
        onboardingThroughput,
        operationalKpi,
        operationalKpiDrilldown,
        operationalKpiById,
        criticalKpiCount,
        warnKpiCount,
        alertHookPayload,
        operationalReport,
    };
}
