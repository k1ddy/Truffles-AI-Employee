"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/useAuthenticatedApi";
import Link from "next/link";
import { Case } from "@/types";
import { getStatusLabel, getSlaIndicator } from "@/utils/labels";
import {
    type InboxCaseFilters,
    type InboxCaseListPrefs,
    readInboxCaseListPrefs,
    writeInboxCaseListPrefs,
} from "@/lib/inbox-workspace";

// Filter state interface
type CaseFilters = InboxCaseFilters;

interface Branch {
    id?: string;
    slug?: string;
    name?: string;
}

interface CasesResponse {
    items: Case[];
    cursor?: string;
    has_more?: boolean;
    total?: number | null;
}

type CaseListVariant = "table" | "compact";

interface CaseListProps {
    variant?: CaseListVariant;
    selectedCaseId?: string | null;
    onSelectCase?: (caseId: string) => void;
    branches?: Branch[];
    showBranchFilter?: boolean;
    workspaceScope?: string | null;
    onCaseIdsChange?: (caseIds: string[]) => void;
}

const DEFAULT_FILTERS: CaseFilters = {
    status: "open",
    branchId: undefined,
    assignedToMe: false,
    query: undefined,
    hasDeliveryError: false,
    hasPendingOutbox: false,
    hasHumanLock: false,
    dateFrom: undefined,
    dateTo: undefined,
    sortBy: "activity",
};

function getPriorityChip(tier?: string | null): { label: string; className: string } | null {
    const normalized = (tier || "").toLowerCase();
    if (!normalized) {
        return null;
    }
    if (normalized === "urgent") {
        return { label: "Критично", className: "bg-red-100 text-red-800" };
    }
    if (normalized === "high") {
        return { label: "Высокий", className: "bg-amber-100 text-amber-900" };
    }
    if (normalized === "normal") {
        return { label: "Обычный", className: "bg-blue-100 text-blue-800" };
    }
    if (normalized === "low") {
        return { label: "Низкий", className: "bg-slate-100 text-slate-700" };
    }
    return { label: normalized, className: "bg-muted text-muted-foreground" };
}

function normalizeStoredPrefs(raw: InboxCaseListPrefs | null): InboxCaseListPrefs | null {
    if (!raw || typeof raw !== "object") {
        return null;
    }
    const filters = raw.filters;
    if (!filters || typeof filters !== "object") {
        return null;
    }
    const sortBy = filters.sortBy;
    if (sortBy !== "activity" && sortBy !== "created_at" && sortBy !== "sla") {
        return null;
    }
    return {
        filters: {
            status: filters.status,
            branchId: filters.branchId,
            assignedToMe: Boolean(filters.assignedToMe),
            query: filters.query,
            hasDeliveryError: Boolean(filters.hasDeliveryError),
            hasPendingOutbox: Boolean(filters.hasPendingOutbox),
            hasHumanLock: Boolean(filters.hasHumanLock),
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            sortBy,
        },
        searchValue: typeof raw.searchValue === "string" ? raw.searchValue : "",
        showAdvancedFilters: Boolean(raw.showAdvancedFilters),
        filtersCollapsed: Boolean(raw.filtersCollapsed),
        autoRefreshEnabled: typeof raw.autoRefreshEnabled === "boolean" ? raw.autoRefreshEnabled : true,
    };
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
    workspaceScope,
    onCaseIdsChange,
}: CaseListProps) {
    const { data: session } = useSession();
    const api = useAuthenticatedApi();
    const storageEnabled = Boolean(workspaceScope);
    const [stateReady, setStateReady] = useState(!storageEnabled);

    const [filters, setFilters] = useState<CaseFilters>(DEFAULT_FILTERS);
    const [cursor, setCursor] = useState<string | undefined>(undefined);
    const [caseItems, setCaseItems] = useState<Case[]>([]);
    const [searchValue, setSearchValue] = useState("");
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const [filtersCollapsed, setFiltersCollapsed] = useState(false);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
    const [documentVisible, setDocumentVisible] = useState(true);
    const isCompact = variant === "compact";
    const filtersCompact = isCompact && !!selectedCaseId;
    const headingLabel = isCompact ? "Очередь" : "Заявки";
    const sortOptions: { id: CaseFilters["sortBy"]; label: string }[] = [
        { id: "activity", label: "Активные" },
        { id: "created_at", label: "Новые" },
        { id: "sla", label: "Срочные" },
    ];

    useEffect(() => {
        setStateReady(!workspaceScope);
    }, [workspaceScope]);

    useEffect(() => {
        if (!workspaceScope) {
            setStateReady(true);
            return;
        }
        const restored = normalizeStoredPrefs(readInboxCaseListPrefs(workspaceScope));
        if (restored) {
            setFilters(restored.filters);
            setSearchValue(restored.searchValue);
            setShowAdvancedFilters(restored.showAdvancedFilters);
            setFiltersCollapsed(restored.filtersCollapsed);
            setAutoRefreshEnabled(restored.autoRefreshEnabled);
            setCursor(undefined);
            setCaseItems([]);
        }
        setStateReady(true);
    }, [workspaceScope]);

    useEffect(() => {
        const handle = setTimeout(() => {
            const trimmed = searchValue.trim();
            setFilters((prev) => ({
                ...prev,
                query: trimmed || undefined,
            }));
            setCursor(undefined);
            setCaseItems([]);
        }, 300);
        return () => clearTimeout(handle);
    }, [searchValue]);

    useEffect(() => {
        if (typeof document === "undefined") {
            return;
        }
        const updateVisibility = () => {
            setDocumentVisible(!document.hidden);
        };
        updateVisibility();
        document.addEventListener("visibilitychange", updateVisibility);
        return () => {
            document.removeEventListener("visibilitychange", updateVisibility);
        };
    }, []);

    // Check if we have a valid token
    const hasToken = !!(session as { accessToken?: string } | null)?.accessToken;

    const selectableBranches = branches.filter((branch) => !!branch.id);
    const branchMap = new Map(
        selectableBranches.map((branch) => [branch.id as string, branch.name ?? branch.id as string])
    );
    const branchFilterEnabled = showBranchFilter && selectableBranches.length > 1;
    const statusFilterActive = filters.status !== "open";
    const advancedFiltersActive = Boolean(
        filters.branchId
        || filters.dateFrom
        || filters.dateTo
        || filters.hasDeliveryError
        || filters.hasPendingOutbox
        || filters.hasHumanLock
    );
    const advancedFiltersVisible = showAdvancedFilters || advancedFiltersActive;
    const filtersToggleLabel = filtersCollapsed
        ? advancedFiltersActive
            ? "Фильтры активны"
            : "Фильтры"
        : "Скрыть фильтры";
    const showAdvancedFiltersRow = !filtersCollapsed && advancedFiltersVisible;
    const advancedToggleLabel = advancedFiltersActive
        ? "Фильтры активны"
        : advancedFiltersVisible
            ? "Скрыть фильтры"
            : "Расширенные фильтры";
    const headingClass = filtersCompact ? "text-base" : isCompact ? "text-lg" : "text-xl";
    const isTight = filtersCompact || filtersCollapsed;
    const autoRefreshLabel = autoRefreshEnabled ? "Автообновление: Вкл" : "Автообновление: Выкл";
    const autoRefreshButtonClass = autoRefreshEnabled
        ? "text-emerald-700 hover:text-emerald-900"
        : "text-muted-foreground hover:text-foreground";
    const refreshIntervalMs = selectedCaseId ? 15000 : 10000;
    const filterContainerClass = `flex flex-col border border-border/60 rounded-lg ${
        isTight ? "gap-2 p-2" : "gap-3 p-3"
    } ${isCompact ? "sticky top-0 z-10 bg-card/95 backdrop-blur" : "bg-muted"}`;
    const searchInputClass = `px-3 border border-border/60 rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-primary/40 ${
        filtersCollapsed ? "min-w-[120px]" : "min-w-[160px]"
    } ${isTight ? "py-1.5 text-xs" : "py-2 text-sm"}`;
    const selectClass = `px-3 border border-border/60 rounded-lg bg-card focus:outline-none focus:ring-2 focus:ring-primary/40 ${
        isTight ? "py-1.5 text-xs" : "py-2 text-xs"
    }`;

    const pillClass = (active: boolean) => (
        `rounded-full border px-3 py-1 text-xs font-semibold transition ${
            active
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border/60 text-muted-foreground hover:text-foreground"
        }`
    );

    useEffect(() => {
        if (!filtersCompact) {
            setFiltersCollapsed(false);
            return;
        }
        if (advancedFiltersActive) {
            setFiltersCollapsed(false);
            return;
        }
        setFiltersCollapsed(true);
    }, [filtersCompact, advancedFiltersActive]);

    useEffect(() => {
        if (!branchFilterEnabled && filters.branchId) {
            setCursor(undefined);
            setCaseItems([]);
            setFilters((prev) => ({ ...prev, branchId: undefined }));
        }
    }, [branchFilterEnabled, filters.branchId]);

    const { data, isLoading, error, refetch, isFetching, dataUpdatedAt } = useQuery({
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
                if (filters.hasHumanLock) params.append("has_human_lock", "true");
                if (filters.dateFrom) params.append("date_from", filters.dateFrom);
                if (filters.dateTo) params.append("date_to", filters.dateTo);
                if (includeSort) {
                    if (filters.sortBy === "activity") params.append("sort_by", "last_activity");
                    if (filters.sortBy === "created_at") params.append("sort_by", "created_at");
                    if (filters.sortBy === "sla") params.append("sort_by", "sla");
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
        enabled: hasToken && stateReady,
        refetchInterval: autoRefreshEnabled && documentVisible ? refreshIntervalMs : false,
        refetchIntervalInBackground: false, // Only refresh when tab is active
    });
    const lastUpdatedTime = dataUpdatedAt
        ? new Date(dataUpdatedAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
        : null;
    const refreshStatusLabel = isFetching
        ? "Обновление..."
        : lastUpdatedTime
            ? `Обновлено: ${lastUpdatedTime}`
            : null;

    useEffect(() => {
        if (!data?.items) {
            return;
        }
        if (!cursor) {
            setCaseItems(data.items);
            return;
        }
        setCaseItems((prev) => {
            const byId = new Map(prev.map((item) => [item.id, item]));
            data.items.forEach((item) => {
                byId.set(item.id, item);
            });
            return Array.from(byId.values());
        });
    }, [data, cursor]);

    const cases = caseItems;

    // Keep server order for SLA; local sort for other modes.
    const sortedCases =
        filters.sortBy === "sla"
            ? cases
            : [...cases].sort((a, b) => {
                if (filters.sortBy === "activity") {
                    const aTime = a.last_inbound_at || a.last_activity_at || a.created_at;
                    const bTime = b.last_inbound_at || b.last_activity_at || b.created_at;
                    return new Date(bTime).getTime() - new Date(aTime).getTime();
                }
                return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
            });

    useEffect(() => {
        if (!workspaceScope || !stateReady) {
            return;
        }
        writeInboxCaseListPrefs(workspaceScope, {
            filters,
            searchValue,
            showAdvancedFilters,
            filtersCollapsed,
            autoRefreshEnabled,
        });
    }, [workspaceScope, stateReady, filters, searchValue, showAdvancedFilters, filtersCollapsed, autoRefreshEnabled]);

    useEffect(() => {
        if (!onCaseIdsChange) {
            return;
        }
        onCaseIdsChange(
            sortedCases
                .map((item) => item.id)
                .filter((item): item is string => Boolean(item))
        );
    }, [onCaseIdsChange, sortedCases]);

    const loadMore = () => {
        if (data?.cursor) {
            setCursor(data.cursor);
        }
    };

    const resetPagination = () => {
        setCursor(undefined);
        setCaseItems([]);
    };

    if (!session) {
        return null;
    }

    if (!stateReady) {
        return (
            <div className="w-full">
                <h2 className="text-xl font-semibold mb-4" data-testid="cases-title">{headingLabel}</h2>
                <TableSkeleton />
            </div>
        );
    }

    if (isLoading && !cursor) {
        return (
            <div className="w-full">
                <h2 className="text-xl font-semibold mb-4" data-testid="cases-title">{headingLabel}</h2>
                <TableSkeleton />
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full">
                <h2 className="text-xl font-semibold mb-4" data-testid="cases-title">{headingLabel}</h2>
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

    const caseNoun = (count: number) => (count === 1 ? "заявка" : count < 5 ? "заявки" : "заявок");
    const loadedCases = sortedCases.length;
    const totalCases = typeof data?.total === "number" && data.total >= 0 ? data.total : loadedCases;
    const countBaseLabel = totalCases > loadedCases
        ? `Показано ${loadedCases} из ${totalCases} ${caseNoun(totalCases)}`
        : `${loadedCases} ${caseNoun(loadedCases)}`;
    const casesCountLabel = `${countBaseLabel}${data?.has_more ? " (есть ещё)" : ""}`;

    return (
        <div className={isCompact ? "flex flex-col h-full" : "w-full"}>
            <div className={`flex flex-wrap items-center justify-between gap-3 ${filtersCompact ? "mb-2" : "mb-3"}`}>
                <div className="flex items-center gap-3">
                    <h2 className={`${headingClass} font-semibold`} data-testid="cases-title">{headingLabel}</h2>
                    {filtersCompact && (
                        <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground" data-testid="cases-count">
                            {casesCountLabel}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    {filtersCompact && (
                        <button
                            type="button"
                            onClick={() => setFiltersCollapsed((prev) => !prev)}
                            className={`text-xs font-semibold ${
                                filtersCollapsed && advancedFiltersActive ? "text-amber-700" : "text-muted-foreground hover:text-foreground"
                            }`}
                            data-testid="cases-filters-toggle"
                        >
                            {filtersToggleLabel}
                        </button>
                    )}
                    <button
                        onClick={() => { resetPagination(); refetch(); }}
                        className="text-xs text-muted-foreground hover:text-foreground"
                        data-testid="cases-refresh"
                    >
                        Обновить
                    </button>
                    <button
                        type="button"
                        onClick={() => setAutoRefreshEnabled((prev) => !prev)}
                        className={`text-xs font-semibold ${autoRefreshButtonClass}`}
                        aria-pressed={autoRefreshEnabled}
                        data-testid="cases-auto-refresh-toggle"
                    >
                        {autoRefreshLabel}
                    </button>
                    {refreshStatusLabel && (
                        <span
                            className={`text-xs ${
                                isFetching ? "text-emerald-700 animate-pulse" : "text-muted-foreground"
                            }`}
                            data-testid="cases-refresh-status"
                        >
                            {refreshStatusLabel}
                        </span>
                    )}
                </div>
            </div>

            <div
                className={filterContainerClass}
                data-testid="cases-filters"
            >
                <div className="flex w-full items-center gap-2 overflow-x-auto pb-1">
                    <input
                        type="text"
                        value={searchValue}
                        onChange={(e) => setSearchValue(e.target.value)}
                        placeholder="Телефон / имя / ID"
                        className={searchInputClass}
                        data-testid="cases-filter-search"
                    />
                    <select
                        value={filters.status || ""}
                        onChange={(e) => { resetPagination(); setFilters({ ...filters, status: e.target.value || undefined }); }}
                        className={selectClass}
                        data-testid="cases-filter-status"
                    >
                        <option value="open">Открытые</option>
                        <option value="">Все статусы</option>
                        <option value="pending">Ожидает</option>
                        <option value="active">В работе</option>
                        <option value="resolved">Закрыта</option>
                    </select>
                    {filtersCollapsed ? (
                        <select
                            value={filters.sortBy}
                            onChange={(e) => {
                                resetPagination();
                                setFilters({ ...filters, sortBy: e.target.value as CaseFilters["sortBy"] });
                            }}
                            className={selectClass}
                            data-testid="cases-filter-sort-select"
                        >
                            {sortOptions.map((option) => (
                                <option key={option.id} value={option.id}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <div className="flex items-center gap-2" data-testid="cases-filter-sort">
                            {sortOptions.map((option) => (
                                <button
                                    key={option.id}
                                    type="button"
                                    onClick={() => {
                                        resetPagination();
                                        setFilters({ ...filters, sortBy: option.id });
                                    }}
                                    className={pillClass(filters.sortBy === option.id)}
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    )}
                    <button
                        type="button"
                        onClick={() => {
                            resetPagination();
                            setFilters({ ...filters, assignedToMe: !filters.assignedToMe });
                        }}
                        className={pillClass(filters.assignedToMe)}
                        data-testid="cases-filter-assigned"
                    >
                        Мои
                    </button>
                    {!filtersCollapsed && (
                        <button
                            type="button"
                            onClick={() => setShowAdvancedFilters((prev) => !prev)}
                            className="text-xs text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60 whitespace-nowrap"
                            data-testid="cases-filter-advanced-toggle"
                            disabled={advancedFiltersActive}
                        >
                            {advancedToggleLabel}
                        </button>
                    )}
                    {(statusFilterActive || (branchFilterEnabled && filters.branchId) || filters.dateFrom || filters.dateTo || filters.assignedToMe || filters.query || filters.hasDeliveryError || filters.hasPendingOutbox || filters.hasHumanLock) && (
                        <button
                            onClick={() => {
                                setSearchValue("");
                                resetPagination();
                                setShowAdvancedFilters(false);
                                setFilters({ ...DEFAULT_FILTERS });
                            }}
                            className="text-xs text-muted-foreground hover:text-destructive whitespace-nowrap"
                            data-testid="cases-filter-clear"
                        >
                            Сбросить
                        </button>
                    )}
                </div>
                {showAdvancedFiltersRow && (
                    <div
                        className="flex w-full flex-wrap items-center gap-3 border-t border-border/60 pt-2"
                        data-testid="cases-filters-advanced"
                    >
                        {branchFilterEnabled && (
                            <select
                                value={filters.branchId || ""}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, branchId: e.target.value || undefined }); }}
                                className={selectClass}
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
                                className="px-2 py-2 border border-border/60 rounded-lg text-xs bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                                data-testid="cases-filter-date-from"
                            />
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="text-xs text-muted-foreground">По:</span>
                            <input
                                type="date"
                                value={filters.dateTo || ""}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, dateTo: e.target.value || undefined }); }}
                                className="px-2 py-2 border border-border/60 rounded-lg text-xs bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={filters.hasHumanLock}
                                onChange={(e) => { resetPagination(); setFilters({ ...filters, hasHumanLock: e.target.checked }); }}
                                className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                data-testid="cases-filter-human-lock"
                            />
                            <span className="text-sm text-foreground/80">Бот на паузе</span>
                        </label>
                    </div>
                )}
                {!filtersCompact && (
                    <div className="text-xs text-muted-foreground" data-testid="cases-count">
                        {casesCountLabel}
                    </div>
                )}
                {storageEnabled && (
                    <div className="text-[11px] text-muted-foreground" data-testid="cases-workspace-persistence">
                        Вид менеджера сохраняется 24 часа
                    </div>
                )}
            </div>

            {isCompact ? (
                <div className="flex-1 overflow-y-auto pr-1 mt-3 flex flex-col gap-2" data-testid="cases-table">
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
                        const hasHumanLock = !!c.human_lock_active;
                        const priorityChip = getPriorityChip(c.priority_tier);
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
                                    {priorityChip && (
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${priorityChip.className}`}>
                                            {priorityChip.label}
                                        </span>
                                    )}
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
                                            Нужно ответить
                                        </span>
                                    )}
                                    {isLive && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-green-100 text-green-800">
                                            Недавний диалог
                                        </span>
                                    )}
                                    {hasHumanLock && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-amber-100 text-amber-800">
                                            Пауза
                                        </span>
                                    )}
                                    {hasIssue && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-red-100 text-red-800">
                                            Ошибка
                                        </span>
                                    )}
                                    {c.attention_reason && (
                                        <span className="px-2 py-0.5 rounded font-semibold bg-primary/10 text-primary">
                                            {c.attention_reason}
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
                                const priorityChip = getPriorityChip(c.priority_tier);
                                return (
                                    <tr key={c.id} className="border-b border-border/60 hover:bg-muted/60" data-testid="cases-row">
                                        <td className="p-4 font-mono text-sm">{c.id.slice(0, 8)}...</td>
                                        <td className="p-4">
                                            <div className="flex flex-wrap items-center gap-2">
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
                                                {c.human_lock_active && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                                                        Пауза
                                                    </span>
                                                )}
                                                {priorityChip && (
                                                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${priorityChip.className}`}>
                                                        {priorityChip.label}
                                                    </span>
                                                )}
                                            </div>
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
                                                        Нужно ответить
                                                    </span>
                                                )}
                                                {isLive && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800">
                                                        Недавний диалог
                                                    </span>
                                                )}
                                                {hasIssue && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-800">
                                                        Ошибка
                                                    </span>
                                                )}
                                                {c.attention_reason && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
                                                        {c.attention_reason}
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
