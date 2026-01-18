"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";

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

async function fetchHealth(): Promise<HealthData> {
    const response = await api.get("/health");
    return response.data;
}

async function fetchMetrics(): Promise<MetricsData> {
    const response = await api.get("/metrics/daily");
    return response.data;
}

function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
        ok: "норма",
        connected: "подключено",
        degraded: "ухудшено",
        error: "ошибка",
        unknown: "неизвестно",
    };
    return labels[status] || status;
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        ok: "bg-green-100 text-green-800",
        connected: "bg-green-100 text-green-800",
        degraded: "bg-yellow-100 text-yellow-800",
        error: "bg-red-100 text-red-800",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || "bg-gray-100 text-gray-800"}`}>
            {getStatusLabel(status)}
        </span>
    );
}

function MetricCard({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-900">{value}</div>
            <div className="text-sm text-gray-600">{label}</div>
            {subtext && <div className="text-xs text-gray-400 mt-1">{subtext}</div>}
        </div>
    );
}

export default function OpsPage() {
    const { data: session } = useSession();

    const { data: health, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery({
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

    const isLoading = healthLoading || metricsLoading;

    if (!session) {
        return (
            <div className="p-8 text-center text-gray-500">
                Войдите в систему для просмотра статуса.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <h1 className="text-2xl font-bold mb-6">Статус системы</h1>
                <div className="animate-pulse space-y-4">
                    <div className="h-32 bg-gray-200 rounded-lg"></div>
                    <div className="h-32 bg-gray-200 rounded-lg"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Статус системы</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-500">Авто-обновление: 30с</span>
                    <button
                        onClick={() => refetchHealth()}
                        className="text-sm text-blue-600 hover:underline"
                    >
                        Обновить
                    </button>
                </div>
            </div>

            {/* Overall Health */}
            <div className="bg-white border rounded-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Общее состояние</h2>
                    <StatusBadge status={health?.status || "unknown"} />
                </div>
                <p className="text-sm text-gray-600">
                    Версия: <span className="font-mono">{health?.version || "неизвестно"}</span>
                </p>
            </div>

            {/* Daily Metrics */}
            <div className="bg-white border rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">
                    Метрики за сегодня
                    <span className="text-sm font-normal text-gray-500 ml-2">
                        ({metrics?.date || "сегодня"})
                    </span>
                </h2>
                {metricsError ? (
                    <div className="text-sm text-gray-500 text-center py-4">
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
            <div className="bg-white border rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Компоненты</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <span className="text-sm font-medium">База данных</span>
                        <StatusBadge status={health?.database || "unknown"} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                        <span className="text-sm font-medium">Redis</span>
                        <StatusBadge status={health?.redis || "unknown"} />
                    </div>
                </div>
            </div>

            {/* Message Queue */}
            <div className="bg-white border rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Очередь сообщений</h2>
                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Ожидающих сообщений</span>
                    <span className={`text-2xl font-bold ${(health?.outbox_backlog || 0) > 100
                        ? "text-red-600"
                        : (health?.outbox_backlog || 0) > 10
                            ? "text-yellow-600"
                            : "text-green-600"
                        }`}>
                        {health?.outbox_backlog ?? 0}
                    </span>
                </div>
            </div>

            {/* Navigation */}
            <div className="text-center">
                <Link href="/" className="text-blue-600 hover:underline">
                    ← Назад к заявкам
                </Link>
            </div>
        </div>
    );
}
