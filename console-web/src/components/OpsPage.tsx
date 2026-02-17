"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import {
    adminApi,
    authApi,
    canAccessConsole,
    opsApi,
    telegramApi,
    type OpsJobRunRequest,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";
import AccessDenied from "@/components/AccessDenied";
import { ConsolePageSkeleton } from "@/components/PageStates";
import { getProviderErrorContract } from "@/lib/provider-error-contract";
import { QUERY_PROFILE_CONTEXT, QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

interface HealthData {
    status: string;
    version: string;
    database: string;
    redis: string;
    outbox_backlog: number;
}

interface MetricsData {
    date: string;
    total_cases: number;
    pending_cases: number;
    active_cases: number;
    resolved_cases: number;
    avg_resolution_hours: number | null;
}

// TG-03: Telegram Health
interface TelegramHealthData {
    status: string;  // ok, degraded, error
    webhook_alive: boolean;
    last_success_at: string | null;
    last_error_at: string | null;
    last_error_message: string | null;
    error_rate_24h: number;
    pending_messages: number;
}

type OutboxStatusFilter = "failed" | "pending" | "processing" | "all";

interface OutboxCounts {
    pending: number;
    processing: number;
    failed: number;
}

interface OutboxItem {
    id: string;
    status: string;
    attempts: number;
    next_attempt_at: string | null;
    last_error: string | null;
    created_at: string;
    updated_at: string;
    conversation_id: string | null;
    branch_id: string | null;
    inbound_message_id: string;
    channel: string | null;
    message_type: string | null;
    message_preview: string | null;
    remote_jid: string | null;
    instance_id: string | null;
    forwarded_to_telegram: boolean | null;
}

interface OutboxListResponse {
    items: OutboxItem[];
    cursor: string | null;
    has_more: boolean;
    counts: OutboxCounts;
}

interface OutboxRetryResponse {
    success: boolean;
    retried: number;
    skipped: number;
}

type OpsJobType = OpsJobRunRequest["job_type"];
type OpsJobMode = OpsJobRunRequest["mode"];

interface OpsJobDefinition {
    job_type: OpsJobType;
    label: string;
    description: string;
    supports_dry_run: boolean;
}

interface OpsJobCatalogResponse {
    items: OpsJobDefinition[];
}

interface OpsJobRecord {
    id: string;
    job_type: OpsJobType;
    mode: OpsJobMode;
    status: "success" | "failed";
    created_at: string;
    finished_at: string | null;
    error_message: string | null;
    request_payload: Record<string, unknown> | null;
    result_payload: Record<string, unknown> | null;
}

interface OpsJobListResponse {
    items: OpsJobRecord[];
    cursor: string | null;
    has_more: boolean;
}

interface OpsJobRunResponse {
    job: OpsJobRecord;
}

async function fetchHealth(): Promise<HealthData> {
    const response = await api.get("/health");
    return response.data;
}

async function fetchMetrics(): Promise<MetricsData> {
    const response = await api.get("/metrics/daily");
    return response.data;
}

async function fetchTelegramHealth(): Promise<TelegramHealthData> {
    const response = await api.get("/telegram/health");
    return response.data;
}

async function fetchOutbox(status: OutboxStatusFilter): Promise<OutboxListResponse> {
    const response = await api.get("/ops/outbox", {
        params: {
            status,
            limit: 50,
        },
    });
    return response.data;
}

import { getSystemStatusLabel } from "@/utils/labels";

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        ok: "bg-green-100 text-green-800",
        connected: "bg-green-100 text-green-800",
        degraded: "bg-yellow-100 text-yellow-800",
        error: "bg-red-100 text-red-800",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || "bg-muted text-muted-foreground"}`}>
            {getSystemStatusLabel(status)}
        </span>
    );
}

function MetricCard({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) {
    return (
        <div className="bg-muted rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-foreground">{value}</div>
            <div className="text-sm text-muted-foreground">{label}</div>
            {subtext && <div className="text-xs text-muted-foreground mt-1">{subtext}</div>}
        </div>
    );
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

function incidentSeverityLabel(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "critical";
    }
    if (severity === "warn") {
        return "warn";
    }
    return "info";
}

function formatJsonPreview(payload: Record<string, unknown> | null, limit = 160): string {
    if (!payload) {
        return "—";
    }
    const raw = JSON.stringify(payload);
    if (!raw) {
        return "—";
    }
    if (raw.length <= limit) {
        return raw;
    }
    return `${raw.slice(0, limit - 3)}...`;
}

export default function OpsPage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();
    const [telegramAction, setTelegramAction] = useState<"verify" | "test" | null>(null);
    const [outboxStatus, setOutboxStatus] = useState<OutboxStatusFilter>("failed");
    const [jobType, setJobType] = useState<OpsJobType>("outbox_process");
    const [outboxProcessLimit, setOutboxProcessLimit] = useState<number>(10);
    const [integrationReconcileLimit, setIntegrationReconcileLimit] = useState<number>(25);
    const [integrationReconcileBranchIds, setIntegrationReconcileBranchIds] = useState<string>("");
    const [metricsSnapshotDays, setMetricsSnapshotDays] = useState<number>(1);
    const [metricsSnapshotDate, setMetricsSnapshotDate] = useState<string>("");

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
    const canReadOps = canAccessConsole(role, "ops", "read");
    const canWriteOps = canAccessConsole(role, "ops", "write");
    const canWriteSettings = canAccessConsole(role, "settings", "write");
    const isFullOps = role === "platform_admin";

    const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
        queryKey: ["health"],
        queryFn: fetchHealth,
        enabled: !!session && canReadOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery({
        queryKey: ["metrics-daily"],
        queryFn: fetchMetrics,
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 60000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    // TG-03: Telegram Health
    const { data: telegramHealth, isLoading: telegramLoading } = useQuery({
        queryKey: ["telegram-health"],
        queryFn: fetchTelegramHealth,
        enabled: !!session && canReadOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: outboxData, isLoading: outboxLoading, error: outboxError, refetch: refetchOutbox } = useQuery({
        queryKey: ["ops-outbox", outboxStatus],
        queryFn: () => fetchOutbox(outboxStatus),
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: opsJobsCatalog } = useQuery({
        queryKey: ["ops-jobs-catalog"],
        queryFn: async () => {
            const response = await opsApi.getJobsCatalog();
            return response.data as OpsJobCatalogResponse;
        },
        enabled: !!session && canReadOps && isFullOps,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: opsJobs, isLoading: opsJobsLoading, error: opsJobsError, refetch: refetchOpsJobs } = useQuery({
        queryKey: ["ops-jobs"],
        queryFn: async () => {
            const response = await opsApi.listJobs({ limit: 20 });
            return response.data as OpsJobListResponse;
        },
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const {
        data: incidentsData,
        isLoading: incidentsLoading,
        error: incidentsError,
        refetch: refetchIncidents,
    } = useQuery({
        queryKey: ["admin-incidents"],
        queryFn: async () => {
            const response = await adminApi.listIncidents({ limit: 20 });
            return response.data;
        },
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    useEffect(() => {
        if (outboxError) {
            handleError(outboxError);
        }
    }, [outboxError, handleError]);

    useEffect(() => {
        if (opsJobsError) {
            handleError(opsJobsError);
        }
    }, [opsJobsError, handleError]);

    useEffect(() => {
        if (incidentsError) {
            handleError(incidentsError);
        }
    }, [incidentsError, handleError]);

    const telegramVerify = useMutation({
        mutationFn: async () => {
            const { data } = await telegramApi.verify({ scope: "client" });
            return data;
        },
        onMutate: () => {
            setTelegramAction("verify");
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success(`Код верификации: ${data.verification_code}`);
            } else {
                toast.error(data.error_message || "Не удалось отправить код");
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTelegramAction(null);
        },
    });

    const telegramTest = useMutation({
        mutationFn: async () => {
            const { data } = await telegramApi.test({ scope: "client" });
            return data;
        },
        onMutate: () => {
            setTelegramAction("test");
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success("Тестовое сообщение отправлено");
            } else {
                toast.error(data.error_message || "Не удалось отправить тест");
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTelegramAction(null);
        },
    });

    const outboxRetry = useMutation({
        mutationFn: async (ids?: string[]) => {
            const { data } = await api.post<OutboxRetryResponse>("/ops/outbox/retry", {
                ids: ids && ids.length > 0 ? ids : undefined,
                limit: 100,
            });
            return data;
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success(`Ретрай: ${data.retried} сообщений`);
            } else {
                toast.error("Не удалось ретраить сообщения");
            }
            refetchOutbox();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const runOpsJob = useMutation({
        mutationFn: async (payload: OpsJobRunRequest) => {
            const response = await opsApi.runJob(payload);
            return response.data as OpsJobRunResponse;
        },
        onSuccess: (data) => {
            if (data.job.status === "success") {
                toast.success(`Job ${data.job.job_type} выполнен`);
            } else {
                toast.error(data.job.error_message || `Job ${data.job.job_type} завершился с ошибкой`);
            }
            refetchOpsJobs();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const outboxCounts = useMemo(() => {
        const pending = outboxData?.counts?.pending ?? 0;
        const processing = outboxData?.counts?.processing ?? 0;
        const failed = outboxData?.counts?.failed ?? 0;
        return {
            pending,
            processing,
            failed,
            total: pending + processing + failed,
        };
    }, [outboxData]);

    const selectedJob = useMemo(
        () => opsJobsCatalog?.items?.find((item) => item.job_type === jobType) ?? null,
        [opsJobsCatalog, jobType],
    );

    const buildRunJobPayload = (mode: OpsJobMode): OpsJobRunRequest => {
        const params: Record<string, unknown> = {};
        if (jobType === "outbox_process") {
            params.limit = Math.max(1, outboxProcessLimit);
        }
        if (jobType === "integration_reconcile") {
            params.limit = Math.max(1, integrationReconcileLimit);
            const branchIds = integrationReconcileBranchIds
                .split(/[\s,]+/)
                .map((item) => item.trim())
                .filter((item) => item.length > 0);
            if (branchIds.length > 0) {
                params.branch_ids = branchIds;
            }
        }
        if (jobType === "metrics_snapshot") {
            params.days = Math.max(1, metricsSnapshotDays);
            if (metricsSnapshotDate) {
                params.metric_date = metricsSnapshotDate;
            }
        }
        return {
            job_type: jobType,
            mode,
            params,
        };
    };

    const isLoading = healthLoading || (isFullOps && metricsLoading) || (!isFullOps && telegramLoading);

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра статуса.
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

    if (!canReadOps) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к Ops." />
        );
    }

    if (isLoading) {
        return (
            <ConsolePageSkeleton
                pageTestId="ops-page"
                title="Статус системы"
                titleTestId="ops-title"
                columns={1}
                cardCount={2}
                cardHeightClass="h-32"
                maxWidthClass="max-w-4xl"
            />
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6" data-testid="ops-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="ops-title">Статус системы</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">Авто-обновление: 30с</span>
                    <button
                        onClick={() => {
                            void refetchHealth();
                            if (isFullOps) {
                                void refetchIncidents();
                            }
                        }}
                        className="text-sm text-primary hover:text-primary/80"
                    >
                        Обновить
                    </button>
                </div>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-incidents-card">
                    <div className="mb-4 flex items-center justify-between">
                        <div>
                            <h2 className="text-lg font-semibold">Критичные инциденты</h2>
                            <p className="text-xs text-muted-foreground">
                                Только факт-основанные причины и безопасные шаги (`dry-run` сначала).
                            </p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                            {incidentsData?.summary.total ?? 0} шт.
                        </span>
                    </div>
                    <div className="mb-4 grid grid-cols-3 gap-3">
                        <MetricCard label="Critical" value={incidentsData?.summary.critical ?? 0} />
                        <MetricCard label="Warn" value={incidentsData?.summary.warn ?? 0} />
                        <MetricCard label="Info" value={incidentsData?.summary.info ?? 0} />
                    </div>
                    {incidentsLoading ? (
                        <p className="text-sm text-muted-foreground">Загрузка инцидентов...</p>
                    ) : !incidentsData?.items?.length ? (
                        <p className="text-sm text-muted-foreground">Критичных инцидентов не обнаружено.</p>
                    ) : (
                        <div className="space-y-3">
                            {incidentsData.items.map((item) => {
                                const providerContract = getProviderErrorContract(item.reason_code);
                                return (
                                    <article
                                        key={item.id}
                                        className="rounded-lg border border-border/60 bg-muted/20 p-3"
                                        data-testid={`ops-incident-${item.id}`}
                                    >
                                        {providerContract && (
                                            <div className="mb-2 rounded-md border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground">
                                                <p className="font-semibold text-foreground">{providerContract.shortLabel}</p>
                                                <p className="mt-0.5">{providerContract.operatorMeaning}</p>
                                            </div>
                                        )}
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <p className="text-sm font-semibold">{item.title}</p>
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${incidentChipClass(item.severity)}`}>
                                                {incidentSeverityLabel(item.severity)}
                                            </span>
                                        </div>
                                        <p className="mt-1 text-xs text-muted-foreground">{item.reason_label}</p>
                                        <p className="mt-1 text-xs text-muted-foreground">{item.summary}</p>
                                        <p className="mt-1 text-[11px] text-muted-foreground">
                                            client: {item.client_slug || "n/a"} · detected: {new Date(item.detected_at).toLocaleString("ru-RU")}
                                        </p>
                                        {providerContract && (
                                            <ol className="mt-2 list-decimal space-y-0.5 pl-4 text-[11px] text-muted-foreground" data-testid={`ops-provider-runbook-${item.id}`}>
                                                {providerContract.runbook.map((step) => (
                                                    <li key={step}>{step}</li>
                                                ))}
                                            </ol>
                                        )}
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {item.actions.map((action) => (
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
                </div>
            )}

            {!isFullOps && (
                <div className="mb-6 rounded-lg border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground" data-testid="ops-short-note">
                    Краткий статус. Полный Ops доступен только platform admin.
                    {health?.status && health.status !== "ok" ? " Есть деградации — обратитесь к platform admin." : ""}
                </div>
            )}

            {/* Overall Health */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-health-card">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Общее состояние</h2>
                    <StatusBadge status={health?.status || "unknown"} />
                </div>
                <p className="text-sm text-muted-foreground">
                    Версия: <span className="font-mono">{health?.version || "неизвестно"}</span>
                </p>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-metrics-card">
                    <h2 className="text-lg font-semibold mb-4">
                        Метрики за сегодня
                        <span className="text-sm font-normal text-muted-foreground ml-2">
                            ({metrics?.date || "сегодня"})
                        </span>
                    </h2>
                    {metricsError ? (
                        <div className="text-sm text-muted-foreground text-center py-4">
                            Не удалось загрузить метрики
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <MetricCard label="Всего заявок" value={metrics?.total_cases ?? 0} />
                            <MetricCard label="Ожидает" value={metrics?.pending_cases ?? 0} />
                            <MetricCard label="В работе" value={metrics?.active_cases ?? 0} />
                            <MetricCard
                                label="Закрыто"
                                value={metrics?.resolved_cases ?? 0}
                                subtext={metrics?.avg_resolution_hours ? `Средн: ${metrics.avg_resolution_hours}ч` : undefined}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Components */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Компоненты</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-3 bg-muted rounded">
                        <span className="text-sm font-medium">База данных</span>
                        <StatusBadge status={health?.database || "unknown"} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted rounded">
                        <span className="text-sm font-medium">Redis</span>
                        <StatusBadge status={health?.redis || "unknown"} />
                    </div>
                </div>
            </div>

            {/* TG-03: Telegram Health */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-telegram-card">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        📨 Telegram
                    </h2>
                    <StatusBadge status={telegramHealth?.status || "unknown"} />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${telegramHealth?.webhook_alive ? "text-green-600" : "text-red-600"}`}>
                            {telegramHealth?.webhook_alive ? "✓" : "✗"}
                        </div>
                        <div className="text-xs text-muted-foreground">Webhook</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${(telegramHealth?.error_rate_24h || 0) > 0.1 ? "text-red-600" : "text-green-600"}`}>
                            {((telegramHealth?.error_rate_24h || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Ошибки 24ч</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${(telegramHealth?.pending_messages || 0) > 5 ? "text-yellow-600" : "text-foreground"}`}>
                            {telegramHealth?.pending_messages ?? 0}
                        </div>
                        <div className="text-xs text-muted-foreground">В ожидании</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className="text-xs text-foreground">
                            {telegramHealth?.last_success_at
                                ? new Date(telegramHealth.last_success_at).toLocaleTimeString("ru-RU")
                                : "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">Посл. успех</div>
                    </div>
                </div>
                {telegramHealth?.last_error_message && (
                    <div className="mt-3 p-2 bg-destructive/10 rounded text-xs text-destructive">
                        ⚠️ {telegramHealth.last_error_message}
                    </div>
                )}
                <div className="mt-4 flex items-center gap-2">
                    <button
                        type="button"
                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => telegramVerify.mutate()}
                        disabled={telegramAction !== null || !canWriteSettings}
                        data-testid="ops-telegram-verify"
                    >
                        {telegramAction === "verify" ? "Отправка..." : "Verify"}
                    </button>
                    <button
                        type="button"
                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => telegramTest.mutate()}
                        disabled={telegramAction !== null || !canWriteSettings}
                        data-testid="ops-telegram-test"
                    >
                        {telegramAction === "test" ? "Отправка..." : "Send test"}
                    </button>
                    {!canWriteSettings && (
                        <span className="text-xs text-muted-foreground">Только owner/admin/platform admin</span>
                    )}
                </div>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-queue-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Очередь сообщений</h2>
                        <span
                            className={`text-2xl font-bold ${(health?.outbox_backlog || 0) > 100
                            ? "text-red-600"
                            : (health?.outbox_backlog || 0) > 10
                                ? "text-yellow-600"
                                : "text-green-600"
                            }`}
                            data-testid="ops-queue-count"
                        >
                            {health?.outbox_backlog ?? 0}
                        </span>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
                        {([
                            { value: "failed", label: "Failed", count: outboxCounts.failed },
                            { value: "pending", label: "Pending", count: outboxCounts.pending },
                            { value: "processing", label: "Processing", count: outboxCounts.processing },
                            { value: "all", label: "All", count: outboxCounts.total },
                        ] as const).map((item) => (
                            <button
                                key={item.value}
                                type="button"
                                onClick={() => setOutboxStatus(item.value)}
                                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                                    outboxStatus === item.value
                                        ? "border-primary text-primary"
                                        : "border-border/60 text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                {item.label} · {item.count}
                            </button>
                        ))}
                        {outboxStatus === "failed" && (
                            <button
                                type="button"
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                onClick={() => outboxRetry.mutate(undefined)}
                                disabled={outboxRetry.isPending || !canWriteOps}
                            >
                                {outboxRetry.isPending ? "Ретрай..." : "Retry failed"}
                            </button>
                        )}
                        {!canWriteOps && (
                            <span className="text-xs text-muted-foreground">Ретрай доступен только owner/admin/platform admin</span>
                        )}
                    </div>
                    {outboxLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка...</div>
                    ) : outboxError ? (
                        <div className="text-sm text-muted-foreground">Не удалось загрузить очередь</div>
                    ) : outboxData?.items?.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground">
                                    <tr className="text-left border-b border-border/60">
                                        <th className="py-2 pr-3">Статус</th>
                                        <th className="py-2 pr-3">Попытки</th>
                                        <th className="py-2 pr-3">Канал</th>
                                        <th className="py-2 pr-3">Сообщение</th>
                                        <th className="py-2 pr-3">Ошибка</th>
                                        <th className="py-2 pr-3">Обновлено</th>
                                        <th className="py-2 pr-3 text-right">Действия</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {outboxData.items.map((item) => (
                                        <tr key={item.id} className="border-b border-border/40">
                                            <td className="py-2 pr-3">
                                                <span
                                                    className={`px-2 py-1 rounded text-xs font-medium ${
                                                        item.status === "failed"
                                                            ? "bg-red-100 text-red-800"
                                                            : item.status === "pending"
                                                                ? "bg-yellow-100 text-yellow-800"
                                                                : "bg-blue-100 text-blue-800"
                                                    }`}
                                                >
                                                    {item.status}
                                                </span>
                                            </td>
                                            <td className="py-2 pr-3">{item.attempts}</td>
                                            <td className="py-2 pr-3">{item.channel || "—"}</td>
                                            <td className="py-2 pr-3">
                                                <div className="text-xs text-foreground">{item.message_preview || "—"}</div>
                                                {item.remote_jid && (
                                                    <div className="text-xs text-muted-foreground">{item.remote_jid}</div>
                                                )}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <span className="text-xs text-destructive">{item.last_error || "—"}</span>
                                            </td>
                                            <td className="py-2 pr-3">
                                                {item.updated_at ? new Date(item.updated_at).toLocaleString("ru-RU") : "—"}
                                            </td>
                                            <td className="py-2 pr-3 text-right">
                                                {item.status === "failed" && (
                                                    <button
                                                        type="button"
                                                        className="text-xs text-primary hover:text-primary/80 disabled:opacity-50"
                                                        onClick={() => outboxRetry.mutate([item.id])}
                                                        disabled={outboxRetry.isPending || !canWriteOps}
                                                    >
                                                        Retry
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">Очередь пуста</div>
                    )}
                </div>
            )}

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-jobs-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Console Jobs</h2>
                        <button
                            type="button"
                            className="text-xs text-primary hover:text-primary/80"
                            onClick={() => refetchOpsJobs()}
                        >
                            Обновить историю
                        </button>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 mb-4">
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1">Job type</label>
                            <select
                                className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                value={jobType}
                                onChange={(event) => setJobType(event.target.value as OpsJobType)}
                            >
                                {(opsJobsCatalog?.items || []).map((item) => (
                                    <option key={item.job_type} value={item.job_type}>
                                        {item.label}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-muted-foreground mt-1">
                                {selectedJob?.description || "Каталог jobs загружается..."}
                            </p>
                        </div>

                        <div>
                            {jobType === "outbox_process" && (
                                <>
                                    <label className="block text-xs text-muted-foreground mb-1">Limit</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={200}
                                        className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                        value={outboxProcessLimit}
                                        onChange={(event) => setOutboxProcessLimit(Number(event.target.value))}
                                    />
                                </>
                            )}
                            {jobType === "integration_reconcile" && (
                                <div className="grid gap-2">
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Limit</label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={200}
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={integrationReconcileLimit}
                                            onChange={(event) => setIntegrationReconcileLimit(Number(event.target.value))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">
                                            Branch IDs (optional, comma or newline separated)
                                        </label>
                                        <textarea
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-xs font-mono"
                                            rows={3}
                                            value={integrationReconcileBranchIds}
                                            onChange={(event) => setIntegrationReconcileBranchIds(event.target.value)}
                                            placeholder="uuid-1, uuid-2"
                                        />
                                    </div>
                                </div>
                            )}
                            {jobType === "metrics_snapshot" && (
                                <div className="grid gap-2">
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Days</label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={60}
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={metricsSnapshotDays}
                                            onChange={(event) => setMetricsSnapshotDays(Number(event.target.value))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Metric date (optional)</label>
                                        <input
                                            type="date"
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={metricsSnapshotDate}
                                            onChange={(event) => setMetricsSnapshotDate(event.target.value)}
                                        />
                                    </div>
                                </div>
                            )}
                            {jobType === "heal" && (
                                <p className="text-xs text-muted-foreground mt-6">
                                    Для `heal` в этом срезе доступен только dry-run.
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-2 mb-4">
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => runOpsJob.mutate(buildRunJobPayload("dry_run"))}
                            disabled={runOpsJob.isPending || !canWriteOps}
                        >
                            {runOpsJob.isPending ? "Запуск..." : "Dry-run"}
                        </button>
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => runOpsJob.mutate(buildRunJobPayload("execute"))}
                            disabled={runOpsJob.isPending || !canWriteOps || jobType === "heal"}
                        >
                            Execute
                        </button>
                    </div>

                    {opsJobsLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка истории jobs...</div>
                    ) : !opsJobs?.items?.length ? (
                        <div className="text-sm text-muted-foreground">История jobs пока пуста</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground">
                                    <tr className="text-left border-b border-border/60">
                                        <th className="py-2 pr-3">Тип</th>
                                        <th className="py-2 pr-3">Режим</th>
                                        <th className="py-2 pr-3">Статус</th>
                                        <th className="py-2 pr-3">Запуск</th>
                                        <th className="py-2 pr-3">Результат</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {opsJobs.items.map((job) => (
                                        <tr key={job.id} className="border-b border-border/40">
                                            <td className="py-2 pr-3">{job.job_type}</td>
                                            <td className="py-2 pr-3">{job.mode}</td>
                                            <td className="py-2 pr-3">
                                                <span
                                                    className={`px-2 py-1 rounded text-xs font-medium ${
                                                        job.status === "success"
                                                            ? "bg-green-100 text-green-800"
                                                            : "bg-red-100 text-red-800"
                                                    }`}
                                                >
                                                    {job.status}
                                                </span>
                                            </td>
                                            <td className="py-2 pr-3">
                                                {job.created_at ? new Date(job.created_at).toLocaleString("ru-RU") : "—"}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <span className="text-xs text-muted-foreground">
                                                    {job.error_message || formatJsonPreview(job.result_payload)}
                                                </span>
                                                {(() => {
                                                    const artifactRaw = job.result_payload && typeof job.result_payload === "object"
                                                        ? job.result_payload["artifact"]
                                                        : undefined;
                                                    if (!artifactRaw || typeof artifactRaw !== "object") {
                                                        return null;
                                                    }
                                                    const artifact = artifactRaw as Record<string, unknown>;
                                                    return (
                                                        <div className="mt-1 text-[11px] text-muted-foreground">
                                                            artifact: {String(artifact.artifact_id || "—")}
                                                        </div>
                                                    );
                                                })()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Navigation */}
            <div className="text-center">
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад к заявкам
                </Link>
            </div>
        </div>
    );
}
