"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useState } from "react";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    authApi,
    businessApi,
    canAccessConsole,
    type MetricFactMeta,
    type OwnerOperationApplyResponse,
} from "@/lib/api-client";

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

function formatMetricMeta(meta?: MetricFactMeta): string {
    if (!meta) {
        return "missing · source: n/a";
    }
    const asOf = meta.as_of ? ` · as_of: ${meta.as_of}` : "";
    return `${meta.kind} · source: ${meta.source}${asOf}`;
}

export default function BusinessTeamPerformancePage() {
    const { data: session } = useSession();
    const [lastOperation, setLastOperation] = useState<OwnerOperationApplyResponse | null>(null);
    const [lastImpactSummary, setLastImpactSummary] = useState<string | null>(null);

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
    const canWriteSettings = canAccessConsole(role, "settings", "write");

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["business-team-performance"],
        queryFn: async () => {
            const response = await businessApi.getTeamPerformanceSummary();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 45000,
    });

    const quickProfileMutation = useMutation({
        mutationFn: async () => {
            const response = await businessApi.applyOwnerModeOperation({ mode: "capture_leads" });
            return response.data;
        },
        onSuccess: (result) => {
            setLastOperation(result);
            setLastImpactSummary(null);
            toast.success("Быстрый профиль применён через server operation");
            refetch();
        },
        onError: () => {
            toast.error("Не удалось применить быстрый профиль");
        },
    });

    const rollbackQuickProfileMutation = useMutation({
        mutationFn: async () => {
            const response = await businessApi.rollbackOwnerModeOperation(
                lastOperation ? { operation_id: lastOperation.operation_id } : undefined,
            );
            return response.data;
        },
        onSuccess: () => {
            setLastOperation(null);
            setLastImpactSummary(null);
            toast.success("Откат выполнен: восстановлен серверный snapshot");
            refetch();
        },
        onError: () => {
            toast.error("Не удалось откатить настройки");
        },
    });

    const impactMutation = useMutation({
        mutationFn: async () => {
            if (!lastOperation?.operation_id) {
                throw new Error("owner_operation_missing");
            }
            const response = await businessApi.getOwnerOperationImpact(lastOperation.operation_id);
            return response.data;
        },
        onSuccess: (impact) => {
            setLastImpactSummary(impact.summary);
            toast.success(`Impact check: ${impact.summary}`);
            refetch();
        },
        onError: () => {
            toast.error("Не удалось проверить эффект операции");
        },
    });

    function applyQuickProfile(): void {
        if (!canWriteSettings) {
            toast.error("Недостаточно прав для изменения настроек");
            return;
        }
        const confirmed = window.confirm(
            "Применить быстрый профиль 5/30/60? Это изменит SLA и эскалацию для текущего клиента.",
        );
        if (!confirmed) {
            return;
        }
        quickProfileMutation.mutate();
    }

    function rollbackQuickProfile(): void {
        if (!canWriteSettings) {
            toast.error("Недостаточно прав для изменения настроек");
            return;
        }
        const confirmed = window.confirm(
            "Откатить последний server-applied режим SLA?",
        );
        if (!confirmed) {
            return;
        }
        rollbackQuickProfileMutation.mutate();
    }

    function checkOperationImpact(): void {
        if (!lastOperation?.operation_id) {
            toast.error("Сначала примените режим, чтобы проверить эффект");
            return;
        }
        impactMutation.mutate();
    }

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
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.unresolved_cases)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Старше 60 минут</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatNumber(data.unresolved_older_than_60m)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.unresolved_older_than_60m)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">Медиана ответа менеджера</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.manager_median_response_seconds)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.manager_median_response_seconds)}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <p className="text-sm text-muted-foreground">P90 первого ответа</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{formatSeconds(data.first_response_p90_seconds)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{formatMetricMeta(data.metric_meta?.first_response_p90_seconds)}</p>
                </div>
            </section>

            {data.status !== "healthy" ? (
                <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="team-performance-quick-profile">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold text-foreground">Быстрый фикс SLA</p>
                            <p className="text-xs text-muted-foreground">
                                Для снижения очереди можно сразу применить профиль 5/30/60.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => {
                                applyQuickProfile();
                            }}
                            disabled={!canWriteSettings || quickProfileMutation.isPending || rollbackQuickProfileMutation.isPending}
                            className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                            data-testid="team-performance-quick-profile-apply"
                        >
                            {quickProfileMutation.isPending ? "Применяю..." : "Применить быстрый профиль"}
                        </button>
                    </div>
                    <div className="mt-3 rounded-lg border border-border/60 bg-muted/20 p-3" data-testid="team-performance-remediation-guide">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Guided remediation</p>
                        <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
                            <li>Примените профиль 5/30/60 для ускорения первого ответа.</li>
                            <li>Через 10-15 минут нажмите «Обновить» и сравните stale cases + медиану ответа.</li>
                            <li>Если динамики нет или стало хуже, выполните откат одним действием.</li>
                        </ol>
                    </div>
                    <div className="mt-3 rounded-lg border border-border/60 bg-background/80 p-3" data-testid="team-performance-quick-profile-rollback-card">
                        {lastOperation ? (
                            <div className="space-y-2">
                                <p className="text-xs text-muted-foreground">
                                    Базовая точка до применения: stale {formatNumber(lastOperation.baseline.unresolved_older_than_60m)}, медиана ответа {formatSeconds(lastOperation.baseline.manager_median_response_seconds)}.
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Применён в {new Date(lastOperation.applied_at).toLocaleString("ru-RU")} (impact due: {new Date(lastOperation.impact_check_due_at).toLocaleString("ru-RU")}).
                                </p>
                                {lastImpactSummary ? (
                                    <p className="text-xs text-foreground">
                                        Последний impact-check: <span className="font-semibold">{lastImpactSummary}</span>
                                    </p>
                                ) : null}
                                <p className="text-xs text-muted-foreground">
                                    Можно откатить к значениям:
                                    {" "}
                                    {lastOperation.previous_settings.reminder_1_minutes}/{lastOperation.previous_settings.reminder_2_minutes}/{lastOperation.previous_settings.escalation_timeout_minutes}.
                                </p>
                                <div className="flex flex-wrap items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            checkOperationImpact();
                                        }}
                                        disabled={impactMutation.isPending}
                                        className="rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                                        data-testid="team-performance-operation-impact"
                                    >
                                        {impactMutation.isPending ? "Проверяю..." : "Проверить эффект"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            rollbackQuickProfile();
                                        }}
                                        disabled={!canWriteSettings || rollbackQuickProfileMutation.isPending}
                                        className="rounded-full border border-border px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                                        data-testid="team-performance-quick-profile-rollback"
                                    >
                                        {rollbackQuickProfileMutation.isPending ? "Откатываю..." : "Откатить к предыдущим настройкам"}
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <p className="text-xs text-muted-foreground" data-testid="team-performance-quick-profile-rollback-empty">
                                Состояние для rollback появится после server-applied режима.
                            </p>
                        )}
                    </div>
                </section>
            ) : null}

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
