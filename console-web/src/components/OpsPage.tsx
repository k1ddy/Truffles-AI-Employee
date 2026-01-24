"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { telegramApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

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

export default function OpsPage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();
    const [telegramAction, setTelegramAction] = useState<"verify" | "test" | null>(null);
    const [outboxStatus, setOutboxStatus] = useState<OutboxStatusFilter>("failed");

    const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
        queryKey: ["health"],
        queryFn: fetchHealth,
        enabled: !!session,
        refetchInterval: 30000,
    });

    const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery({
        queryKey: ["metrics-daily"],
        queryFn: fetchMetrics,
        enabled: !!session,
        refetchInterval: 60000,
    });

    // TG-03: Telegram Health
    const { data: telegramHealth } = useQuery({
        queryKey: ["telegram-health"],
        queryFn: fetchTelegramHealth,
        enabled: !!session,
        refetchInterval: 30000,
    });

    const { data: outboxData, isLoading: outboxLoading, error: outboxError, refetch: refetchOutbox } = useQuery({
        queryKey: ["ops-outbox", outboxStatus],
        queryFn: () => fetchOutbox(outboxStatus),
        enabled: !!session,
        refetchInterval: 30000,
        onError: (error) => {
            handleError(error);
        },
    });

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

    const isLoading = healthLoading || metricsLoading;

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра статуса.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto p-6" data-testid="ops-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="ops-title">Статус системы</h1>
                <div className="animate-pulse space-y-4">
                    <div className="h-32 bg-muted/70 rounded-lg"></div>
                    <div className="h-32 bg-muted/70 rounded-lg"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6" data-testid="ops-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="ops-title">Статус системы</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">Авто-обновление: 30с</span>
                    <button
                        onClick={() => refetchHealth()}
                        className="text-sm text-primary hover:text-primary/80"
                    >
                        Обновить
                    </button>
                </div>
            </div>

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

            {/* Daily Metrics */}
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
                        disabled={telegramAction !== null}
                        data-testid="ops-telegram-verify"
                    >
                        {telegramAction === "verify" ? "Отправка..." : "Verify"}
                    </button>
                    <button
                        type="button"
                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => telegramTest.mutate()}
                        disabled={telegramAction !== null}
                        data-testid="ops-telegram-test"
                    >
                        {telegramAction === "test" ? "Отправка..." : "Send test"}
                    </button>
                </div>
            </div>

            {/* Message Queue */}
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
                            onClick={() => outboxRetry.mutate()}
                            disabled={outboxRetry.isPending}
                        >
                            {outboxRetry.isPending ? "Ретрай..." : "Retry failed"}
                        </button>
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
                                                    disabled={outboxRetry.isPending}
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

            {/* Navigation */}
            <div className="text-center">
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад к заявкам
                </Link>
            </div>
        </div>
    );
}
