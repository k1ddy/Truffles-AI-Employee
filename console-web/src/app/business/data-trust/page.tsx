"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { authApi, businessApi, canAccessConsole, type MetricFactMeta } from "@/lib/api-client";

function formatNumber(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return value.toLocaleString("ru-RU");
}

function formatHours(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 24) {
        return `${Math.round(value)} ч`;
    }
    return `${(value / 24).toFixed(1)} д`;
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

function formatMetricMeta(meta?: MetricFactMeta): string {
    if (!meta) {
        return "missing · source: n/a";
    }
    const asOf = meta.as_of ? ` · as_of: ${meta.as_of}` : "";
    return `${meta.kind} · source: ${meta.source}${asOf}`;
}

export default function BusinessDataTrustPage() {
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
        queryKey: ["business-data-trust"],
        queryFn: async () => {
            const response = await businessApi.getDataTrustSummary();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 45000,
    });

    if (!session) {
        return <div className="p-8 text-center text-muted-foreground">Пожалуйста, войдите для просмотра Data Trust.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли...</div>;
    }

    if (!canReadBusiness) {
        return <AccessDenied message="Эта роль не имеет доступа к разделу Data Trust." />;
    }

    if (isLoading) {
        return (
            <div className="mx-auto max-w-6xl p-6" data-testid="data-trust-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="data-trust-title">Надежность данных</h1>
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
            <div className="mx-auto max-w-6xl p-6" data-testid="data-trust-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="data-trust-title">Надежность данных</h1>
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid="data-trust-error">
                    <p className="mb-4 text-destructive">Не удалось загрузить Data Trust сводку</p>
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="data-trust-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-6xl p-6" data-testid="data-trust-page">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="data-trust-title">Надежность данных</h1>
                    <p className="mt-1 text-sm text-muted-foreground" data-testid="data-trust-generated-at">
                        Обновлено: {new Date(data.generated_at).toLocaleString("ru-RU")}
                    </p>
                    <p className="text-xs text-muted-foreground" data-testid="data-trust-metric-date">
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
                        data-testid="data-trust-refresh"
                    >
                        {isFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/business" className="btn-ghost">Назад в Бизнес</Link>
                </div>
            </div>

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="data-trust-status-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус доверия к данным</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{data.status_label}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(data.status)}`} data-testid="data-trust-status-chip">
                        {data.status}
                    </span>
                </div>
                {data.analytics_scope_limited ? (
                    <p className="mt-3 rounded-lg border border-amber-300/60 bg-amber-50 px-3 py-2 text-xs text-amber-800" data-testid="data-trust-scope-warning">
                        Вы работаете в branch-режиме: часть quality-метрик доступна только в полном company scope.
                    </p>
                ) : null}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-4" data-testid="data-trust-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Пробелы first response</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.first_response_missing_total)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.first_response_missing_total)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Пробелы escalation meta</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.escalation_meta_missing_total)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.escalation_meta_missing_total)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Пробелы intent</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.intent_missing_total)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.intent_missing_total)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Свежесть знаний</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatHours(data.knowledge_stale_hours)}</p>
                    <p className="text-xs text-muted-foreground">
                        последняя публикация: {data.knowledge_last_published_at ? new Date(data.knowledge_last_published_at).toLocaleString("ru-RU") : "—"}
                    </p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.knowledge_stale_hours)}</p>
                </div>
            </section>

            <section className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2" data-testid="data-trust-audit-grid">
                <div className="rounded-lg border border-border/60 bg-card p-4">
                    <p className="text-sm text-muted-foreground">Audit-события за 24 часа</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.audit_events_24h)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-card p-4">
                    <p className="text-sm text-muted-foreground">Критичные audit-события</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.critical_audit_events_24h)}</p>
                </div>
            </section>

            <section className="mt-6 rounded-xl border border-border/60 bg-card p-4" data-testid="data-trust-actions">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Рекомендуемые действия</h2>
                    <span className="text-xs text-muted-foreground">{data.actions.length} шт.</span>
                </div>
                <div className="space-y-3">
                    {data.actions.map((action) => (
                        <article key={action.id} className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid={`data-trust-action-${action.id}`}>
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
