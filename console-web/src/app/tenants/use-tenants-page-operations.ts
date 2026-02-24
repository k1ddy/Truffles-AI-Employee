"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { type QueryClient } from "@tanstack/react-query";
import { adminApi, opsApi, type TenantsOperationalSnapshotPayload, type TenantsWeeklySnapshotRecord } from "@/lib/api-client";
import type { OperationalKpiDrilldown } from "./operational-kpi";

type UseTenantsPageOperationsParams<TWeeklySnapshot extends { id: string; weekKey: string; createdAt: string; report: TenantsOperationalSnapshotPayload }> = {
    pageFilterClientId: string | null;
    operationalReport: TenantsOperationalSnapshotPayload;
    alertHookPayload: {
        severity: string;
        breaches: Array<{
            metric: string;
            label: string;
            status: string;
            value: number;
            reason: string;
            action: string;
        }>;
        [key: string]: unknown;
    };
    operationalKpiDrilldown: OperationalKpiDrilldown[];
    queryClient: QueryClient;
    weeklySnapshotsServerData: TWeeklySnapshot[] | undefined;
    mapWeeklySnapshotRecordToViewModel: (record: TenantsWeeklySnapshotRecord) => TWeeklySnapshot | null;
    buildLocalSnapshot: (input: {
        id: string;
        createdAt: string;
        weekKey: string;
        report: TenantsOperationalSnapshotPayload;
    }) => TWeeklySnapshot;
    buildWeekKey: (isoTimestamp: string) => string;
    maxWeeklySnapshots: number;
    reportValidationError: (message: string, code?: string, scope?: string) => void;
    reportError: (error: unknown, options?: { scope?: string }) => void;
    activeErrorScope: string;
};

function toCsvCell(value: string | number): string {
    const raw = String(value);
    if (raw.includes(",") || raw.includes("\"") || raw.includes("\n")) {
        return `"${raw.replaceAll("\"", "\"\"")}"`;
    }
    return raw;
}

export function useTenantsPageOperations<TWeeklySnapshot extends { id: string; weekKey: string; createdAt: string; report: TenantsOperationalSnapshotPayload }>({
    pageFilterClientId,
    operationalReport,
    alertHookPayload,
    operationalKpiDrilldown,
    queryClient,
    weeklySnapshotsServerData,
    mapWeeklySnapshotRecordToViewModel,
    buildLocalSnapshot,
    buildWeekKey,
    maxWeeklySnapshots,
    reportValidationError,
    reportError,
    activeErrorScope,
}: UseTenantsPageOperationsParams<TWeeklySnapshot>) {
    const [weeklySnapshots, setWeeklySnapshots] = useState<TWeeklySnapshot[]>([]);
    const [runningMetricsSnapshotMode, setRunningMetricsSnapshotMode] = useState<"dry_run" | "execute" | null>(null);
    const [lastMetricsSnapshotJob, setLastMetricsSnapshotJob] = useState<{
        job_type?: string | null;
        mode?: string | null;
        status?: string | null;
    } | null>(null);

    useEffect(() => {
        if (!pageFilterClientId) {
            setWeeklySnapshots([]);
            return;
        }
        if (!weeklySnapshotsServerData) {
            return;
        }
        setWeeklySnapshots(weeklySnapshotsServerData);
    }, [pageFilterClientId, weeklySnapshotsServerData]);

    const exportOperationalReport = (format: "json" | "csv") => {
        const timestamp = new Date().toISOString().replaceAll(":", "-");
        if (format === "json") {
            const content = JSON.stringify(
                {
                    report: operationalReport,
                    alert_payload: alertHookPayload,
                },
                null,
                2,
            );
            const blob = new Blob([content], { type: "application/json;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `tenants-operational-report-${timestamp}.json`;
            link.click();
            URL.revokeObjectURL(url);
            toast.success("Отчёт JSON выгружен");
            return;
        }
        const rows = [
            ["metric", "value", "status", "reason"],
            ...operationalKpiDrilldown.map((item) => [
                item.id,
                item.displayValue,
                item.status,
                item.reason,
            ]),
        ];
        const csvContent = rows.map((row) => row.map((cell) => toCsvCell(cell)).join(",")).join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `tenants-operational-report-${timestamp}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success("Отчёт CSV выгружен");
    };

    const saveWeeklySnapshot = async () => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы", "VALIDATION_ERROR", "portfolio");
            return;
        }
        const now = new Date().toISOString();
        const weekKey = buildWeekKey(now);
        const localSnapshot = buildLocalSnapshot({
            id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : `${Date.now()}`,
            createdAt: now,
            weekKey,
            report: operationalReport,
        });
        const applySnapshot = (snapshot: TWeeklySnapshot) => {
            setWeeklySnapshots((previous) => {
                const withoutWeek = previous.filter((item) => item.weekKey !== snapshot.weekKey);
                return [snapshot, ...withoutWeek].slice(0, maxWeeklySnapshots);
            });
        };
        try {
            const response = await adminApi.saveTenantsWeeklySnapshot({
                client_id: pageFilterClientId,
                week_key: weekKey,
                snapshot: operationalReport,
            });
            const mappedSnapshot = mapWeeklySnapshotRecordToViewModel(response.data.item);
            applySnapshot(mappedSnapshot ?? localSnapshot);
            queryClient.invalidateQueries({
                queryKey: ["tenants-weekly-snapshots", pageFilterClientId],
            });
            toast.success(`Недельный снимок сохранён (${weekKey})`);
        } catch (error) {
            reportError(error, { scope: "portfolio" });
            toast.error(`Не удалось сохранить недельный снимок (${weekKey})`);
        }
    };

    const copyAlertHookPayload = async () => {
        const serialized = JSON.stringify(alertHookPayload, null, 2);
        try {
            await navigator.clipboard.writeText(serialized);
            toast.success("Данные уведомления скопированы");
        } catch {
            reportValidationError("Не удалось скопировать данные уведомления");
        }
    };

    const runMetricsSnapshotHook = async (mode: "dry_run" | "execute") => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы");
            return;
        }
        setRunningMetricsSnapshotMode(mode);
        try {
            const response = await opsApi.runJob({
                job_type: "metrics_snapshot",
                mode,
                params: ({ days: 7 } as unknown as Record<string, never>),
            });
            setLastMetricsSnapshotJob(response.data.job);
            toast.success(mode === "dry_run" ? "Пробный снимок метрик выполнен" : "Снимок метрик выполнен");
        } catch (error) {
            reportError(error, { scope: activeErrorScope });
        } finally {
            setRunningMetricsSnapshotMode(null);
        }
    };

    return {
        weeklySnapshots,
        runningMetricsSnapshotMode,
        lastMetricsSnapshotJob,
        exportOperationalReport,
        saveWeeklySnapshot,
        copyAlertHookPayload,
        runMetricsSnapshotHook,
    };
}
