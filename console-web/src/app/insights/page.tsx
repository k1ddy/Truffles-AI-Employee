"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { authApi, canAccessConsole, opsApi } from "@/lib/api-client";

function formatMetricDate(value?: string | null): string {
    if (!value) {
        return "—";
    }
    const parsed = new Date(`${value}T00:00:00Z`);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("ru-RU");
}

function formatHours(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return `${value.toFixed(1)} ч`;
}

function formatCount(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return value.toLocaleString("ru-RU");
}

function MetricTile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
    return (
        <div className="bg-muted rounded-lg p-4 text-center">
            <div className="text-2xl font-semibold text-foreground">{value}</div>
            <div className="text-sm text-muted-foreground">{label}</div>
            {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
        </div>
    );
}

export default function InsightsPage() {
    const { data: session } = useSession();
    const [selectedDate, setSelectedDate] = useState("");

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadInsights = canAccessConsole(role, "insights", "read");

    const queryDate = selectedDate || undefined;
    const {
        data: metrics,
        isLoading,
        error,
        refetch,
        isFetching,
    } = useQuery({
        queryKey: ["insights-metrics", queryDate ?? "today"],
        queryFn: async () => {
            const response = await opsApi.getMetricsDaily(queryDate);
            return response.data;
        },
        enabled: !!session && canReadInsights,
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра аналитики.
            </div>
        );
    }

    if (meLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canReadInsights) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к аналитике." />
        );
    }

    const reportDate = formatMetricDate(metrics?.date ?? selectedDate);

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="insights-page">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold mb-1" data-testid="insights-title">Аналитика</h1>
                    <p className="text-sm text-muted-foreground">
                        Ежедневная сводка по сообщениям и заявкам.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Дата</span>
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(event) => setSelectedDate(event.target.value)}
                        className="px-2 py-2 border border-border/60 rounded-lg text-xs bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                        data-testid="insights-date"
                    />
                    <button
                        onClick={() => setSelectedDate("")}
                        className="rounded-full border border-border/60 px-3 py-2 text-xs font-semibold text-foreground transition hover:bg-muted"
                        data-testid="insights-today"
                    >
                        Сегодня
                    </button>
                    <button
                        onClick={() => refetch()}
                        className="rounded-full bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground transition hover:bg-primary/90"
                        data-testid="insights-refresh"
                        disabled={isFetching}
                    >
                        {isFetching ? "Обновление..." : "Обновить"}
                    </button>
                </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                <span>Дата отчета:</span>
                <span className="font-semibold text-foreground">{reportDate}</span>
            </div>

            {isLoading ? (
                <div className="space-y-4" data-testid="insights-loading">
                    <div className="grid gap-4 md:grid-cols-2 animate-pulse">
                        {[...Array(2)].map((_, index) => (
                            <div key={`msg-${index}`} className="h-24 bg-muted/70 rounded-lg"></div>
                        ))}
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5 animate-pulse">
                        {[...Array(5)].map((_, index) => (
                            <div key={`case-${index}`} className="h-24 bg-muted/70 rounded-lg"></div>
                        ))}
                    </div>
                </div>
            ) : error ? (
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="insights-error">
                    <p className="text-destructive mb-4">Не удалось загрузить аналитику</p>
                    <button
                        onClick={() => refetch()}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="insights-retry"
                    >
                        Повторить
                    </button>
                </div>
            ) : (
                <div className="space-y-4" data-testid="insights-metrics">
                    <div className="grid gap-4 md:grid-cols-2">
                        <MetricTile label="Сообщений от клиентов" value={formatCount(metrics?.total_client_messages)} />
                        <MetricTile label="Ответов бота" value={formatCount(metrics?.total_bot_messages)} />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                        <MetricTile label="Всего заявок" value={metrics?.total_cases ?? 0} />
                        <MetricTile label="Ожидают ответа" value={metrics?.pending_cases ?? 0} />
                        <MetricTile label="В работе" value={metrics?.active_cases ?? 0} />
                        <MetricTile label="Закрыты" value={metrics?.resolved_cases ?? 0} />
                        <MetricTile label="Среднее время" value={formatHours(metrics?.avg_resolution_hours)} />
                    </div>
                </div>
            )}
        </div>
    );
}
