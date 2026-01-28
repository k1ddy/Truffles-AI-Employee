"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/useAuthenticatedApi";
import Link from "next/link";
import { Case } from "@/types";
import { getStatusLabel, getSlaIndicator } from "@/utils/labels";

// Filter state interface
interface CaseFilters {
    status?: string;
    branchId?: string;
    assignedToMe: boolean;
    query?: string;
    hasDeliveryError: boolean;
    hasPendingOutbox: boolean;
    dateFrom?: string;
    dateTo?: string;
    sortBy: "created_at" | "sla" | "activity";
}

interface Branch {
    id?: string;
    slug?: string;
    name?: string;
}

interface CasesResponse {
    items: Case[];
    cursor?: string;
    has_more?: boolean;
}

type CaseListVariant = "table" | "compact";

interface CaseListProps {
    variant?: CaseListVariant;
    selectedCaseId?: string | null;
    onSelectCase?: (caseId: string) => void;
    branches?: Branch[];
    showBranchFilter?: boolean;
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

export default function CaseList({
    variant = "table",
    selectedCaseId,
    onSelectCase,
    branches = [],
    showBranchFilter = false,
}: CaseListProps) {
    const { data: session } = useSession();
    const api = useAuthenticatedApi();

    const [filters, setFilters] = useState<CaseFilters>({
        status: undefined,
        branchId: undefined,
        assignedToMe: false,
        query: undefined,
        hasDeliveryError: false,
        hasPendingOutbox: false,
        dateFrom: undefined,
        dateTo: undefined,
        sortBy: "activity",
    });
    const [cursor, setCursor] = useState<string | undefined>(undefined);
    const [searchValue, setSearchValue] = useState("");
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const isCompact = variant === "compact";

    useEffect(() => {
        const handle = setTimeout(() => {
            const trimmed = searchValue.trim();
            setFilters((prev) => ({
                ...prev,
                query: trimmed || undefined,
            }));
            setCursor(undefined);
        }, 300);
        return () => clearTimeout(handle);
    }, [searchValue]);

    // Check if we have a valid token
    const hasToken = !!(session as { accessToken?: string } | null)?.accessToken;

    const selectableBranches = branches.filter((branch) => !!branch.id);
    const branchMap = new Map(
        selectableBranches.map((branch) => [branch.id as string, branch.name ?? branch.id as string])
    );
    const branchFilterEnabled = showBranchFilter && selectableBranches.length > 1;
    const advancedFiltersActive = Boolean(
        filters.branchId || filters.dateFrom || filters.dateTo || filters.hasDeliveryError || filters.hasPendingOutbox
    );
    const advancedFiltersVisible = showAdvancedFilters || advancedFiltersActive;
    const advancedToggleLabel = advancedFiltersActive
        ? "Фильтры активны"
        : advancedFiltersVisible
            ? "Скрыть фильтры"
            : "Расширенные фильтры";

    useEffect(() => {
        if (!branchFilterEnabled && filters.branchId) {
            setCursor(undefined);
            setFilters((prev) => ({ ...prev, branchId: undefined }));
        }
    }, [branchFilterEnabled, filters.branchId]);

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["cases", filters, cursor],
        queryFn: async (): Promise<CasesResponse> => {
            const buildParams = (includeSort: boolean) => {
                const params = new URLSearchParams();
                if (filters.status) params.append("status", filters.status);
                if (filters.branchId) params.append("branch_id", filters.branchId);
                if (filters.assignedToMe) params.append("assigned_to_me", "true");
                if (filters.query) params.append("q", filters.query);
                if (filters.hasDeliveryError) params.append("has_delivery_error", "true");
                if (filters.hasPendingOutbox) params.append("has_pending_outbox", "true");
                if (filters.dateFrom) params.append("date_from", filters.dateFrom);
                if (filters.dateTo) params.append("date_to", filters.dateTo);
                if (includeSort) {
                    if (filters.sortBy === "activity") params.append("sort_by", "last_activity");
                    if (filters.sortBy === "created_at") params.append("sort_by", "created_at");
                }
                if (cursor) params.append("cursor", cursor);
                params.append("limit", "20");
                return params;
            };

            const fetchCases = async (includeSort: boolean) => {
                const params = buildParams(includeSort);
                const response = await api.get(`/cases?${params.toString()}`);
                return response.data as CasesResponse;
            };

            try {
                return await fetchCases(true);
            } catch (err) {
                const code = (err as { response?: { data?: { error?: { code?: string; message?: string } } } })?.response?.data?.error?.code;
                const message = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message;
                if (code === "INVALID_PARAM" && message?.includes("sort_by")) {
                    return await fetchCases(false);
                }
                throw err;
            }
        },
        enabled: hasToken,
        refetchInterval: 10000, // Auto-refresh every 10 seconds
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
        if (filters.sortBy === "activity") {
            const aTime = a.last_inbound_at || a.last_activity_at || a.created_at;
            const bTime = b.last_inbound_at || b.last_activity_at || b.created_at;
            return new Date(bTime).getTime() - new Date(aTime).getTime();
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
            <div className="w-full">
                <h2 className="text-xl font-semibold mb-4" data-testid="cases-title">Заявки</h2>
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
            <div
                className={`flex flex-wrap items-center gap-3 mb-4 p-3 bg-muted rounded-lg border border-border/60 ${
                    isCompact ? "flex-col items-start" : ""
                }`}
                data-testid="cases-filters"
            >
                <div className="flex w-full flex-wrap items-center gap-3">
                    <input
                        type="text"
                        value={searchValue}
                        onChange={(e) => setSearchValue(e.target.value)}
                        placeholder="Телефон / имя / ID"
                        className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40 min-w-[220px]"
                        data-testid="cases-filter-search"
                    />
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
                    <select
                        value={filters.sortBy}
                        onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as "created_at" | "sla" | "activity" })}
                        className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                        data-testid="cases-filter-sort"
                    >
                        <option value="activity">Сортировка: Активные</option>
                        <option value="created_at">Сортировка: Новые</option>
                        <option value="sla">Сортировка: Срочные</option>
                    </select>
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
                    <button
                        type="button"
                        onClick={() => setShowAdvancedFilters((prev) => !prev)}
                        className="text-xs text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                        data-testid="cases-filter-advanced-toggle"
                        disabled={advancedFiltersActive}
                    >
                        {advancedToggleLabel}
                    </button>
                    {(filters.status || (branchFilterEnabled && filters.branchId) || filters.dateFrom || filters.dateTo || filters.assignedToMe || filters.query || filters.hasDeliveryError || filters.hasPendingOutbox) && (
                        <button
                            onClick={() => {
                                setSearchValue("");
                                resetPagination();
                                setShowAdvancedFilters(false);
                                setFilters({
                                    assignedToMe: false,
                                    sortBy: "activity",
                                    hasDeliveryError: false,
                                    hasPendingOutbox: false,
                                });
                            }}
                            className="text-xs text-muted-foreground hover:text-destructive"
                            data-testid="cases-filter-clear"
                        >
                            Сбросить
                        </button>
                    )}
                </div>
                {advancedFiltersVisible && (
                    <div
                        className="flex w-full flex-wrap items-center gap-3 border-t border-border/60 pt-3"
                        data-testid="cases-filters-advanced"
                    >
                        {branchFilterEnabled && (
                            <select
                                value={filters.branchId || ""}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, branchId: e.target.value || undefined }); }}
                                className="px-3 py-2 border border-border/60 rounded-lg text-sm bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                                data-testid="cases-filter-branch"
                            >
                                <option value="">Все филиалы</option>
                                {selectableBranches.map((branch) => (
                                    <option key={branch.id} value={branch.id}>
                                        {branch.name ?? branch.id}
                                    </option>
                                ))}
                            </select>
                        )}
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
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={filters.hasDeliveryError}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, hasDeliveryError: e.target.checked }); }}
                                className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                data-testid="cases-filter-delivery-error"
                            />
                            <span className="text-sm text-foreground/80">Есть ошибки</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={filters.hasPendingOutbox}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, hasPendingOutbox: e.target.checked }); }}
                                className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                data-testid="cases-filter-pending-outbox"
                            />
                            <span className="text-sm text-foreground/80">В очереди</span>
                        </label>
                    </div>
                )}
            </div>

            {/* Results count */}
            <div className="text-sm text-muted-foreground mb-2" data-testid="cases-count">
                {sortedCases.length} {sortedCases.length === 1 ? "заявка" : sortedCases.length < 5 ? "заявки" : "заявок"}
                {data?.has_more && " (есть ещё)"}
            </div>

            {isCompact ? (
                <div className="flex flex-col gap-2" data-testid="cases-table">
                    {sortedCases.map((c) => {
                        const sla = getSlaIndicator(c.created_at);
                        const branchName = branchMap.get(c.branch_id || "") || "-";
                        const lastInbound = c.last_inbound_at ? new Date(c.last_inbound_at) : null;
                        const lastActivity = c.last_activity_at || c.last_inbound_at || c.created_at;
                        const isLive = lastInbound ? (Date.now() - lastInbound.getTime()) < 5 * 60 * 1000 : false;
                        const needsReply = !!c.needs_reply;
                        const hasIssue = !!c.has_delivery_error || !!c.has_pending_outbox;
                        const contactName = c.customer_name || c.customer_phone || c.customer_remote_jid?.split("@")[0] || "Клиент";
                        const contactPhone = c.customer_phone || c.customer_remote_jid?.split("@")[0] || "";
                        const preview = c.last_message_preview || c.user_message || "-";
                        const isSelected = selectedCaseId === c.id;
                        const statusClass = c.status === "active"
                            ? "bg-green-100 text-green-800"
                            : c.status === "pending"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-muted text-muted-foreground";
                        const content = (
                            <div
                                className={`rounded-xl border border-border/60 p-3 text-left transition ${
                                    isSelected ? "border-primary/60 bg-primary/5" : "bg-card hover:bg-muted/60"
                                }`}
                            >
                                <div className="flex items-start justify-between gap-3 mb-2">
                                    <div>
                                        <p className="text-sm font-semibold">{contactName}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {contactPhone || branchName}
                                        </p>
                                    </div>
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${statusClass}`}>
                                        {getStatusLabel(c.status)}
                                    </span>
                                </div>
                                <p className="text-xs text-muted-foreground mb-2">
                                    {preview}
                                </p>
                                <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                                    <span>{branchName}</span>
                                    <span>•</span>
                                    <span>{new Date(lastActivity).toLocaleString("ru-RU")}</span>
                                    <span className={`px-2 py-0.5 rounded font-semibold ${sla.className}`}>
                                        {sla.label}
                                    </span>
                                    {needsReply && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-yellow-100 text-yellow-800">
                                            NEW
                                        </span>
                                    )}
                                    {isLive && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-green-100 text-green-800">
                                            LIVE
                                        </span>
                                    )}
                                    {hasIssue && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-red-100 text-red-800">
                                            ⚠️
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                        return onSelectCase ? (
                            <button
                                key={c.id}
                                type="button"
                                onClick={() => onSelectCase(c.id)}
                                className="text-left"
                                data-testid="cases-row"
                            >
                                {content}
                            </button>
                        ) : (
                            <Link key={c.id} href={`/cases/${c.id}`} data-testid="cases-row">
                                {content}
                            </Link>
                        );
                    })}
                    {sortedCases.length === 0 && (
                        <div className="text-center text-muted-foreground py-6" data-testid="cases-empty">
                            Заявки не найдены по указанным фильтрам.
                        </div>
                    )}
                </div>
            ) : (
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
                                <th className="p-4 text-sm font-medium text-muted-foreground">Активность</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedCases.map((c) => {
                                const sla = getSlaIndicator(c.created_at);
                                const branchName = branchMap.get(c.branch_id || "") || "-";
                                const lastInbound = c.last_inbound_at ? new Date(c.last_inbound_at) : null;
                                const lastActivity = c.last_activity_at || c.last_inbound_at || c.created_at;
                                const isLive = lastInbound ? (Date.now() - lastInbound.getTime()) < 5 * 60 * 1000 : false;
                                const needsReply = !!c.needs_reply;
                                const hasIssue = !!c.has_delivery_error || !!c.has_pending_outbox;
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
                                        <td className="p-4 text-sm max-w-xs">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="truncate max-w-[180px]">{c.last_message_preview || c.user_message || "-"}</span>
                                                {needsReply && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-800">
                                                        NEW
                                                    </span>
                                                )}
                                                {isLive && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800">
                                                        LIVE
                                                    </span>
                                                )}
                                                {hasIssue && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-800">
                                                        ⚠️
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="p-4 text-sm text-muted-foreground">
                                            <div className="flex flex-col">
                                                <span>{new Date(lastActivity).toLocaleString("ru-RU")}</span>
                                                <span className="text-xs text-muted-foreground">
                                                    {c.last_activity_channel || "—"}
                                                </span>
                                            </div>
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
            )}

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
