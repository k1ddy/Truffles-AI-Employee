"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useAuthenticatedApi } from "@/hooks/useAuthenticatedApi";
import Link from "next/link";
import { Case } from "@/types";
import { getStatusLabel, getSlaIndicator } from "@/utils/labels";

// Filter state interface
interface CaseFilters {
    status?: string;
    branchId?: string;
    assignedToMe: boolean;
    dateFrom?: string;
    dateTo?: string;
    sortBy: "created_at" | "sla";
}

interface Branch {
    id: string;
    slug: string;
    name: string;
}

interface CasesResponse {
    items: Case[];
    cursor?: string;
    has_more?: boolean;
}

// Loading skeleton component
function TableSkeleton() {
    return (
        <div className="animate-pulse">
            {[...Array(5)].map((_, i) => (
                <div key={i} className="flex gap-4 p-4 border-b">
                    <div className="h-4 bg-gray-200 rounded w-20"></div>
                    <div className="h-4 bg-gray-200 rounded w-16"></div>
                    <div className="h-4 bg-gray-200 rounded w-24"></div>
                    <div className="h-4 bg-gray-200 rounded flex-1"></div>
                    <div className="h-4 bg-gray-200 rounded w-32"></div>
                </div>
            ))}
        </div>
    );
}

export default function CaseList() {
    const { data: session } = useSession();
    const api = useAuthenticatedApi();

    const [filters, setFilters] = useState<CaseFilters>({
        status: undefined,
        branchId: undefined,
        assignedToMe: false,
        dateFrom: undefined,
        dateTo: undefined,
        sortBy: "created_at",
    });
    const [cursor, setCursor] = useState<string | undefined>(undefined);

    // Check if we have a valid token
    const hasToken = !!(session as { accessToken?: string } | null)?.accessToken;

    // Fetch branches for filter dropdown
    const { data: settingsData } = useQuery({
        queryKey: ["settings"],
        queryFn: async () => {
            const response = await api.get("/settings");
            return response.data;
        },
        enabled: hasToken,
    });

    const branches: Branch[] = settingsData?.branches ?? [];
    const branchMap = new Map<string, string>(branches.map((b) => [b.id, b.name]));

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["cases", filters, cursor],
        queryFn: async (): Promise<CasesResponse> => {
            const params = new URLSearchParams();
            if (filters.status) params.append("status", filters.status);
            if (filters.branchId) params.append("branch_id", filters.branchId);
            if (filters.assignedToMe) params.append("assigned_to_me", "true");
            if (filters.dateFrom) params.append("date_from", filters.dateFrom);
            if (filters.dateTo) params.append("date_to", filters.dateTo);
            if (cursor) params.append("cursor", cursor);
            params.append("limit", "20");

            const response = await api.get(`/cases?${params.toString()}`);
            return response.data;
        },
        enabled: hasToken,
        refetchInterval: 30000, // Auto-refresh every 30 seconds
        refetchIntervalInBackground: false, // Only refresh when tab is active
    });

    const cases = data?.items ?? [];

    // Sort by SLA if selected
    const sortedCases = [...cases].sort((a, b) => {
        if (filters.sortBy === "sla") {
            const slaA = getSlaIndicator(a.created_at).minutes;
            const slaB = getSlaIndicator(b.created_at).minutes;
            return slaB - slaA; // Oldest first (highest SLA breach)
        }
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    const loadMore = () => {
        if (data?.cursor) {
            setCursor(data.cursor);
        }
    };

    const resetPagination = () => {
        setCursor(undefined);
        setAllCases([]);
    };

    if (!session) {
        return null;
    }

    if (isLoading && !cursor) {
        return (
            <div className="w-full">
                <h2 data-testid="cases-title" className="text-xl font-semibold mb-4">Заявки</h2>
                <TableSkeleton />
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full">
                <h2 data-testid="cases-title" className="text-xl font-semibold mb-4">Заявки</h2>
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <p className="text-red-600 mb-4">Не удалось загрузить заявки</p>
                    <button
                        onClick={() => refetch()}
                        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full">
            {/* Header with filters */}
            <div className="flex flex-wrap justify-between items-center gap-4 mb-4">
                <h2 data-testid="cases-title" className="text-xl font-semibold">Заявки</h2>
                <button
                    onClick={() => { resetPagination(); refetch(); }}
                    className="text-sm text-blue-600 hover:underline"
                >
                    Обновить
                </button>
            </div>

            {/* Filter row */}
            <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
                {/* Status filter */}
                <select
                    value={filters.status || ""}
                    onChange={(e) => { resetPagination(); setFilters({ ...filters, status: e.target.value || undefined }); }}
                    className="px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="">Все статусы</option>
                    <option value="pending">Ожидает</option>
                    <option value="active">В работе</option>
                    <option value="resolved">Закрыта</option>
                </select>

                {/* Branch filter */}
                {branches.length > 0 && (
                    <select
                        value={filters.branchId || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, branchId: e.target.value || undefined }); }}
                        className="px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">Все филиалы</option>
                        {branches.map((b: Branch) => (
                            <option key={b.id} value={b.id}>{b.name}</option>
                        ))}
                    </select>
                )}

                {/* Sort by */}
                <select
                    value={filters.sortBy}
                    onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as "created_at" | "sla" })}
                    className="px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="created_at">Сортировка: Новые</option>
                    <option value="sla">Сортировка: Срочные</option>
                </select>

                {/* Date from */}
                <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-500">С:</span>
                    <input
                        type="date"
                        value={filters.dateFrom || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, dateFrom: e.target.value || undefined }); }}
                        className="px-2 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                {/* Date to */}
                <div className="flex items-center gap-1">
                    <span className="text-xs text-gray-500">По:</span>
                    <input
                        type="date"
                        value={filters.dateTo || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, dateTo: e.target.value || undefined }); }}
                        className="px-2 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                {/* Assigned to me toggle */}
                <label className="flex items-center gap-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={filters.assignedToMe}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, assignedToMe: e.target.checked }); }}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Мои заявки</span>
                </label>

                {/* Clear filters */}
                {(filters.status || filters.branchId || filters.dateFrom || filters.dateTo || filters.assignedToMe) && (
                    <button
                        onClick={() => { resetPagination(); setFilters({ assignedToMe: false, sortBy: "created_at" }); }}
                        className="text-xs text-gray-500 hover:text-red-600"
                    >
                        Сбросить
                    </button>
                )}
            </div>

            {/* Results count */}
            <div className="text-sm text-gray-500 mb-2">
                {sortedCases.length} {sortedCases.length === 1 ? "заявка" : sortedCases.length < 5 ? "заявки" : "заявок"}
                {data?.has_more && " (есть ещё)"}
            </div>

            {/* Table */}
            <div className="overflow-x-auto border rounded-lg">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="p-4 text-sm font-medium text-gray-600">ID</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Статус</th>
                            <th className="p-4 text-sm font-medium text-gray-600">SLA</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Филиал</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Канал</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Назначено</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Сообщение</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Создано</th>
                            <th className="p-4 text-sm font-medium text-gray-600">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedCases.map((c) => {
                            const sla = getSlaIndicator(c.created_at);
                            const branchName = branchMap.get(c.branch_id || "") || "-";
                            return (
                                <tr key={c.id} className="border-b hover:bg-gray-50">
                                    <td className="p-4 font-mono text-sm">{c.id.slice(0, 8)}...</td>
                                    <td className="p-4">
                                        <span
                                            className={`px-2 py-1 rounded text-xs font-medium ${c.status === "active"
                                                ? "bg-green-100 text-green-800"
                                                : c.status === "pending"
                                                    ? "bg-yellow-100 text-yellow-800"
                                                    : "bg-gray-100 text-gray-800"
                                                }`}
                                        >
                                            {getStatusLabel(c.status)}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${sla.className}`}>
                                            {sla.label}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm">{branchName}</td>
                                    <td className="p-4 text-sm">{c.channel}</td>
                                    <td className="p-4 text-sm">{c.assigned_to_name || "-"}</td>
                                    <td className="p-4 text-sm truncate max-w-xs">{c.user_message || "-"}</td>
                                    <td className="p-4 text-sm text-gray-500">
                                        {new Date(c.created_at).toLocaleString("ru-RU")}
                                    </td>
                                    <td className="p-4">
                                        <Link
                                            href={`/cases/${c.id}`}
                                            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                                        >
                                            Открыть
                                        </Link>
                                    </td>
                                </tr>
                            );
                        })}
                        {sortedCases.length === 0 && (
                            <tr>
                                <td colSpan={9} className="p-8 text-center text-gray-500">
                                    Заявки не найдены по указанным фильтрам.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Load More button */}
            {data?.has_more && (
                <div className="mt-4 text-center">
                    <button
                        onClick={loadMore}
                        disabled={isFetching}
                        className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                    >
                        {isFetching ? "Загрузка..." : "Загрузить ещё"}
                    </button>
                </div>
            )}
        </div>
    );
}
