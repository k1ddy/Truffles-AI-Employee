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

function formatPercent(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return `${value.toFixed(1)}%`;
}

function usageBarWidth(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "0%";
    }
    const normalized = Math.max(0, Math.min(100, value));
    return `${normalized.toFixed(1)}%`;
}

function subscriptionAlertClass(level: "normal" | "warning_80" | "limit_100"): string {
    if (level === "limit_100") {
        return "border-red-300 bg-red-50 text-red-900";
    }
    if (level === "warning_80") {
        return "border-amber-300 bg-amber-50 text-amber-900";
    }
    return "border-emerald-300 bg-emerald-50 text-emerald-900";
}

function formatMetricMeta(meta?: MetricFactMeta): string {
    if (!meta) {
        return "missing · source: n/a";
    }
    const asOf = meta.as_of ? ` · as_of: ${meta.as_of}` : "";
    return `${meta.kind} · source: ${meta.source}${asOf}`;
}

export default function SubscriptionPage() {
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
    const canReadSubscription = canAccessConsole(role, "subscription", "read");

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["subscription-summary"],
        queryFn: async () => {
            const response = await businessApi.getSubscriptionSummary();
            return response.data;
        },
        enabled: !!session && canReadSubscription,
        refetchInterval: 60000,
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра подписки.
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

    if (!canReadSubscription) {
        return <AccessDenied message="Эта роль не имеет доступа к разделу Подписка." />;
    }

    if (isLoading) {
        return (
            <div className="mx-auto max-w-6xl p-6" data-testid="subscription-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="subscription-title">Подписка</h1>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                    <div className="h-24 animate-pulse rounded-lg bg-muted/70" />
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="mx-auto max-w-6xl p-6" data-testid="subscription-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="subscription-title">Подписка</h1>
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid="subscription-error">
                    <p className="mb-4 text-destructive">Не удалось загрузить сводку подписки</p>
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="subscription-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-6xl p-6" data-testid="subscription-page">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="subscription-title">Подписка</h1>
                    <p className="mt-1 text-sm text-muted-foreground" data-testid="subscription-period">
                        Период: {data.period_start} - {data.period_end}
                    </p>
                    <p className="text-xs text-muted-foreground" data-testid="subscription-next-billing-date">
                        Следующее списание: {data.next_billing_date}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="btn-ghost"
                        disabled={isFetching}
                        data-testid="subscription-refresh"
                    >
                        {isFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/ops" className="btn-ghost">Открыть статус</Link>
                </div>
            </div>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-4" data-testid="subscription-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">План</p>
                    <p className="mt-1 text-lg font-semibold text-foreground">{data.plan_name || data.contract_label || "Не указан"}</p>
                    <p className="text-xs text-muted-foreground">Источник: {data.quota_source}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.monthly_quota)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Лимит в месяц</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.monthly_quota)}</p>
                    <p className="text-xs text-muted-foreground">Валюта: {data.currency || "—"}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.monthly_quota)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Использовано</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.billable_messages)}</p>
                    <p className="text-xs text-muted-foreground">Остаток: {formatNumber(data.remaining_quota)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.billable_messages)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Прогноз за месяц</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.projected_month_total)}</p>
                    <p className="text-xs text-muted-foreground">Загрузка лимита: {formatPercent(data.usage_percent)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.projected_month_total)}</p>
                </div>
            </section>

            <section
                className={`mt-4 rounded-xl border p-4 ${subscriptionAlertClass(data.quota_alert_level)}`}
                data-testid="subscription-alert"
            >
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold">Алерт квоты</p>
                    <span className="rounded-full border border-current/30 px-2 py-0.5 text-xs font-semibold">
                        {data.quota_alert_level}
                    </span>
                </div>
                <p className="mt-2 text-sm">{data.quota_alert_message}</p>
                <p className="mt-1 text-xs">
                    Что при превышении: {data.overage_policy_message}
                </p>
            </section>

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-usage">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">Использование квоты</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${data.over_quota ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>
                        {data.over_quota ? "Лимит превышен" : "В пределах лимита"}
                    </span>
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div
                        className={`h-full transition-all ${data.over_quota ? "bg-red-500" : "bg-emerald-500"}`}
                        style={{ width: usageBarWidth(data.usage_percent) }}
                        data-testid="subscription-usage-bar"
                    />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                    Формула биллинга основана на подтвержденных исходящих outbox-сообщениях.
                </p>
            </section>

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-forecast-v2">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">Прогноз до конца периода</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${data.projected_over_quota ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}`}>
                        {data.projected_over_quota ? "Риск перерасхода" : "В пределах лимита"}
                    </span>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Прогнозируемый остаток</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                            {formatNumber(data.projected_remaining_quota)}
                        </p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Прогнозируемый перерасход</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">
                            {formatNumber(data.projected_overage_messages)}
                        </p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Следующее списание</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">{data.next_billing_date}</p>
                    </div>
                </div>
            </section>

            <section className="mt-6 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-evidence">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Доказательства по сообщениям</h2>
                    <span className="text-xs text-muted-foreground">{data.evidence.length} последних записей</span>
                </div>
                {data.evidence.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Нет биллинговых сообщений за выбранный период.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-left text-sm" data-testid="subscription-evidence-table">
                            <thead className="border-b border-border/60 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                                <tr>
                                    <th className="py-2 pr-4">Время</th>
                                    <th className="py-2 pr-4">Outbox ID</th>
                                    <th className="py-2 pr-4">Статус</th>
                                    <th className="py-2 pr-4">Provider</th>
                                    <th className="py-2 pr-4">Inbound ID</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.evidence.map((item) => (
                                    <tr key={item.outbox_id} className="border-b border-border/40">
                                        <td className="py-2 pr-4 whitespace-nowrap">{new Date(item.created_at).toLocaleString("ru-RU")}</td>
                                        <td className="py-2 pr-4 font-mono text-xs">{item.outbox_id}</td>
                                        <td className="py-2 pr-4">{item.status}</td>
                                        <td className="py-2 pr-4">{item.provider_status || "—"}</td>
                                        <td className="py-2 pr-4 font-mono text-xs">{item.inbound_message_id}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    );
}
