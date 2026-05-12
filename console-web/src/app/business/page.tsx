"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useMemo } from "react";

import AccessDenied from "@/components/AccessDenied";
import { ConsolePageError, ConsolePageSkeleton } from "@/components/PageStates";
import {
    authApi,
    businessApi,
    canAccessConsole,
    type GoNoGoReadinessFinding,
    type GoNoGoReadinessResponse,
    type IncidentItem,
    type MetricFactMeta,
} from "@/lib/api-client";
import { getProviderErrorContract } from "@/lib/provider-error-contract";
import { QUERY_PROFILE_CONTEXT, QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

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

function formatPercent(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return `${value.toFixed(1)}%`;
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

function statusChipLabel(status?: string | null): string {
    if (status === "unhealthy") {
        return "Требует срочного внимания";
    }
    if (status === "degraded") {
        return "Есть риск задержек";
    }
    return "Стабильно";
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

function incidentChipClass(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "bg-red-100 text-red-800";
    }
    if (severity === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

function severityLabel(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "Срочно";
    }
    if (severity === "warn") {
        return "Важно";
    }
    return "Планово";
}

function verdictChipClass(verdict?: GoNoGoReadinessResponse["verdict"] | null): string {
    if (verdict === "blocked") {
        return "bg-red-100 text-red-800";
    }
    if (verdict === "no_go") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-emerald-100 text-emerald-800";
}

function verdictLabel(verdict?: GoNoGoReadinessResponse["verdict"] | null): string {
    if (verdict === "blocked") {
        return "BLOCKED";
    }
    if (verdict === "no_go") {
        return "NO-GO";
    }
    return "GO";
}

function readinessChipClass(ready: boolean): string {
    return ready ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800";
}

function readinessLabel(ready: boolean): string {
    return ready ? "Готово" : "Не готово";
}

function findingCategoryLabel(category: GoNoGoReadinessFinding["category"]): string {
    const labels: Record<GoNoGoReadinessFinding["category"], string> = {
        provider: "Провайдер",
        onboarding: "Onboarding",
        data_trust: "Данные",
        business: "Бизнес",
        booking: "Записи",
        runtime: "Runtime",
        knowledge: "Знания",
        support: "Support",
    };
    return labels[category] ?? category;
}

function evidenceChipClass(status: "pass" | "warn" | "fail" | "unknown"): string {
    if (status === "pass") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "fail") {
        return "bg-red-100 text-red-800";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

type BusinessNowStep = {
    id: string;
    title: string;
    summary: string;
    href: string;
    severity: "critical" | "warn" | "info";
};

function formatMetricMeta(meta?: MetricFactMeta): string {
    if (!meta) {
        return "missing · source: n/a";
    }
    const asOf = meta.as_of ? ` · as_of: ${meta.as_of}` : "";
    return `${meta.kind} · source: ${meta.source}${asOf}`;
}

function findBillingBlockedIncident(items: IncidentItem[] | undefined): IncidentItem | null {
    if (!items?.length) {
        return null;
    }
    return items.find((item) => item.reason_code === "provider_billing_blocked") ?? null;
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
        ...QUERY_PROFILE_CONTEXT,
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
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const {
        data: readinessData,
        isLoading: readinessLoading,
        error: readinessError,
        refetch: refetchReadiness,
        isFetching: readinessFetching,
    } = useQuery({
        queryKey: ["business-go-no-go-readiness"],
        queryFn: async () => {
            const response = await businessApi.getGoNoGoReadiness();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: incidentsData, isLoading: incidentsLoading } = useQuery({
        queryKey: ["business-incidents"],
        queryFn: async () => {
            const response = await businessApi.getIncidents();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });
    const billingBlockedIncident = useMemo(
        () => findBillingBlockedIncident(incidentsData?.items),
        [incidentsData?.items],
    );
    const billingIncidentLinks = useMemo(
        () => (
            billingBlockedIncident?.actions
                ?.filter((action) => Boolean(action.href))
                .slice(0, 3)
                ?? []
        ),
        [billingBlockedIncident?.actions],
    );
    const billingBlockedContract = useMemo(
        () => (
            billingBlockedIncident
                ? getProviderErrorContract(billingBlockedIncident.reason_code)
                : null
        ),
        [billingBlockedIncident],
    );

    const todaySteps = useMemo<BusinessNowStep[]>(() => {
        if (!data) {
            return [];
        }
        const steps: BusinessNowStep[] = [];
        const effectivePlanned = Math.max(0, data.scheduled_visits_today - data.cancelled_visits_today);
        if (data.no_show_followup_pending > 0) {
            steps.push({
                id: "no_show_followup_pending",
                title: "Разберите неявки без follow-up",
                summary: `По ${data.no_show_followup_pending} неявкам ещё нет действия менеджера.`,
                href: "/calendar",
                severity: data.no_show_followup_pending >= 5 ? "critical" : "warn",
            });
        }
        if (data.reminder_delivery_failures_today > 0) {
            steps.push({
                id: "reminder_delivery_failures",
                title: "Проверьте сбои напоминаний",
                summary: `Сегодня ошибок доставки напоминаний: ${data.reminder_delivery_failures_today}.`,
                href: "/ops",
                severity: data.reminder_delivery_failures_today >= 10 ? "critical" : "warn",
            });
        }
        if (effectivePlanned >= 5 && data.no_show_visits_today > 0) {
            const noShowRate = data.no_show_visits_today / effectivePlanned;
            if (noShowRate >= 0.3) {
                steps.push({
                    id: "reduce_no_show",
                    title: "Снизьте неявки по записям",
                    summary: `Не пришли ${data.no_show_visits_today} из ${effectivePlanned} запланированных визитов.`,
                    href: "/calendar",
                    severity: noShowRate >= 0.5 ? "critical" : "warn",
                });
            }
        }

        if (data.outbox_backlog >= 500 || data.outbox_failed_24h >= 30) {
            steps.push({
                id: "stabilize_delivery",
                title: "Стабилизируйте доставку ответов",
                summary: "Откройте Статус и снизьте pending/failed, чтобы клиенты не ждали.",
                href: "/ops",
                severity: data.outbox_backlog >= 1000 || data.outbox_failed_24h >= 100 ? "critical" : "warn",
            });
        }
        if (data.unresolved_cases > 0) {
            steps.push({
                id: "clear_open_cases",
                title: "Разберите открытые заявки",
                summary: "Проверьте очередь заявок и назначение менеджеров.",
                href: "/",
                severity: data.unresolved_cases > 20 ? "critical" : "warn",
            });
        }
        if (data.first_response_p90_seconds !== null && data.first_response_p90_seconds !== undefined && data.first_response_p90_seconds > 900) {
            steps.push({
                id: "improve_reply_speed",
                title: "Ускорьте первый ответ менеджеров",
                summary: "Откройте показатели команды и примените быстрый профиль.",
                href: "/business/team-performance",
                severity: "warn",
            });
        }
        if ((incidentsData?.summary.critical ?? 0) > 0) {
            steps.push({
                id: "review_incidents",
                title: "Проверьте критичные инциденты",
                summary: "Сверьте причины и запустите предложенные действия.",
                href: "/business",
                severity: "critical",
            });
        }
        if (!steps.length) {
            steps.push({
                id: "daily_control",
                title: "Ситуация стабильная",
                summary: "Держите ежедневный контроль: заявки, скорость ответа, лимиты.",
                href: "/subscription",
                severity: "info",
            });
        }

        return steps.slice(0, 3);
    }, [data, incidentsData?.summary.critical]);

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
        return <ConsolePageSkeleton pageTestId="business-page" title="Бизнес" titleTestId="business-title" columns={3} cardCount={3} cardHeightClass="h-28" maxWidthClass="max-w-5xl" />;
    }

    if (error || !data) {
        return (
            <ConsolePageError
                pageTestId="business-page"
                title="Бизнес"
                titleTestId="business-title"
                errorTestId="business-error"
                retryTestId="business-retry"
                errorMessage="Не удалось загрузить бизнес-сводку"
                maxWidthClass="max-w-5xl"
                onRetry={() => {
                    refetch();
                }}
            />
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
                            refetchReadiness();
                        }}
                        className="btn-ghost"
                        disabled={isFetching || readinessFetching}
                        data-testid="business-refresh"
                    >
                        {isFetching || readinessFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/insights" className="btn-ghost">Открыть аналитику</Link>
                </div>
            </div>

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="business-status-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус бизнеса</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{data.status_label}</p>
                        <p className="mt-1 text-xs text-muted-foreground">Технический статус: {data.status}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(data.status)}`} data-testid="business-status-chip">
                        {statusChipLabel(data.status)}
                    </span>
                </div>
            </section>

            <section
                className="mb-4 rounded-xl border border-border/60 bg-card p-4"
                data-testid="business-go-no-go-card"
            >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Go/No-Go запуска</p>
                        <h2 className="mt-1 text-xl font-semibold text-foreground">
                            {readinessData?.status_label ?? "Проверяем готовность запуска..."}
                        </h2>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Единый verdict по onboarding, provider, данным, бизнес-сводке и internal calendar.
                        </p>
                    </div>
                    {readinessData ? (
                        <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold ${verdictChipClass(readinessData.verdict)}`}
                            data-testid="business-go-no-go-verdict"
                        >
                            {verdictLabel(readinessData.verdict)}
                        </span>
                    ) : (
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                            {readinessLoading ? "LOADING" : "UNKNOWN"}
                        </span>
                    )}
                </div>

                {readinessError ? (
                    <div
                        className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-900"
                        data-testid="business-go-no-go-error"
                    >
                        Не удалось загрузить Go/No-Go readiness. Не считайте бизнес готовым, пока этот статус неизвестен.
                    </div>
                ) : readinessLoading && !readinessData ? (
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
                        Загружаем readiness verdict...
                    </div>
                ) : readinessData ? (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Внешний канал</p>
                                <p
                                    className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${readinessChipClass(readinessData.external_channel_ready)}`}
                                    data-testid="business-go-no-go-external-channel"
                                >
                                    {readinessLabel(readinessData.external_channel_ready)}
                                </p>
                                <p className="mt-2 text-xs text-muted-foreground">
                                    Chatflow/WhatsApp должен быть оплачен и доступен для external go-live.
                                </p>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Internal booking</p>
                                <p
                                    className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${readinessChipClass(readinessData.internal_booking_ready)}`}
                                    data-testid="business-go-no-go-internal-booking"
                                >
                                    {readinessLabel(readinessData.internal_booking_ready)}
                                </p>
                                <p className="mt-2 text-xs text-muted-foreground">
                                    Internal Console Calendar не зависит от WhatsApp и Google Calendar.
                                </p>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Data trust</p>
                                <p
                                    className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${readinessChipClass(readinessData.data_trust_ready)}`}
                                    data-testid="business-go-no-go-data-trust"
                                >
                                    {readinessLabel(readinessData.data_trust_ready)}
                                </p>
                                <p className="mt-2 text-xs text-muted-foreground">
                                    Данные и знания должны быть достаточно свежими для запуска.
                                </p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                                <div className="flex items-center justify-between gap-2">
                                    <h3 className="text-sm font-semibold">Blockers</h3>
                                    <span className="text-xs text-muted-foreground">{readinessData.blockers.length} шт.</span>
                                </div>
                                {readinessData.blockers.length ? (
                                    <div className="mt-3 space-y-2" data-testid="business-go-no-go-blockers">
                                        {readinessData.blockers.slice(0, 6).map((blocker) => (
                                            <article key={`${blocker.category}:${blocker.code}`} className="rounded-md border border-red-200/80 bg-red-50 p-2 text-red-950">
                                                <div className="flex flex-wrap items-center justify-between gap-2">
                                                    <p className="text-sm font-semibold">{blocker.code}</p>
                                                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-800">
                                                        {findingCategoryLabel(blocker.category)}
                                                    </span>
                                                </div>
                                                <p className="mt-1 text-xs">{blocker.detail}</p>
                                                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                                                    {blocker.owner_lane ? <span>owner: {blocker.owner_lane}</span> : null}
                                                    {blocker.href ? <Link href={blocker.href} className="btn-ghost text-xs">Открыть</Link> : null}
                                                </div>
                                            </article>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="mt-2 text-sm text-muted-foreground">Обязательных blockers нет.</p>
                                )}
                            </div>

                            <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                                <div className="flex items-center justify-between gap-2">
                                    <h3 className="text-sm font-semibold">Evidence</h3>
                                    <span className="text-xs text-muted-foreground">{readinessData.evidence.length} sources</span>
                                </div>
                                <div className="mt-3 space-y-2" data-testid="business-go-no-go-evidence">
                                    {readinessData.evidence.map((item) => (
                                        <article key={item.id} className="rounded-md border border-border/60 bg-background p-2">
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <p className="text-sm font-semibold">{item.id}</p>
                                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${evidenceChipClass(item.status)}`}>
                                                    {item.status}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-xs text-muted-foreground">{item.summary}</p>
                                            <p className="mt-1 text-[10px] text-muted-foreground">source: {item.source}</p>
                                        </article>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {readinessData.actions.length ? (
                            <div className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid="business-go-no-go-actions">
                                <div className="mb-2 flex items-center justify-between gap-2">
                                    <h3 className="text-sm font-semibold">Следующие действия</h3>
                                    <span className="text-xs text-muted-foreground">{readinessData.actions.length} шт.</span>
                                </div>
                                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                                    {readinessData.actions.slice(0, 4).map((action) => (
                                        <article key={action.id} className="rounded-md border border-border/60 bg-background p-2">
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <p className="text-sm font-semibold">{action.title}</p>
                                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${actionChipClass(action.severity)}`}>
                                                    {severityLabel(action.severity)}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-xs text-muted-foreground">{action.description}</p>
                                            <div className="mt-2">
                                                <Link href={action.href} className="btn-ghost text-xs">Открыть действие</Link>
                                            </div>
                                        </article>
                                    ))}
                                </div>
                            </div>
                        ) : null}
                    </div>
                ) : null}
            </section>

            {billingBlockedIncident && (
                <section
                    className="mb-4 rounded-xl border border-red-300/80 bg-red-50 p-4 text-red-900"
                    data-testid="business-billing-incident-banner"
                >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold">Отправка клиентам заблокирована у провайдера</p>
                        <span className="rounded-full bg-red-200/80 px-2 py-0.5 text-[10px] font-semibold uppercase">
                            p0
                        </span>
                    </div>
                    <p className="mt-1 text-xs">{billingBlockedIncident.reason_label}</p>
                    <p className="mt-1 text-xs">{billingBlockedIncident.summary}</p>
                    {billingBlockedContract && (
                        <p className="mt-1 text-xs">
                            {billingBlockedContract.businessImpact}
                        </p>
                    )}
                    <ol className="mt-2 space-y-1 text-[11px]" data-testid="business-billing-incident-runbook">
                        {(billingBlockedContract?.runbook ?? [
                            "Откройте Подписку и проверьте оплату/лимиты провайдера.",
                            "Откройте Интеграции и проверьте `paid_until`, `next_renewal_at`, `webhook_status`.",
                            "После исправления запустите dry-run outbox и проверьте, что `failed` не растет.",
                        ]).map((step, index) => (
                            <li key={step}>{index + 1}. {step}</li>
                        ))}
                    </ol>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {billingIncidentLinks.length > 0 ? (
                            billingIncidentLinks.map((action) => (
                                <Link key={action.id} href={action.href ?? "/subscription"} className="btn-ghost text-xs">
                                    {action.title}
                                </Link>
                            ))
                        ) : (
                            <>
                                <Link href="/subscription" className="btn-ghost text-xs">Открыть подписку</Link>
                                <Link href="/integrations" className="btn-ghost text-xs">Открыть интеграции</Link>
                                <Link href="/ops" className="btn-ghost text-xs">Открыть статус</Link>
                            </>
                        )}
                    </div>
                </section>
            )}

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="business-today-plan">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">Что делать сейчас</h2>
                        <p className="text-sm text-muted-foreground">Короткий план для владельца: максимум 3 шага.</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{todaySteps.length} шага</span>
                </div>
                <div className="space-y-2">
                    {todaySteps.map((step, index) => (
                        <article
                            key={step.id}
                            className="rounded-lg border border-border/60 bg-muted/20 p-3"
                            data-testid={`business-today-step-${step.id}`}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-foreground">{index + 1}. {step.title}</p>
                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${actionChipClass(step.severity)}`}>
                                    {severityLabel(step.severity)}
                                </span>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">{step.summary}</p>
                            <div className="mt-2">
                                <Link href={step.href} className="btn-ghost text-xs">Открыть шаг</Link>
                            </div>
                        </article>
                    ))}
                </div>
            </section>

            <section className="mb-4 rounded-xl border border-border/60 bg-card p-4" data-testid="business-incidents-card">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Ключевые инциденты</h2>
                    <span className="text-xs text-muted-foreground">{incidentsData?.summary.total ?? 0} шт.</span>
                </div>
                {incidentsLoading ? (
                    <p className="text-sm text-muted-foreground">Проверяем инциденты...</p>
                ) : !incidentsData?.items?.length ? (
                    <p className="text-sm text-muted-foreground">Критичных инцидентов не найдено. Продолжайте ежедневный контроль.</p>
                ) : (
                    <div className="space-y-3">
                        {incidentsData.items.map((incident) => {
                            const providerContract = getProviderErrorContract(incident.reason_code);
                            return (
                                <article key={incident.id} className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid={`business-incident-${incident.id}`}>
                                    {providerContract && (
                                        <p className="mb-2 rounded-md border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground">
                                            {providerContract.shortLabel}. {providerContract.businessImpact}
                                        </p>
                                    )}
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-semibold">{incident.title}</p>
                                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${incidentChipClass(incident.severity)}`}>
                                            {incident.severity}
                                        </span>
                                    </div>
                                    <p className="mt-1 text-xs text-muted-foreground">{incident.reason_label}</p>
                                    <p className="mt-1 text-xs text-muted-foreground">{incident.summary}</p>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {incident.actions.map((action) => (
                                            action.href ? (
                                                <Link key={action.id} href={action.href} className="btn-ghost text-xs">
                                                    {action.title}
                                                </Link>
                                            ) : (
                                                <span key={action.id} className="rounded-full border border-border/60 px-2 py-1 text-[11px] text-muted-foreground">
                                                    {action.title} {action.job_type ? `(${action.job_type}:${action.mode})` : ""}
                                                </span>
                                            )
                                        ))}
                                    </div>
                                </article>
                            );
                        })}
                    </div>
                )}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-3" data-testid="business-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Очередь отправки</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.outbox_backlog}</p>
                    <p className="text-xs text-muted-foreground">failed за 24ч: {data.outbox_failed_24h}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.outbox_backlog)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Неразобранные заявки</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.unresolved_cases}</p>
                    <p className="text-xs text-muted-foreground">pending: {data.pending_cases} · active: {data.active_cases}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.unresolved_cases)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Скорость ответа</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.first_response_p90_seconds)}</p>
                    <p className="text-xs text-muted-foreground">старейшая незавершенная: {formatMinutes(data.oldest_unresolved_minutes)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.first_response_p90_seconds)}</p>
                </div>
            </section>

            <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5" data-testid="business-visit-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Запланировано</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.scheduled_visits_today}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.scheduled_visits_today)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Пришли</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.arrived_visits_today}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.arrived_visits_today)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Не пришли</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.no_show_visits_today}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.no_show_visits_today)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Отменены</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.cancelled_visits_today}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.cancelled_visits_today)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">% прихода</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatPercent(data.arrival_rate_percent)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.arrival_rate_percent)}</p>
                </div>
            </section>

            <section className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2" data-testid="business-ops-followup-kpi-grid">
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Сбои напоминаний сегодня</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.reminder_delivery_failures_today}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.reminder_delivery_failures_today)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Неявки без follow-up</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{data.no_show_followup_pending}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.no_show_followup_pending)}</p>
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

            <section className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3" data-testid="business-wave2-shortcuts">
                <article className="rounded-xl border border-border/60 bg-card p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Контроль качества</p>
                    <h2 className="mt-1 text-lg font-semibold">Надежность данных и рисков</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Проверка полноты quality-метрик, свежести знаний и критичных audit-событий.
                    </p>
                    <div className="mt-3">
                        <Link href="/business/data-trust" className="btn-ghost">Проверить качество данных</Link>
                    </div>
                </article>
                <article className="rounded-xl border border-border/60 bg-card p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Доверие к консультанту</p>
                    <h2 className="mt-1 text-lg font-semibold">Проверка консультанта под давлением</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Подготовьте owner-facing проверку, где можно писать как клиент и искать реальные слабые места.
                    </p>
                    <div className="mt-3">
                        <Link href="/business/consultant-verification" className="btn-ghost">Открыть проверку консультанта</Link>
                    </div>
                </article>
                <article className="rounded-xl border border-border/60 bg-card p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Работа менеджеров</p>
                    <h2 className="mt-1 text-lg font-semibold">Скорость и нагрузка команды</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Контроль скорости первого ответа, просроченных заявок и баланса нагрузки менеджеров.
                    </p>
                    <div className="mt-3">
                        <Link href="/business/team-performance" className="btn-ghost">Открыть показатели команды</Link>
                    </div>
                </article>
            </section>
        </div>
    );
}
