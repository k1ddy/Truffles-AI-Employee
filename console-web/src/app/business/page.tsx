"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { authApi, businessApi, canAccessConsole } from "@/lib/api-client";

function formatMinutes(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 60) {
        return `${value} мин`;
    }
    const hours = value / 60;
    if (hours < 24) {
        return `${hours.toFixed(1)} ч`;
    }
    return `${(hours / 24).toFixed(1)} д`;
}

function formatSeconds(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 60) {
        return `${Math.round(value)} с`;
    }
    const minutes = value / 60;
    if (minutes < 60) {
        return `${minutes.toFixed(1)} мин`;
    }
    return `${(minutes / 60).toFixed(1)} ч`;
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

export default function BusinessPage() {
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
        queryKey: ["business-summary"],
        queryFn: async () => {
            const response = await businessApi.getSummary();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 30000,
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра бизнес-сводки.
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

    if (!canReadBusiness) {
        return <AccessDenied message="Эта роль не имеет доступа к разделу Бизнес." />;
    }

    if (isLoading) {
        return (
            <div className="mx-auto max-w-5xl p-6" data-testid="business-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="business-title">Бизнес</h1>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="h-28 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-28 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-28 animate-pulse rounded-lg bg-muted/70" />
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="mx-auto max-w-5xl p-6" data-testid="business-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="business-title">Бизнес</h1>
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid="business-error">
                    <p className="mb-4 text-destructive">Не удалось загрузить бизнес-сводку</p>
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="business-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-5xl p-6" data-testid="business-page">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="business-title">Бизнес</h1>
                    <p className="mt-1 text-sm text-muted-foreground" data-testid="business-generated-at">
                        Обновлено: {new Date(data.generated_at).toLocaleString("ru-RU")}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="btn-ghost"
                        disabled={isFetching}
                        data-testid="business-refresh"
                    >
                        {isFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/insights" className="btn-ghost">Открыть аналитику</Link>
                </div>
            </div>

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="business-status-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус бизнеса</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{data.status_label}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(data.status)}`} data-testid="business-status-chip">
                        {data.status}
                    </span>
                </div>
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-3" data-testid="business-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Очередь отправки</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.outbox_backlog}</p>
                    <p className="text-xs text-muted-foreground">failed за 24ч: {data.outbox_failed_24h}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Неразобранные заявки</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.unresolved_cases}</p>
                    <p className="text-xs text-muted-foreground">pending: {data.pending_cases} · active: {data.active_cases}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Скорость ответа</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.first_response_p90_seconds)}</p>
                    <p className="text-xs text-muted-foreground">старейшая незавершенная: {formatMinutes(data.oldest_unresolved_minutes)}</p>
                </div>
            </section>

            <section className="mt-6 rounded-xl border border-border/60 bg-card p-4" data-testid="business-actions">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Приоритетные действия</h2>
                    <span className="text-xs text-muted-foreground">{data.actions.length} шт.</span>
                </div>
                <div className="space-y-3">
                    {data.actions.map((action) => (
                        <article key={action.id} className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid={`business-action-${action.id}`}>
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
