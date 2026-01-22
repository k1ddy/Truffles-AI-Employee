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
                    <div className="h-4 bg-muted rounded w-20"></div>
                    <div className="h-4 bg-muted rounded w-16"></div>
                    <div className="h-4 bg-muted rounded w-24"></div>
                    <div className="h-4 bg-muted rounded flex-1"></div>
                    <div className="h-4 bg-muted rounded w-32"></div>
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

    // Update allCases when data changes
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
    };

    if (!session) {
        return null;
    }

    if (isLoading && !cursor) {
        return (
            <div className="w-full">
                <h2 className="text-xl font-semibold mb-4" data-testid="cases-title">Заявки</h2>
                <TableSkeleton />
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="cases-error">
                <p className="text-destructive mb-4">Не удалось загрузить заявки</p>
                <button
                    onClick={() => refetch()}
                    className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                    data-testid="cases-retry"
                >
                    Повторить
                </button>
            </div>
        );
    }

    return (
        <div className="w-full">
            {/* Header with filters */}
            <div className="flex flex-wrap justify-between items-center gap-4 mb-4">
                <h2 className="text-xl font-semibold" data-testid="cases-title">Заявки</h2>
                <button
                    onClick={() => { resetPagination(); refetch(); }}
                    className="text-sm text-primary hover:text-primary/80"
                    data-testid="cases-refresh"
                >
                    Обновить
                </button>
            </div>

            {/* Filter row */}
            <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-muted rounded-lg border border-border/60" data-testid="cases-filters">
                {/* Status filter */}
                <select
                    value={filters.status || ""}
                    onChange={(e) => { resetPagination(); setFilters({ ...filters, status: e.target.value || undefined }); }}
                    className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                    data-testid="cases-filter-status"
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
                        className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                        data-testid="cases-filter-branch"
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
                    className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                    data-testid="cases-filter-sort"
                >
                    <option value="created_at">Сортировка: Новые</option>
                    <option value="sla">Сортировка: Срочные</option>
                </select>

                {/* Date from */}
                <div className="flex items-center gap-1">
                    <span className="text-xs text-muted-foreground">С:</span>
                    <input
                        type="date"
                        value={filters.dateFrom || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, dateFrom: e.target.value || undefined }); }}
                        className="px-2 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                        data-testid="cases-filter-date-from"
                    />
                </div>

                {/* Date to */}
                <div className="flex items-center gap-1">
                    <span className="text-xs text-muted-foreground">По:</span>
                    <input
                        type="date"
                        value={filters.dateTo || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, dateTo: e.target.value || undefined }); }}
                        className="px-2 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                        data-testid="cases-filter-date-to"
                    />
                </div>

                {/* Assigned to me toggle */}
                <label className="flex items-center gap-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={filters.assignedToMe}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, assignedToMe: e.target.checked }); }}
                        className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                        data-testid="cases-filter-assigned"
                    />
                    <span className="text-sm text-foreground/80">Мои заявки</span>
                </label>

                {/* Clear filters */}
                {(filters.status || filters.branchId || filters.dateFrom || filters.dateTo || filters.assignedToMe) && (
                    <button
                        onClick={() => { resetPagination(); setFilters({ assignedToMe: false, sortBy: "created_at" }); }}
                        className="text-xs text-muted-foreground hover:text-destructive"
                        data-testid="cases-filter-clear"
                    >
                        Сбросить
                    </button>
                )}
            </div>

            {/* Results count */}
            <div className="text-sm text-muted-foreground mb-2" data-testid="cases-count">
                {sortedCases.length} {sortedCases.length === 1 ? "заявка" : sortedCases.length < 5 ? "заявки" : "заявок"}
                {data?.has_more && " (есть ещё)"}
            </div>

            {/* Table */}
            <div className="overflow-x-auto border border-border/60 rounded-lg bg-card" data-testid="cases-table">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-muted">
                        <tr>
                            <th className="p-4 text-sm font-medium text-muted-foreground">ID</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Статус</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">SLA</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Филиал</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Канал</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Назначено</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Сообщение</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Создано</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedCases.map((c) => {
                            const sla = getSlaIndicator(c.created_at);
                            const branchName = branchMap.get(c.branch_id || "") || "-";
                            return (
                                <tr key={c.id} className="border-b border-border/60 hover:bg-muted/60" data-testid="cases-row">
                                    <td className="p-4 font-mono text-sm">{c.id.slice(0, 8)}...</td>
                                    <td className="p-4">
                                        <span
                                            className={`px-2 py-1 rounded text-xs font-medium ${c.status === "active"
                                                ? "bg-green-100 text-green-800"
                                                : c.status === "pending"
                                                    ? "bg-yellow-100 text-yellow-800"
                                                    : "bg-muted text-muted-foreground"
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
                                    <td className="p-4 text-sm text-muted-foreground">
                                        {new Date(c.created_at).toLocaleString("ru-RU")}
                                    </td>
                                    <td className="p-4">
                                        <Link
                                            href={`/cases/${c.id}`}
                                            className="rounded-full bg-primary px-3 py-1 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
                                            data-testid="case-open"
                                        >
                                            Открыть
                                        </Link>
                                    </td>
                                </tr>
                            );
                        })}
                        {sortedCases.length === 0 && (
                            <tr>
                                <td colSpan={9} className="p-8 text-center text-muted-foreground" data-testid="cases-empty">
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
                        className="px-6 py-2 bg-muted text-foreground/80 rounded-lg hover:bg-muted/80 disabled:opacity-50"
                        data-testid="cases-load-more"
                    >
                        {isFetching ? "Загрузка..." : "Загрузить ещё"}
                    </button>
                </div>
            )}
        </div>
    );
}
