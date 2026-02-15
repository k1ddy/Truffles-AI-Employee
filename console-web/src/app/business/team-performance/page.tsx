"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { authApi, businessApi, canAccessConsole } from "@/lib/api-client";

function formatNumber(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return value.toLocaleString("ru-RU");
}

function formatSeconds(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 60) {
        return `${Math.round(value)} с`;
    }
    if (value < 3600) {
        return `${(value / 60).toFixed(1)} мин`;
    }
    return `${(value / 3600).toFixed(1)} ч`;
}

function formatMinutes(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 60) {
        return `${Math.round(value)} мин`;
    }
    return `${(value / 60).toFixed(1)} ч`;
}

function statusChipClass(status?: string | null): string {
    if (status === "unhealthy") {
        return "bg-red-100 text-red-800";
    }
    if (status === "degraded") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-emerald-100 text-emerald-800";
}

function actionChipClass(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "bg-red-100 text-red-800";
    }
    if (severity === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

export default function BusinessTeamPerformancePage() {
    const { data: session } = useSession();

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadBusiness = canAccessConsole(role, "business", "read");

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["business-team-performance"],
        queryFn: async () => {
            const response = await businessApi.getTeamPerformanceSummary();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 45000,
    });

    if (!session) {
        return <div className="p-8 text-center text-muted-foreground">Пожалуйста, войдите для просмотра Team KPI.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли...</div>;
    }

    if (!canReadBusiness) {
        return <AccessDenied message="Эта роль не имеет доступа к разделу Team Performance." />;
    }

    if (isLoading) {
        return (
            <div className="mx-auto max-w-6xl p-6" data-testid="team-performance-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="team-performance-title">Эффективность команды</h1>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="mx-auto max-w-6xl p-6" data-testid="team-performance-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="team-performance-title">Эффективность команды</h1>
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid="team-performance-error">
                    <p className="mb-4 text-destructive">Не удалось загрузить Team Performance сводку</p>
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="team-performance-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-6xl p-6" data-testid="team-performance-page">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="team-performance-title">Эффективность команды</h1>
                    <p className="mt-1 text-sm text-muted-foreground" data-testid="team-performance-generated-at">
                        Обновлено: {new Date(data.generated_at).toLocaleString("ru-RU")}
                    </p>
                    <p className="text-xs text-muted-foreground" data-testid="team-performance-metric-date">
                        Метрики за дату: {data.metric_date || "нет данных"}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="btn-ghost"
                        disabled={isFetching}
                        data-testid="team-performance-refresh"
                    >
                        {isFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/business" className="btn-ghost">Назад в Бизнес</Link>
                </div>
            </div>

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="team-performance-status-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус команды</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{data.status_label}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(data.status)}`} data-testid="team-performance-status-chip">
                        {data.status}
                    </span>
                </div>
                {data.analytics_scope_limited ? (
                    <p className="mt-3 rounded-lg border border-amber-300/60 bg-amber-50 px-3 py-2 text-xs text-amber-800" data-testid="team-performance-scope-warning">
                        Вы работаете в branch-режиме: client-level KPI сравнение ограничено.
                    </p>
                ) : null}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-4" data-testid="team-performance-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Открытые заявки</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.unresolved_cases)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Старше 60 минут</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.unresolved_older_than_60m)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Медиана ответа менеджера</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.manager_median_response_seconds)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">P90 первого ответа</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.first_response_p90_seconds)}</p>
                </div>
            </section>

            <section className="mt-6 rounded-xl border border-border/60 bg-card p-4" data-testid="team-performance-managers">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Нагрузка по менеджерам</h2>
                    <span className="text-xs text-muted-foreground">{data.managers.length} в списке</span>
                </div>
                {data.managers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Нет открытых заявок в текущем scope.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-left text-sm" data-testid="team-performance-table">
                            <thead className="border-b border-border/60 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                                <tr>
                                    <th className="py-2 pr-4">Менеджер</th>
                                    <th className="py-2 pr-4">Открыто</th>
                                    <th className="py-2 pr-4">Pending</th>
                                    <th className="py-2 pr-4">Active</th>
                                    <th className="py-2 pr-4">Старейшая</th>
                                    <th className="py-2 pr-4">Avg first response (30д)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.managers.map((item) => (
                                    <tr key={item.manager_name} className="border-b border-border/40">
                                        <td className="py-2 pr-4 font-medium">{item.manager_name}</td>
                                        <td className="py-2 pr-4">{formatNumber(item.unresolved_cases)}</td>
                                        <td className="py-2 pr-4">{formatNumber(item.pending_cases)}</td>
                                        <td className="py-2 pr-4">{formatNumber(item.active_cases)}</td>
                                        <td className="py-2 pr-4">{formatMinutes(item.oldest_unresolved_minutes)}</td>
                                        <td className="py-2 pr-4">{formatSeconds(item.avg_first_response_seconds_30d)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            <section className="mt-6 rounded-xl border border-border/60 bg-card p-4" data-testid="team-performance-actions">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Рекомендуемые действия</h2>
                    <span className="text-xs text-muted-foreground">{data.actions.length} шт.</span>
                </div>
                <div className="space-y-3">
                    {data.actions.map((action) => (
                        <article key={action.id} className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid={`team-performance-action-${action.id}`}>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-foreground">{action.title}</p>
                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${actionChipClass(action.severity)}`}>
                                    {action.severity}
                                </span>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">{action.description}</p>
                            <div className="mt-3">
                                <Link href={action.href} className="btn-ghost">Перейти</Link>
                            </div>
                        </article>
                    ))}
                </div>
            </section>
        </div>
    );
}
