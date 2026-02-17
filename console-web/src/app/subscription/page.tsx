"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { ConsolePageError, ConsolePageSkeleton } from "@/components/PageStates";
import { authApi, businessApi, canAccessConsole, type MetricFactMeta } from "@/lib/api-client";
import { QUERY_PROFILE_CONTEXT, QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

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

function meterStatusClass(status: "ok" | "warning" | "limit_reached" | "over_limit" | "not_included" | "included_not_configured" | "unknown"): string {
    if (status === "over_limit") {
        return "bg-red-100 text-red-800";
    }
    if (status === "warning" || status === "limit_reached" || status === "included_not_configured") {
        return "bg-amber-100 text-amber-800";
    }
    if (status === "ok") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "not_included") {
        return "bg-slate-200 text-slate-700";
    }
    return "bg-muted text-muted-foreground";
}

function meterStatusLabel(status: "ok" | "warning" | "limit_reached" | "over_limit" | "not_included" | "included_not_configured" | "unknown"): string {
    if (status === "ok") {
        return "Норма";
    }
    if (status === "warning") {
        return "Риск";
    }
    if (status === "limit_reached") {
        return "Лимит";
    }
    if (status === "over_limit") {
        return "Превышение";
    }
    if (status === "included_not_configured") {
        return "Нужно включить";
    }
    if (status === "not_included") {
        return "Не входит";
    }
    return "Нет контракта";
}

function paymentStatusClass(status: "pending" | "confirmed" | "rejected" | "unknown"): string {
    if (status === "confirmed") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "pending") {
        return "bg-amber-100 text-amber-800";
    }
    if (status === "rejected") {
        return "bg-red-100 text-red-800";
    }
    return "bg-muted text-muted-foreground";
}

function paymentStatusLabel(status: "pending" | "confirmed" | "rejected" | "unknown"): string {
    if (status === "confirmed") {
        return "Оплата подтверждена";
    }
    if (status === "pending") {
        return "Ожидает подтверждения";
    }
    if (status === "rejected") {
        return "Оплата отклонена";
    }
    return "Статус не заполнен";
}

function contractHealthClass(status: "ok" | "partial" | "missing"): string {
    if (status === "ok") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "partial") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-red-100 text-red-800";
}

function contractHealthLabel(status: "ok" | "partial" | "missing"): string {
    if (status === "ok") {
        return "Контракт подтвержден";
    }
    if (status === "partial") {
        return "Контракт частичный";
    }
    return "Контракт не заполнен";
}

function formatMetricMeta(meta?: MetricFactMeta): string {
    if (!meta) {
        return "missing · source: n/a";
    }
    const asOf = meta.as_of ? ` · as_of: ${meta.as_of}` : "";
    return `${meta.kind} · source: ${meta.source}${asOf}`;
}

function subscriptionSourceLabel(source: string): string {
    if (source === "company_billing_info") {
        return "Карточка компании";
    }
    if (source === "client_config") {
        return "Настройки клиента";
    }
    if (source === "onboarding_contract") {
        return "Онбординг контракт";
    }
    if (source === "unknown") {
        return "Источник не указан";
    }
    return source;
}

function meterSourceLabel(source: string): string {
    if (source.startsWith("subscription_contract:")) {
        const raw = source.replace("subscription_contract:", "");
        return `Контракт: ${subscriptionSourceLabel(raw)}`;
    }
    if (source.startsWith("onboarding_contract")) {
        return "Онбординг контракт";
    }
    return source;
}

function severityLabel(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "Критично";
    }
    if (severity === "warn") {
        return "Внимание";
    }
    return "Инфо";
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
        ...QUERY_PROFILE_CONTEXT,
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
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
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
            <ConsolePageSkeleton
                pageTestId="subscription-page"
                title="Подписка"
                titleTestId="subscription-title"
                columns={4}
                cardCount={4}
            />
        );
    }

    if (error || !data) {
        return (
            <ConsolePageError
                pageTestId="subscription-page"
                title="Подписка"
                titleTestId="subscription-title"
                errorTestId="subscription-error"
                retryTestId="subscription-retry"
                errorMessage="Не удалось загрузить сводку подписки"
                onRetry={() => {
                    refetch();
                }}
            />
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

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-contract">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">Контракт и статус оплаты</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${paymentStatusClass(data.payment_status)}`}>
                        {paymentStatusLabel(data.payment_status)}
                    </span>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Текущий план клиента</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">{data.plan_name || data.contract_label || "Не указан"}</p>
                        <p className="text-xs text-muted-foreground">Источник лимита: {subscriptionSourceLabel(data.quota_source)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Оплата</p>
                        <p className="mt-1 text-sm font-semibold text-foreground">{data.payment_status_message || "Статус оплаты не задан"}</p>
                        <p className="text-xs text-muted-foreground">Источник: {subscriptionSourceLabel(data.payment_status_source)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Лимит сообщений (контракт)</p>
                        <p className="mt-1 text-lg font-semibold text-foreground">{formatNumber(data.monthly_quota)}</p>
                        <p className="text-xs text-muted-foreground">
                            {data.monthly_quota === null || data.monthly_quota === undefined
                                ? "Не подтвержден"
                                : "Подтвержден"}
                        </p>
                    </div>
                </div>
            </section>

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-contract-health">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">Состояние контракта</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${contractHealthClass(data.contract_health.status)}`}>
                        {contractHealthLabel(data.contract_health.status)}
                    </span>
                </div>
                <p className="text-sm text-muted-foreground">{data.contract_health.summary}</p>
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Источник лимита сообщений</p>
                        <p className="mt-1 text-sm font-semibold text-foreground">{subscriptionSourceLabel(data.contract_health.quota_source)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Источник лимита WhatsApp</p>
                        <p className="mt-1 text-sm font-semibold text-foreground">{subscriptionSourceLabel(data.contract_health.whatsapp_source)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                        <p className="text-xs text-muted-foreground">Активный onboarding-контракт</p>
                        <p className="mt-1 text-sm font-semibold text-foreground">
                            {data.contract_health.has_active_onboarding_contract ? "Да" : "Нет"}
                        </p>
                    </div>
                </div>
                {data.contract_health.gaps.length > 0 ? (
                    <div className="mt-3 space-y-2">
                        {data.contract_health.gaps.map((gap) => (
                            <div key={gap.code} className="rounded-lg border border-border/60 bg-muted/30 p-3">
                                <p className="text-sm font-semibold text-foreground">{gap.message}</p>
                                <p className="text-xs text-muted-foreground">Код: {gap.code} · Приоритет: {severityLabel(gap.severity)}</p>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="mt-3 text-xs text-muted-foreground">Критичных пробелов по контракту не найдено.</p>
                )}
            </section>

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-reference-plan">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">Справка: стандартный Starter</p>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
                        reference-only
                    </span>
                </div>
                <p className="text-sm text-muted-foreground">
                    Этот блок не применяется автоматически к клиенту и не участвует в расчетах лимитов без подтвержденного контракта.
                </p>
                <p className="mt-2 text-sm font-semibold text-foreground">
                    {data.plan_defaults.plan_name}: {formatNumber(data.plan_defaults.included_messages)} сообщений · {formatNumber(data.plan_defaults.included_whatsapp_channels)} WhatsApp
                </p>
                <p className="text-xs text-muted-foreground">Источник справки: {data.plan_defaults.source}</p>
            </section>

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-meters">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Лимиты по направлениям</h2>
                    <span className="text-xs text-muted-foreground">{data.meters.length} показателей</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                        <thead className="border-b border-border/60 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            <tr>
                                <th className="py-2 pr-4">Показатель</th>
                                <th className="py-2 pr-4">Включено</th>
                                <th className="py-2 pr-4">Использовано</th>
                                <th className="py-2 pr-4">Остаток</th>
                                <th className="py-2 pr-4">Статус</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.meters.map((meter) => (
                                <tr key={meter.key} className="border-b border-border/40 align-top">
                                    <td className="py-2 pr-4">
                                        <p className="font-medium text-foreground">{meter.label}</p>
                                        <p className="text-xs text-muted-foreground">Источник: {meterSourceLabel(meter.source)}</p>
                                        {meter.note ? (
                                            <p className="mt-1 text-xs text-muted-foreground">{meter.note}</p>
                                        ) : null}
                                    </td>
                                    <td className="py-2 pr-4">{formatNumber(meter.included)}</td>
                                    <td className="py-2 pr-4">{formatNumber(meter.used)}</td>
                                    <td className="py-2 pr-4">{formatNumber(meter.remaining)}</td>
                                    <td className="py-2 pr-4">
                                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${meterStatusClass(meter.status)}`}>
                                            {meterStatusLabel(meter.status)}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
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

            <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="subscription-actions">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Что делать сейчас</h2>
                    <span className="text-xs text-muted-foreground">{data.recommended_actions.length} действий</span>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    {data.recommended_actions.map((action) => (
                        <div key={action.id} className="rounded-lg border border-border/60 bg-muted/30 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-foreground">{action.title}</p>
                                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${action.severity === "critical" ? "bg-red-100 text-red-800" : action.severity === "warn" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
                                    {severityLabel(action.severity)}
                                </span>
                            </div>
                            <p className="mt-2 text-xs text-muted-foreground">{action.description}</p>
                            <Link href={action.href} className="mt-3 inline-block text-xs font-semibold text-primary hover:underline">
                                Перейти к действию
                            </Link>
                        </div>
                    ))}
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
