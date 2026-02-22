"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { authApi, canAccessConsole, opsApi } from "@/lib/api-client";

type InsightsTrendItem = {
    date?: string | null;
    bot_closed_rate?: number | null;
    booking_conversion_rate?: number | null;
    first_response_p50_seconds?: number | null;
    after_hours_coverage_rate?: number | null;
    escalation_quality_rate?: number | null;
    outbox_failed_total?: number | null;
    no_response_alert_total?: number | null;
};

type InsightsIntentItem = {
    intent: string;
    share?: number | null;
};

type InsightsSectionItem = {
    section: string;
    share?: number | null;
};

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

function formatHoursFromSeconds(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return `${(value / 3600).toFixed(1)} ч`;
}

function formatSeconds(value: number | null | undefined): string {
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

function formatCount(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return value.toLocaleString("ru-RU");
}

function formatPercent(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    return `${(value * 100).toFixed(1)}%`;
}

function getLatestValue(values: Array<number | null | undefined>): number | null {
    for (let index = values.length - 1; index >= 0; index -= 1) {
        const value = values[index];
        if (value === null || value === undefined || Number.isNaN(value)) {
            continue;
        }
        return value;
    }
    return null;
}

function StatusBadge({ status }: { status?: string | null }) {
    if (!status) {
        return null;
    }
    const normalized = status.toLowerCase();
    const styles: Record<string, string> = {
        fact: "bg-emerald-100 text-emerald-800",
        estimate: "bg-amber-100 text-amber-800",
        need: "bg-rose-100 text-rose-800",
    };
    const labels: Record<string, string> = {
        fact: "FACT",
        estimate: "EST",
        need: "NEED",
    };
    return (
        <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
                styles[normalized] ?? "bg-muted text-muted-foreground"
            }`}
            title={status}
        >
            {labels[normalized] ?? status}
        </span>
    );
}

function Sparkline({
    values,
    stroke = "currentColor",
    height = 48,
}: {
    values: Array<number | null | undefined>;
    stroke?: string;
    height?: number;
}) {
    const numericValues = values.filter(
        (value): value is number => value !== null && value !== undefined && !Number.isNaN(value),
    );
    if (numericValues.length < 2) {
        return (
            <div className="h-12 flex items-center justify-center text-xs text-muted-foreground">
                —
            </div>
        );
    }
    const width = 220;
    const padding = 4;
    const minValue = Math.min(...numericValues);
    const maxValue = Math.max(...numericValues);
    const range = maxValue - minValue || 1;
    const points = values
        .map((value, index) => {
            if (value === null || value === undefined || Number.isNaN(value)) {
                return null;
            }
            const x = padding + (index / Math.max(values.length - 1, 1)) * (width - padding * 2);
            const y =
                height -
                padding -
                ((value - minValue) / range) * (height - padding * 2);
            return `${x},${y}`;
        })
        .filter(Boolean)
        .join(" ");
    return (
        <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-12 text-foreground/70"
            role="img"
            aria-label="trend sparkline"
            preserveAspectRatio="none"
        >
            <line
                x1={0}
                y1={height / 2}
                x2={width}
                y2={height / 2}
                stroke="currentColor"
                strokeOpacity={0.15}
                strokeWidth={1}
            />
            <polyline
                points={points}
                fill="none"
                stroke={stroke}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    );
}

function TrendCard({
    label,
    values,
    valueFormatter,
    detail,
    tooltip,
}: {
    label: string;
    values: Array<number | null | undefined>;
    valueFormatter: (value: number | null | undefined) => string;
    detail?: string | null;
    tooltip?: string | null;
}) {
    const latest = getLatestValue(values);
    return (
        <div className="rounded-lg border border-border/60 bg-muted/60 p-3">
            <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    <span>{label}</span>
                    {tooltip ? <InfoTooltip text={tooltip} /> : null}
                </div>
                <div className="text-sm font-semibold text-foreground">
                    {valueFormatter(latest)}
                </div>
            </div>
            <div className="mt-2">
                <Sparkline values={values} />
            </div>
            {detail && <div className="mt-1 text-[11px] text-muted-foreground">{detail}</div>}
        </div>
    );
}

function KpiTile({
    label,
    value,
    status,
    detail,
    hint,
    tooltip,
    children,
}: {
    label: string;
    value?: React.ReactNode;
    status?: string | null;
    detail?: string | null;
    hint?: string | null;
    tooltip?: string | null;
    children?: React.ReactNode;
}) {
    return (
        <div className="bg-muted rounded-lg p-4">
            <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{label}</span>
                    {tooltip ? <InfoTooltip text={tooltip} /> : null}
                </div>
                <StatusBadge status={status} />
            </div>
            {children ?? (
                <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
            )}
            {detail && <div className="text-xs text-muted-foreground mt-1">{detail}</div>}
            {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
        </div>
    );
}

function InfoTooltip({ text }: { text: string }) {
    return (
        <span className="relative inline-flex items-center group">
            <button
                type="button"
                className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-border/60 text-[10px] font-semibold text-muted-foreground transition hover:text-foreground hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                aria-label={text}
            >
                ?
            </button>
            <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-56 -translate-x-1/2 rounded-lg border border-border/60 bg-card px-3 py-2 text-[11px] text-foreground opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
                {text}
            </span>
        </span>
    );
}

const INSIGHTS_TOOLTIPS = {
    clientMessages:
        "Сколько сообщений написали клиенты за день. Показывает активность.",
    botReplies:
        "Сколько ответов дал бот за день. Видно, сколько отвечает автоматика.",
    totalCases:
        "Сколько новых заявок создано за день. Это общий вход в работу.",
    pendingCases:
        "Сколько заявок еще без ответа. Это текущая очередь.",
    activeCases:
        "Сколько заявок сейчас в работе у менеджера.",
    resolvedCases:
        "Сколько заявок завершено за день.",
    avgResolution:
        "Среднее время от создания заявки до завершения.",
    botClosed:
        "Доля диалогов, где бот ответил и менеджер не подключался.",
    managerTimeSaved:
        "Примерная экономия времени за счет ответов бота.",
    bookingConversion:
        "Доля диалогов, которые закончились записью.",
    firstResponse:
        "Как быстро отвечаем: обычно / почти всегда.",
    firstResponseP50:
        "Как быстро отвечаем обычно.",
    afterHours:
        "Доля обращений вне рабочего времени, где бот ответил быстро.",
    escalationQuality:
        "Доля заявок с полными данными клиента и услугой.",
    lossRisk:
        "Сколько сообщений не доставилось или остались без ответа.",
    topThemes:
        "О чем клиенты спрашивают чаще всего.",
} as const;

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
        return <AccessDenied message="Эта роль не имеет доступа к аналитике." />;
    }

    const reportDate = formatMetricDate(metrics?.date ?? selectedDate);
    const topIntents: InsightsIntentItem[] = metrics?.top_intents ?? [];
    const topSections: InsightsSectionItem[] = metrics?.top_info_sections ?? [];
    const analyticsTrend: InsightsTrendItem[] = metrics?.analytics_trend ?? [];
    const trendRangeLabel = analyticsTrend.length
        ? `${formatMetricDate(analyticsTrend[0].date)} – ${formatMetricDate(
            analyticsTrend[analyticsTrend.length - 1].date,
        )}`
        : "—";

    const botClosedTrend = analyticsTrend.map((item) => item.bot_closed_rate ?? null);
    const bookingTrend = analyticsTrend.map((item) => item.booking_conversion_rate ?? null);
    const responseTrend = analyticsTrend.map((item) => item.first_response_p50_seconds ?? null);
    const afterHoursTrend = analyticsTrend.map((item) => item.after_hours_coverage_rate ?? null);
    const escalationTrend = analyticsTrend.map((item) => item.escalation_quality_rate ?? null);
    const outboxFailedTrend = analyticsTrend.map((item) => item.outbox_failed_total ?? null);
    const noResponseTrend = analyticsTrend.map((item) => item.no_response_alert_total ?? null);
    const lossTrend = analyticsTrend.map((item) => {
        const failed = item.outbox_failed_total;
        const noResponse = item.no_response_alert_total;
        if (failed === null && noResponse === null) {
            return null;
        }
        return (failed ?? 0) + (noResponse ?? 0);
    });

    const botClosedDetail = metrics?.bot_closed_sessions !== undefined
        ? `${formatCount(metrics?.bot_closed_sessions)} из ${formatCount(metrics?.bot_closed_total_sessions)}`
        : null;
    const botClosedHint = metrics?.bot_closed_incomplete_total
        ? `Окно 24ч ещё не закрыто: ${formatCount(metrics?.bot_closed_incomplete_total)}`
        : null;

    const bookingDetail = metrics?.booking_attributed !== undefined
        ? `Записи: ${formatCount(metrics?.booking_attributed)} из ${formatCount(
            metrics?.inbound_conversations_total,
        )}`
        : null;
    const bookingHint = metrics?.booking_missing_conversation_total
        ? `Нет связи booking→conversation: ${formatCount(metrics?.booking_missing_conversation_total)}`
        : null;

    const responseDetail = metrics?.first_response_missing_total
        ? `Без ответа: ${formatCount(metrics?.first_response_missing_total)}`
        : null;

    const afterHoursDetail = metrics?.after_hours_covered !== undefined
        ? `Покрыто: ${formatCount(metrics?.after_hours_covered)} из ${formatCount(
            metrics?.after_hours_total,
        )}`
        : null;
    const afterHoursHint = metrics?.after_hours_missing_total
        ? `Нет TZ/графика: ${formatCount(metrics?.after_hours_missing_total)}`
        : null;

    const escalationDetail = metrics?.escalation_quality_total !== undefined
        ? `Слоты: ${formatCount(metrics?.escalation_quality_total)} из ${formatCount(
            metrics?.escalation_total,
        )}`
        : null;
    const escalationHint = metrics?.escalation_meta_missing_total
        ? `Нет snapshot: ${formatCount(metrics?.escalation_meta_missing_total)}`
        : null;

    const lossDetail = metrics?.outbox_saved_total
        ? `Спасено ~ ${formatCount(metrics?.outbox_saved_total)}`
        : null;
    const lossTrendDetail = analyticsTrend.length
        ? `${formatCount(getLatestValue(outboxFailedTrend))} failed / ${formatCount(
            getLatestValue(noResponseTrend),
        )} no_response`
        : null;

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="insights-page">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold mb-1" data-testid="insights-title">Аналитика</h1>
                    <p className="text-sm text-muted-foreground">
                        Ежедневная сводка по сообщениям, заявкам и KPI.
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
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 animate-pulse">
                        {[...Array(4)].map((_, index) => (
                            <div key={`kpi-${index}`} className="h-32 bg-muted/70 rounded-lg"></div>
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
                        <KpiTile
                            label="Сообщений от клиентов"
                            value={formatCount(metrics?.total_client_messages)}
                            tooltip={INSIGHTS_TOOLTIPS.clientMessages}
                        />
                        <KpiTile
                            label="Ответов бота"
                            value={formatCount(metrics?.total_bot_messages)}
                            tooltip={INSIGHTS_TOOLTIPS.botReplies}
                        />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                        <KpiTile
                            label="Всего заявок"
                            value={metrics?.total_cases ?? 0}
                            tooltip={INSIGHTS_TOOLTIPS.totalCases}
                        />
                        <KpiTile
                            label="Ожидают ответа"
                            value={metrics?.pending_cases ?? 0}
                            tooltip={INSIGHTS_TOOLTIPS.pendingCases}
                        />
                        <KpiTile
                            label="В работе"
                            value={metrics?.active_cases ?? 0}
                            tooltip={INSIGHTS_TOOLTIPS.activeCases}
                        />
                        <KpiTile
                            label="Закрыты"
                            value={metrics?.resolved_cases ?? 0}
                            tooltip={INSIGHTS_TOOLTIPS.resolvedCases}
                        />
                        <KpiTile
                            label="Среднее время"
                            value={formatHours(metrics?.avg_resolution_hours)}
                            tooltip={INSIGHTS_TOOLTIPS.avgResolution}
                        />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <KpiTile
                            label="Закрыты без человека"
                            value={formatPercent(metrics?.bot_closed_rate)}
                            status={metrics?.bot_closed_status}
                            detail={botClosedDetail}
                            hint={botClosedHint}
                            tooltip={INSIGHTS_TOOLTIPS.botClosed}
                        />
                        <KpiTile
                            label="Экономия времени менеджера"
                            value={formatHoursFromSeconds(metrics?.manager_time_saved_seconds_estimate)}
                            status={metrics?.manager_time_saved_status}
                            detail={`Медиана ответа: ${formatSeconds(metrics?.manager_median_response_seconds)}`}
                            hint="Оценка на основе медианы ручных ответов"
                            tooltip={INSIGHTS_TOOLTIPS.managerTimeSaved}
                        />
                        <KpiTile
                            label="Конверсия в запись"
                            value={formatPercent(metrics?.booking_conversion_rate)}
                            status={metrics?.booking_status}
                            detail={bookingDetail}
                            hint={bookingHint}
                            tooltip={INSIGHTS_TOOLTIPS.bookingConversion}
                        />
                        <KpiTile
                            label="Время до первого ответа (p50/p90)"
                            value={`${formatSeconds(metrics?.first_response_p50_seconds)} / ${formatSeconds(
                                metrics?.first_response_p90_seconds,
                            )}`}
                            status={metrics?.first_response_status}
                            detail={responseDetail}
                            tooltip={INSIGHTS_TOOLTIPS.firstResponse}
                        />
                        <KpiTile
                            label="После-часов покрытие"
                            value={formatPercent(metrics?.after_hours_coverage_rate)}
                            status={metrics?.after_hours_status}
                            detail={afterHoursDetail}
                            hint={afterHoursHint}
                            tooltip={INSIGHTS_TOOLTIPS.afterHours}
                        />
                        <KpiTile
                            label="Качество эскалаций"
                            value={formatPercent(metrics?.escalation_quality_rate)}
                            status={metrics?.escalation_quality_status}
                            detail={escalationDetail}
                            hint={escalationHint}
                            tooltip={INSIGHTS_TOOLTIPS.escalationQuality}
                        />
                        <KpiTile
                            label="Потери / риски"
                            value={`${formatCount(metrics?.outbox_failed_total)} / ${formatCount(
                                metrics?.no_response_alert_total,
                            )}`}
                            status={metrics?.loss_risk_status}
                            detail={lossDetail}
                            hint="FAILED / no_response за день"
                            tooltip={INSIGHTS_TOOLTIPS.lossRisk}
                        />
                        <KpiTile
                            label="Топ темы и боли"
                            status={metrics?.top_intents_status}
                            detail={metrics?.intent_missing_total ? `Без intent: ${formatCount(metrics?.intent_missing_total)}` : null}
                            tooltip={INSIGHTS_TOOLTIPS.topThemes}
                        >
                            <div className="mt-2 grid gap-3 md:grid-cols-2">
                                <div>
                                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Интенты</div>
                                    {topIntents.length ? (
                                        <div className="mt-1 space-y-1 text-xs text-foreground">
                                            {topIntents.slice(0, 3).map((item) => (
                                                <div key={item.intent} className="flex items-center justify-between gap-2">
                                                    <span className="truncate">{item.intent}</span>
                                                    <span className="text-muted-foreground">
                                                        {formatPercent(item.share)}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="mt-1 text-xs text-muted-foreground">—</div>
                                    )}
                                </div>
                                <div>
                                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Инфо</div>
                                    {topSections.length ? (
                                        <div className="mt-1 space-y-1 text-xs text-foreground">
                                            {topSections.slice(0, 3).map((item) => (
                                                <div key={item.section} className="flex items-center justify-between gap-2">
                                                    <span className="truncate">{item.section}</span>
                                                    <span className="text-muted-foreground">
                                                        {formatPercent(item.share)}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="mt-1 text-xs text-muted-foreground">—</div>
                                    )}
                                </div>
                            </div>
                        </KpiTile>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-card p-4">
                        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                            <div>
                                <div className="text-sm font-semibold text-foreground">Тренды KPI</div>
                                <div className="text-xs text-muted-foreground">
                                    Диапазон: {trendRangeLabel}
                                </div>
                            </div>
                            <div className="text-xs text-muted-foreground">
                                Источник: daily snapshot (7 дней)
                            </div>
                        </div>
                        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                            <TrendCard
                                label="Закрыты без человека"
                                values={botClosedTrend}
                                valueFormatter={formatPercent}
                                tooltip={INSIGHTS_TOOLTIPS.botClosed}
                            />
                            <TrendCard
                                label="Конверсия в запись"
                                values={bookingTrend}
                                valueFormatter={formatPercent}
                                tooltip={INSIGHTS_TOOLTIPS.bookingConversion}
                            />
                            <TrendCard
                                label="Ответ p50"
                                values={responseTrend}
                                valueFormatter={formatSeconds}
                                tooltip={INSIGHTS_TOOLTIPS.firstResponseP50}
                            />
                            <TrendCard
                                label="После-часов покрытие"
                                values={afterHoursTrend}
                                valueFormatter={formatPercent}
                                tooltip={INSIGHTS_TOOLTIPS.afterHours}
                            />
                            <TrendCard
                                label="Качество эскалаций"
                                values={escalationTrend}
                                valueFormatter={formatPercent}
                                tooltip={INSIGHTS_TOOLTIPS.escalationQuality}
                            />
                            <TrendCard
                                label="Потери/риски"
                                values={lossTrend}
                                valueFormatter={formatCount}
                                detail={lossTrendDetail}
                                tooltip={INSIGHTS_TOOLTIPS.lossRisk}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
