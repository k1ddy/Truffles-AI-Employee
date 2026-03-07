"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/useAuthenticatedApi";
import Link from "next/link";
import { Case } from "@/types";
import { getCaseBusinessStatusBadge, getCaseSlaIndicator } from "@/utils/labels";
import {
    casesApi,
    type CaseAssigneeOption,
    type CaseBulkActionResponse,
} from "@/lib/api-client";
import {
    type InboxCaseFilters,
    type InboxCaseListPrefs,
    type InboxCaseVisibleField,
    type InboxCaseVisibleFields,
    type InboxQueueViewId,
    normalizeInboxQueueViewId,
    readInboxCaseListPrefs,
    writeInboxCaseListPrefs,
} from "@/lib/inbox-workspace";
import toast from "react-hot-toast";

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
type BulkActionMode = "reassign" | "route" | "snooze" | null;
type QueueViewDefinition = {
    id: InboxQueueViewId;
    label: string;
    description: string;
    privileged?: boolean;
    serverView?: "needs_reply" | "waiting_client" | "snoozed" | "delivery" | "unassigned";
    applyFilters: (prev: CaseFilters) => CaseFilters;
    matchesFilters: (filters: CaseFilters) => boolean;
};

function resolveServerQueueView(viewId: InboxQueueViewId): QueueViewDefinition["serverView"] {
    if (
        viewId === "needs_reply"
        || viewId === "waiting_client"
        || viewId === "snoozed"
        || viewId === "delivery"
        || viewId === "unassigned"
    ) {
        return viewId;
    }
    return undefined;
}

interface CaseListProps {
    variant?: CaseListVariant;
    selectedCaseId?: string | null;
    onSelectCase?: (caseId: string) => void;
    branches?: Branch[];
    showBranchFilter?: boolean;
    workspaceScope?: string | null;
    onCaseIdsChange?: (caseIds: string[]) => void;
    canBulkManage?: boolean;
    viewerRole?: string;
}

interface BulkSummary {
    tone: "success" | "warning" | "error";
    label: string;
    detail: string;
}

const DEFAULT_FILTERS: CaseFilters = {
    status: "open",
    branchId: undefined,
    assignedToMe: false,
    assigneeId: undefined,
    unassigned: false,
    query: undefined,
    hasDeliveryError: false,
    hasPendingOutbox: false,
    hasHumanLock: false,
    dateFrom: undefined,
    dateTo: undefined,
    sortBy: "activity",
};

const DEFAULT_VISIBLE_FIELDS: InboxCaseVisibleFields = {
    branch: true,
    owner: false,
    channel: false,
    activity: true,
    priority: false,
};

const FIELD_ORDER: InboxCaseVisibleField[] = ["branch", "owner", "channel", "activity", "priority"];
const FIELD_LABELS: Record<InboxCaseVisibleField, string> = {
    branch: "Филиал",
    owner: "Менеджер",
    channel: "Канал",
    activity: "Активность",
    priority: "Приоритет",
};

const BULK_SNOOZE_PRESETS = [30, 60, 120];

function caseNoun(count: number) {
    if (count === 1) {
        return "заявка";
    }
    return count < 5 ? "заявки" : "заявок";
}

function sortAssigneeOptionsByLoad(options: CaseAssigneeOption[]) {
    return [...options].sort((left, right) => {
        const leftLoad = left.open_case_count ?? 0;
        const rightLoad = right.open_case_count ?? 0;
        if (leftLoad !== rightLoad) {
            return leftLoad - rightLoad;
        }
        return left.agent_name.localeCompare(right.agent_name, "ru");
    });
}

function sortAssigneeOptionsByName(options: CaseAssigneeOption[]) {
    return [...options].sort((left, right) => left.agent_name.localeCompare(right.agent_name, "ru"));
}

function formatQueueAssigneeOptionLabel(option: CaseAssigneeOption) {
    return `${option.agent_name} · ${option.open_case_count ?? 0} в работе`;
}

function formatBulkAssigneeOptionLabel(option: CaseAssigneeOption) {
    return `${option.agent_name} · ${option.open_case_count ?? 0} в работе`;
}

function bulkToggleClass(active: boolean) {
    return `rounded-full border px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${
        active
            ? "border-primary bg-primary/5 text-primary"
            : "border-border/60 text-foreground"
    }`;
}

function resolveRecommendedAssignee(options: CaseAssigneeOption[]) {
    if (options.length === 0) {
        return null;
    }
    return [...options].sort((left, right) => {
        const leftLoad = left.open_case_count ?? 0;
        const rightLoad = right.open_case_count ?? 0;
        if (leftLoad !== rightLoad) {
            return leftLoad - rightLoad;
        }
        return left.agent_name.localeCompare(right.agent_name, "ru");
    })[0];
}

function buildBulkSummary(response: CaseBulkActionResponse): BulkSummary {
    const parts: string[] = [];
    if (response.processed_count > 0) {
        const processedVerb = response.action === "route"
            ? "распределили"
            : response.action === "snooze"
                ? "отложили"
                : "обновили";
        parts.push(`${processedVerb} ${response.processed_count}`);
    }
    if (response.skipped_count > 0) {
        parts.push(`без изменений ${response.skipped_count}`);
    }
    if (response.failed_count > 0) {
        parts.push(`ошибки ${response.failed_count}`);
    }
    const tone = response.failed_count > 0
        ? "error"
        : response.skipped_count > 0
            ? "warning"
            : "success";
    return {
        tone,
        label: parts.length > 0
            ? `${parts.join(", ")} ${caseNoun(response.requested_count)}`
            : "Изменений нет",
        detail: "Необработанные заявки остаются отмеченными, чтобы их можно было разобрать отдельно.",
    };
}

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

function formatCompactActivityLabel(value: string) {
    return new Date(value).toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function isPrivilegedQueueRole(role?: string): boolean {
    return role === "owner" || role === "admin" || role === "platform_admin";
}

function matchesGovernedFilters(filters: CaseFilters, target: Partial<CaseFilters>): boolean {
    return (
        (target.status ?? DEFAULT_FILTERS.status) === filters.status
        && (target.assignedToMe ?? DEFAULT_FILTERS.assignedToMe) === filters.assignedToMe
        && (target.assigneeId ?? DEFAULT_FILTERS.assigneeId) === filters.assigneeId
        && (target.unassigned ?? DEFAULT_FILTERS.unassigned) === filters.unassigned
        && (target.hasDeliveryError ?? DEFAULT_FILTERS.hasDeliveryError) === filters.hasDeliveryError
        && (target.hasPendingOutbox ?? DEFAULT_FILTERS.hasPendingOutbox) === filters.hasPendingOutbox
        && (target.hasHumanLock ?? DEFAULT_FILTERS.hasHumanLock) === filters.hasHumanLock
        && (target.sortBy ?? DEFAULT_FILTERS.sortBy) === filters.sortBy
    );
}

function normalizeVisibleFields(raw?: InboxCaseVisibleFields | null): InboxCaseVisibleFields {
    if (!raw || typeof raw !== "object") {
        return { ...DEFAULT_VISIBLE_FIELDS };
    }
    return {
        branch: typeof raw.branch === "boolean" ? raw.branch : DEFAULT_VISIBLE_FIELDS.branch,
        owner: typeof raw.owner === "boolean" ? raw.owner : DEFAULT_VISIBLE_FIELDS.owner,
        channel: typeof raw.channel === "boolean" ? raw.channel : DEFAULT_VISIBLE_FIELDS.channel,
        activity: typeof raw.activity === "boolean" ? raw.activity : DEFAULT_VISIBLE_FIELDS.activity,
        priority: typeof raw.priority === "boolean" ? raw.priority : DEFAULT_VISIBLE_FIELDS.priority,
    };
}

function buildQueueViews(privileged: boolean): QueueViewDefinition[] {
    const sharedViews: QueueViewDefinition[] = [
        {
            id: "all_open",
            label: "Все открытые",
            description: "Базовая очередь для менеджера.",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
        },
        {
            id: "mine",
            label: "Мои",
            description: "Только заявки текущего менеджера.",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: true,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: true,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
        },
        {
            id: "needs_reply",
            label: "Требуют ответа",
            description: "Срочный фокус на кейсах, где клиент ждёт менеджера.",
            serverView: "needs_reply",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "sla",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "sla",
            }),
        },
        {
            id: "waiting_client",
            label: "Ждём клиента",
            description: "Диалоги, где менеджер уже ответил и ждёт следующий шаг клиента.",
            serverView: "waiting_client",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
        },
        {
            id: "snoozed",
            label: "Отложенные",
            description: "Диалоги, которые менеджер сознательно отложил до следующего срока.",
            serverView: "snoozed",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: true,
                sortBy: "activity",
            }),
        },
        {
            id: "delivery",
            label: "Проблемы доставки",
            description: "Ошибки отправки и зависшие исходящие.",
            serverView: "delivery",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: false,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
        },
    ];

    if (!privileged) {
        return sharedViews;
    }

    return [
        ...sharedViews,
        {
            id: "unassigned",
            label: "Без владельца",
            description: "Быстрый срез для супервизора по кейсам без ответственного.",
            privileged: true,
            serverView: "unassigned",
            applyFilters: (prev) => ({
                ...prev,
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: true,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
            matchesFilters: (filters) => matchesGovernedFilters(filters, {
                status: "open",
                assignedToMe: false,
                assigneeId: undefined,
                unassigned: true,
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: "activity",
            }),
        },
    ];
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
    const rawActiveViewId = raw.activeViewId as string | undefined;
    const normalizedActiveViewId = normalizeInboxQueueViewId(rawActiveViewId);
    const legacyPausedView = rawActiveViewId === "paused";
    return {
        filters: {
            status: filters.status,
            branchId: filters.branchId,
            assignedToMe: Boolean(filters.assignedToMe),
            assigneeId: typeof filters.assigneeId === "string" ? filters.assigneeId : undefined,
            unassigned: Boolean(filters.unassigned),
            query: filters.query,
            hasDeliveryError: Boolean(filters.hasDeliveryError),
            hasPendingOutbox: Boolean(filters.hasPendingOutbox),
            hasHumanLock: legacyPausedView ? false : Boolean(filters.hasHumanLock),
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            sortBy,
        },
        searchValue: typeof raw.searchValue === "string" ? raw.searchValue : "",
        showAdvancedFilters: Boolean(raw.showAdvancedFilters),
        filtersCollapsed: Boolean(raw.filtersCollapsed),
        autoRefreshEnabled: typeof raw.autoRefreshEnabled === "boolean" ? raw.autoRefreshEnabled : true,
        activeViewId: normalizedActiveViewId,
        visibleFields: normalizeVisibleFields(raw.visibleFields),
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
    canBulkManage = false,
    viewerRole = "manager",
}: CaseListProps) {
    const { data: session } = useSession();
    const api = useAuthenticatedApi();
    const queryClient = useQueryClient();
    const storageEnabled = Boolean(workspaceScope);
    const [stateReady, setStateReady] = useState(!storageEnabled);

    const [filters, setFilters] = useState<CaseFilters>(DEFAULT_FILTERS);
    const [cursor, setCursor] = useState<string | undefined>(undefined);
    const [caseItems, setCaseItems] = useState<Case[]>([]);
    const [searchValue, setSearchValue] = useState("");
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const [filtersCollapsed, setFiltersCollapsed] = useState(false);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
    const [activeViewId, setActiveViewId] = useState<InboxQueueViewId>("all_open");
    const [visibleFields, setVisibleFields] = useState<InboxCaseVisibleFields>(DEFAULT_VISIBLE_FIELDS);
    const [fieldPanelOpen, setFieldPanelOpen] = useState(false);
    const [documentVisible, setDocumentVisible] = useState(true);
    const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
    const [bulkActionMode, setBulkActionMode] = useState<BulkActionMode>(null);
    const [bulkAssigneeId, setBulkAssigneeId] = useState("");
    const [bulkSnoozeMinutes, setBulkSnoozeMinutes] = useState(60);
    const [bulkSnoozeReason, setBulkSnoozeReason] = useState("");
    const [bulkSummary, setBulkSummary] = useState<BulkSummary | null>(null);
    const isCompact = variant === "compact";
    const filtersCompact = isCompact && !!selectedCaseId;
    const headingLabel = isCompact ? "Очередь" : "Заявки";
    const queueViews = useMemo(
        () => buildQueueViews(isPrivilegedQueueRole(viewerRole)),
        [viewerRole],
    );
    const queueViewMap = useMemo(
        () => new Map(queueViews.map((view) => [view.id, view])),
        [queueViews],
    );
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
            setActiveViewId(restored.activeViewId ?? "all_open");
            setVisibleFields(normalizeVisibleFields(restored.visibleFields));
            setCursor(undefined);
            setCaseItems([]);
        }
        setStateReady(true);
    }, [workspaceScope]);

    useEffect(() => {
        if (queueViewMap.has(activeViewId)) {
            return;
        }
        setActiveViewId("all_open");
    }, [activeViewId, queueViewMap]);

    useEffect(() => {
        const handle = setTimeout(() => {
            const nextQuery = searchValue.trim() || undefined;
            if (filters.query === nextQuery) {
                return;
            }
            setCursor(undefined);
            setCaseItems([]);
            setFilters((prev) => ({
                ...prev,
                query: nextQuery,
            }));
        }, 300);
        return () => clearTimeout(handle);
    }, [filters.query, searchValue]);

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
    const privilegedOwnerFilterVisible = isPrivilegedQueueRole(viewerRole);
    const branchFilterEnabled = showBranchFilter && selectableBranches.length > 1;
    const activeQueueView = queueViewMap.get(activeViewId) ?? queueViewMap.get("all_open") ?? queueViews[0];
    const activeServerQueueView = resolveServerQueueView(activeViewId);
    const queueViewHasManualOverrides = activeQueueView ? !activeQueueView.matchesFilters(filters) : false;
    const ownerFilterLabel = filters.unassigned
        ? "Без владельца"
        : filters.assigneeId
            ? null
            : "Все владельцы";
    const statusFilterActive = filters.status !== "open";
    const advancedFiltersActive = Boolean(
        filters.branchId
        || filters.assigneeId
        || filters.unassigned
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
    const hasAnyFiltersApplied = Boolean(
        activeViewId !== "all_open"
        || statusFilterActive
        || (branchFilterEnabled && filters.branchId)
        || filters.dateFrom
        || filters.dateTo
        || filters.assignedToMe
        || filters.assigneeId
        || filters.unassigned
        || filters.query
        || filters.hasDeliveryError
        || filters.hasPendingOutbox
        || filters.hasHumanLock
    );
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
    const compactSearchInputClass = "w-full rounded-xl border border-border/60 bg-card px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
    const compactSelectClass = "w-full min-w-0 rounded-xl border border-border/60 bg-card px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
    const compactPrimaryGridClass = "grid w-full gap-2 sm:grid-cols-2";

    const pillClass = (active: boolean) => (
        `rounded-full border px-3 py-1 text-xs font-semibold transition ${
            active
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border/60 text-muted-foreground hover:text-foreground"
        }`
    );
    const enabledFieldCount = FIELD_ORDER.filter((field) => visibleFields[field]).length;

    useEffect(() => {
        if (!filtersCompact) {
            setFiltersCollapsed(false);
            return;
        }
        if (advancedFiltersActive && filtersCollapsed) {
            setFiltersCollapsed(false);
        }
    }, [filtersCompact, advancedFiltersActive, filtersCollapsed]);

    useEffect(() => {
        if (!branchFilterEnabled && filters.branchId) {
            setCursor(undefined);
            setCaseItems([]);
            setFilters((prev) => ({ ...prev, branchId: undefined }));
        }
    }, [branchFilterEnabled, filters.branchId]);

    const { data, isLoading, error, refetch, isFetching, dataUpdatedAt } = useQuery({
        queryKey: ["cases", filters, activeServerQueueView || activeViewId, cursor],
        queryFn: async (): Promise<CasesResponse> => {
            const buildParams = (includeSort: boolean) => {
                const params = new URLSearchParams();
                if (filters.status) params.append("status", filters.status);
                if (filters.branchId) params.append("branch_id", filters.branchId);
                if (filters.assignedToMe) params.append("assigned_to_me", "true");
                if (filters.assigneeId) params.append("assignee_id", filters.assigneeId);
                if (filters.unassigned) params.append("unassigned", "true");
                if (filters.query) params.append("q", filters.query);
                if (filters.hasDeliveryError) params.append("has_delivery_error", "true");
                if (filters.hasPendingOutbox) params.append("has_pending_outbox", "true");
                if (filters.hasHumanLock) params.append("has_human_lock", "true");
                if (filters.dateFrom) params.append("date_from", filters.dateFrom);
                if (filters.dateTo) params.append("date_to", filters.dateTo);
                if (activeServerQueueView) params.append("queue_view", activeServerQueueView);
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
    const visibleCases = sortedCases;
    const selectedCaseIdSet = useMemo(() => new Set(selectedCaseIds), [selectedCaseIds]);
    const selectedCases = useMemo(
        () => visibleCases.filter((item) => selectedCaseIdSet.has(item.id)),
        [selectedCaseIdSet, visibleCases],
    );
    const selectedBranchIds = useMemo(
        () => Array.from(
            new Set(
                selectedCases
                    .map((item) => item.branch_id)
                    .filter((branchId): branchId is string => Boolean(branchId))
            )
        ),
        [selectedCases],
    );
    const bulkAssigneeSourceCaseId = selectedBranchIds.length === 1
        ? selectedCases.find((item) => item.branch_id === selectedBranchIds[0])?.id
        : undefined;
    const bulkBranchLabel = selectedBranchIds.length === 1
        ? branchMap.get(selectedBranchIds[0]) || selectedBranchIds[0]
        : null;
    const allVisibleSelected = visibleCases.length > 0 && visibleCases.every((item) => selectedCaseIdSet.has(item.id));
    const bulkReassignDisabledReason = selectedCases.length === 0
        ? "Выберите заявки"
        : selectedBranchIds.length > 1
            ? "Для передачи выберите заявки одного филиала"
            : null;
    const bulkRouteDisabledReason = selectedCases.length === 0
        ? "Выберите заявки"
        : selectedBranchIds.length > 1
            ? "Для распределения выберите заявки одного филиала"
            : null;

    const { data: bulkAssigneesData, isFetching: assigneesLoading } = useQuery({
        queryKey: ["case-assignees-bulk", bulkAssigneeSourceCaseId],
        queryFn: async () => {
            if (!bulkAssigneeSourceCaseId) {
                return { items: [] as CaseAssigneeOption[] };
            }
            const response = await casesApi.listAssignees(bulkAssigneeSourceCaseId);
            return response.data;
        },
        enabled: canBulkManage && bulkActionMode === "reassign" && !!bulkAssigneeSourceCaseId,
    });
    const bulkAssignees = useMemo(
        () => sortAssigneeOptionsByLoad(bulkAssigneesData?.items ?? []),
        [bulkAssigneesData?.items],
    );
    const { data: queueAssigneesData, isFetching: queueAssigneesLoading } = useQuery({
        queryKey: ["case-assignees-queue", filters.branchId || "all", viewerRole],
        queryFn: async () => {
            const response = await casesApi.listQueueAssignees(filters.branchId);
            return response.data;
        },
        enabled: privilegedOwnerFilterVisible,
    });
    const queueAssignees = useMemo(
        () => sortAssigneeOptionsByName(queueAssigneesData?.items ?? []),
        [queueAssigneesData?.items],
    );
    const recommendedBulkAssignee = useMemo(
        () => resolveRecommendedAssignee(bulkAssignees),
        [bulkAssignees],
    );
    const selectedAssigneeLabel = filters.assigneeId
        ? queueAssignees.find((item) => String(item.agent_id) === filters.assigneeId)?.agent_name ?? filters.assigneeId
        : ownerFilterLabel;

    const bulkActionMutation = useMutation({
        mutationFn: async () => {
            if (selectedCaseIds.length === 0 || !bulkActionMode) {
                throw new Error("Выберите заявки и действие");
            }
            if (bulkActionMode === "route") {
                const response = await casesApi.bulkAction({
                    action: "route",
                    case_ids: selectedCaseIds,
                    policy: "least_open_cases",
                });
                return response.data;
            }
            if (bulkActionMode === "reassign") {
                const agentId = bulkAssigneeId.trim();
                if (!agentId) {
                    throw new Error("Выберите менеджера");
                }
                const response = await casesApi.bulkAction({
                    action: "reassign",
                    case_ids: selectedCaseIds,
                    agent_id: agentId,
                });
                return response.data;
            }
            const minutes = Math.min(Math.max(Number(bulkSnoozeMinutes) || 0, 1), 1440);
            const response = await casesApi.bulkAction({
                action: "snooze",
                case_ids: selectedCaseIds,
                minutes,
                reason: bulkSnoozeReason.trim() || undefined,
            });
            return response.data;
        },
        onSuccess: (response) => {
            const summary = buildBulkSummary(response);
            const remainingIds = response.items
                .filter((item) => item.status !== "processed")
                .map((item) => item.case_id);
            setBulkSummary(summary);
            setSelectedCaseIds(remainingIds);
            setBulkActionMode(remainingIds.length > 0 ? bulkActionMode : null);
            setBulkAssigneeId("");
            if (response.processed_count > 0) {
                resetPagination();
            }
            void queryClient.invalidateQueries({ queryKey: ["cases"] });
            if (selectedCaseId && selectedCaseIdSet.has(selectedCaseId)) {
                void queryClient.invalidateQueries({ queryKey: ["case", selectedCaseId] });
            }
            if (summary.tone === "error") {
                toast.error(summary.label);
            } else if (summary.tone === "warning") {
                toast(summary.label);
            } else {
                toast.success(summary.label);
            }
        },
        onError: (error) => {
            const message = (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message
                || (error as Error)?.message
                || "Не удалось выполнить массовое действие";
            toast.error(message);
        },
    });

    useEffect(() => {
        const visibleIds = new Set(visibleCases.map((item) => item.id));
        setSelectedCaseIds((prev) => {
            const next = prev.filter((caseId) => visibleIds.has(caseId));
            return next.length === prev.length ? prev : next;
        });
    }, [visibleCases]);

    useEffect(() => {
        if (selectedCaseIds.length > 0) {
            return;
        }
        setBulkActionMode(null);
        setBulkAssigneeId("");
    }, [selectedCaseIds.length]);

    useEffect(() => {
        if (bulkActionMode !== "reassign") {
            setBulkAssigneeId("");
        }
    }, [bulkActionMode]);

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
            activeViewId,
            visibleFields,
        });
    }, [workspaceScope, stateReady, filters, searchValue, showAdvancedFilters, filtersCollapsed, autoRefreshEnabled, activeViewId, visibleFields]);

    useEffect(() => {
        if (!onCaseIdsChange) {
            return;
        }
        onCaseIdsChange(
            visibleCases
                .map((item) => item.id)
                .filter((item): item is string => Boolean(item))
        );
    }, [onCaseIdsChange, visibleCases]);

    const loadMore = () => {
        if (data?.cursor) {
            setCursor(data.cursor);
        }
    };

    const resetPagination = () => {
        setCursor(undefined);
    };

    const applyQueueView = (viewId: InboxQueueViewId) => {
        const nextView = queueViewMap.get(viewId);
        if (!nextView) {
            return;
        }
        setBulkSummary(null);
        resetPagination();
        setSelectedCaseIds([]);
        setActiveViewId(viewId);
        setFilters((prev) => nextView.applyFilters(prev));
    };

    const updateVisibleField = (field: InboxCaseVisibleField, enabled: boolean) => {
        setVisibleFields((prev) => ({
            ...prev,
            [field]: enabled,
        }));
    };

    const clearBulkSelection = () => {
        setSelectedCaseIds([]);
        setBulkSummary(null);
        setBulkActionMode(null);
        setBulkAssigneeId("");
    };

    const toggleCaseSelection = (caseId: string) => {
        setBulkSummary(null);
        setSelectedCaseIds((prev) => (
            prev.includes(caseId)
                ? prev.filter((item) => item !== caseId)
                : [...prev, caseId]
        ));
    };

    const toggleSelectAllVisible = () => {
        setBulkSummary(null);
        const visibleIds = visibleCases.map((item) => item.id);
        if (visibleIds.length === 0) {
            return;
        }
        setSelectedCaseIds((prev) => {
            const prevSet = new Set(prev);
            if (visibleIds.every((caseId) => prevSet.has(caseId))) {
                return prev.filter((caseId) => !visibleIds.includes(caseId));
            }
            const next = [...prev];
            visibleIds.forEach((caseId) => {
                if (!prevSet.has(caseId)) {
                    next.push(caseId);
                }
            });
            return next;
        });
    };

    const resetAllFilters = () => {
        setSearchValue("");
        setShowAdvancedFilters(false);
        setSelectedCaseIds([]);
        setBulkSummary(null);
        setFieldPanelOpen(false);
        resetPagination();
        setActiveViewId("all_open");
        setFilters({ ...DEFAULT_FILTERS });
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

    const loadedCases = visibleCases.length;
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
                    <button
                        type="button"
                        onClick={() => setFieldPanelOpen((prev) => !prev)}
                        className="text-xs font-semibold text-muted-foreground hover:text-foreground"
                        data-testid="cases-field-toggle"
                    >
                        Вид {enabledFieldCount}/{FIELD_ORDER.length}
                    </button>
                    {canBulkManage && visibleCases.length > 0 && (
                        <button
                            type="button"
                            onClick={toggleSelectAllVisible}
                            className="text-xs font-semibold text-muted-foreground hover:text-foreground"
                            data-testid="cases-bulk-select-all"
                        >
                            {allVisibleSelected ? "Снять выбор" : "Выбрать все"}
                        </button>
                    )}
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
                </div>
            </div>

            <div
                className={filterContainerClass}
                data-testid="cases-filters"
            >
                <div className="flex w-full flex-wrap items-center gap-2 border-b border-border/60 pb-2" data-testid="cases-queue-views">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        Режимы
                    </span>
                    {queueViews.map((view) => (
                        <button
                            key={view.id}
                            type="button"
                            onClick={() => applyQueueView(view.id)}
                            className={pillClass(activeViewId === view.id)}
                            data-testid={`cases-queue-view-${view.id}`}
                        >
                            {view.label}
                        </button>
                    ))}
                </div>
                {isCompact ? (
                    <div className="grid w-full gap-3" data-testid="cases-filter-compact-layout">
                        <input
                            type="text"
                            value={searchValue}
                            onChange={(e) => setSearchValue(e.target.value)}
                            placeholder="Телефон / имя / ID"
                            className={compactSearchInputClass}
                            data-testid="cases-filter-search"
                        />
                        {!filtersCollapsed && (
                            <div className={compactPrimaryGridClass}>
                                <label className="space-y-1">
                                    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                        Статус
                                    </span>
                                    <select
                                        value={filters.status || ""}
                                        onChange={(e) => { resetPagination(); setFilters({ ...filters, status: e.target.value || undefined }); }}
                                        className={compactSelectClass}
                                        data-testid="cases-filter-status"
                                    >
                                        <option value="open">Открытые</option>
                                        <option value="">Все статусы</option>
                                        <option value="pending">Ожидает</option>
                                        <option value="active">В работе</option>
                                        <option value="resolved">Закрыта</option>
                                    </select>
                                </label>
                                <label className="space-y-1">
                                    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                        Сортировка
                                    </span>
                                    <select
                                        value={filters.sortBy}
                                        onChange={(e) => {
                                            resetPagination();
                                            setFilters({ ...filters, sortBy: e.target.value as CaseFilters["sortBy"] });
                                        }}
                                        className={compactSelectClass}
                                        data-testid="cases-filter-sort-select"
                                    >
                                        {sortOptions.map((option) => (
                                            <option key={option.id} value={option.id}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                {privilegedOwnerFilterVisible && (
                                    <label className="space-y-1 sm:col-span-2">
                                        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                            Владелец
                                        </span>
                                        <select
                                            value={filters.unassigned ? "__unassigned__" : filters.assigneeId || ""}
                                            onChange={(event) => {
                                                const nextValue = event.target.value;
                                                resetPagination();
                                                setFilters({
                                                    ...filters,
                                                    assignedToMe: false,
                                                    assigneeId: nextValue && nextValue !== "__unassigned__" ? nextValue : undefined,
                                                    unassigned: nextValue === "__unassigned__",
                                                });
                                            }}
                                            className={compactSelectClass}
                                            disabled={queueAssigneesLoading}
                                            data-testid="cases-filter-assignee"
                                        >
                                            <option value="">Все владельцы</option>
                                            <option value="__unassigned__">Без владельца</option>
                                            {queueAssignees.map((option) => (
                                                <option key={option.agent_id} value={String(option.agent_id)}>
                                                    {formatQueueAssigneeOptionLabel(option)}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                )}
                            </div>
                        )}
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => {
                                    resetPagination();
                                    setFilters({
                                        ...filters,
                                        assignedToMe: !filters.assignedToMe,
                                        assigneeId: undefined,
                                        unassigned: false,
                                    });
                                }}
                                className={pillClass(filters.assignedToMe)}
                                data-testid="cases-filter-assigned"
                            >
                                Мои
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowAdvancedFilters((prev) => !prev)}
                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                                data-testid="cases-filter-advanced-toggle"
                                disabled={advancedFiltersActive}
                            >
                                {advancedToggleLabel}
                            </button>
                            {hasAnyFiltersApplied && (
                                <button
                                    onClick={resetAllFilters}
                                    className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-destructive"
                                    data-testid="cases-filter-clear"
                                >
                                    Сбросить
                                </button>
                            )}
                        </div>
                    </div>
                ) : (
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
                                setFilters({
                                    ...filters,
                                    assignedToMe: !filters.assignedToMe,
                                    assigneeId: undefined,
                                    unassigned: false,
                                });
                            }}
                            className={pillClass(filters.assignedToMe)}
                            data-testid="cases-filter-assigned"
                        >
                            Мои
                        </button>
                        {privilegedOwnerFilterVisible && (
                            <select
                                value={filters.unassigned ? "__unassigned__" : filters.assigneeId || ""}
                                onChange={(event) => {
                                    const nextValue = event.target.value;
                                    resetPagination();
                                    setFilters({
                                        ...filters,
                                        assignedToMe: false,
                                        assigneeId: nextValue && nextValue !== "__unassigned__" ? nextValue : undefined,
                                        unassigned: nextValue === "__unassigned__",
                                    });
                                }}
                                className={selectClass}
                                disabled={queueAssigneesLoading}
                                data-testid="cases-filter-assignee"
                            >
                                <option value="">Все владельцы</option>
                                <option value="__unassigned__">Без владельца</option>
                                {queueAssignees.map((option) => (
                                    <option key={option.agent_id} value={String(option.agent_id)}>
                                        {formatQueueAssigneeOptionLabel(option)}
                                    </option>
                                ))}
                            </select>
                        )}
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
                        {hasAnyFiltersApplied && (
                            <button
                                onClick={resetAllFilters}
                                className="text-xs text-muted-foreground hover:text-destructive whitespace-nowrap"
                                data-testid="cases-filter-clear"
                            >
                                Сбросить
                            </button>
                        )}
                    </div>
                )}
                <div className="flex flex-wrap items-center gap-2 text-[11px]" data-testid="cases-queue-view-summary">
                    <span className="rounded-full bg-primary/10 px-2 py-1 font-semibold text-primary">
                        {activeQueueView?.label ?? "Все открытые"}
                    </span>
                    {queueViewHasManualOverrides && (
                        <span className="font-semibold text-amber-700">
                            Есть ручные фильтры поверх режима
                        </span>
                    )}
                    {(filters.assigneeId || filters.unassigned) && (
                        <span className="rounded-full bg-slate-100 px-2 py-1 font-semibold text-slate-700" data-testid="cases-owner-summary">
                            {selectedAssigneeLabel}
                        </span>
                    )}
                    {refreshStatusLabel && (
                        <span
                            className={`text-muted-foreground ${
                                isFetching ? "animate-pulse text-emerald-700" : ""
                            }`}
                            data-testid="cases-refresh-status"
                        >
                            {refreshStatusLabel}
                        </span>
                    )}
                </div>
                {fieldPanelOpen && (
                    <div className="grid w-full gap-3 border-t border-border/60 pt-3 md:grid-cols-[1fr_auto]" data-testid="cases-field-panel">
                        <div className="flex flex-wrap items-center gap-3">
                            {FIELD_ORDER.map((field) => (
                                <label key={field} className="flex items-center gap-2 text-xs text-foreground/80">
                                    <input
                                        type="checkbox"
                                        checked={visibleFields[field]}
                                        onChange={(event) => updateVisibleField(field, event.target.checked)}
                                        className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        data-testid={`cases-field-${field}`}
                                    />
                                    {FIELD_LABELS[field]}
                                </label>
                            ))}
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                            <button
                                type="button"
                                onClick={() => setAutoRefreshEnabled((prev) => !prev)}
                                className={`font-semibold ${autoRefreshButtonClass}`}
                                aria-pressed={autoRefreshEnabled}
                                data-testid="cases-auto-refresh-toggle"
                            >
                                {autoRefreshLabel}
                            </button>
                        </div>
                    </div>
                )}
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

            {canBulkManage && selectedCases.length > 0 && (
                <div
                    className="mt-3 rounded-xl border border-border/60 bg-card p-3"
                    data-testid="cases-bulk-toolbar"
                >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1">
                            <p className="text-sm font-semibold" data-testid="cases-bulk-count">
                                Выбрано {selectedCases.length} {caseNoun(selectedCases.length)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {bulkBranchLabel
                                    ? `Передача и распределение доступны для филиала ${bulkBranchLabel}. Отсрочка работает для всей выборки.`
                                    : "Для передачи и распределения выберите заявки одного филиала. Отсрочка доступна для всей выборки."}
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => {
                                    setBulkSummary(null);
                                    setBulkActionMode((current) => current === "reassign" ? null : "reassign");
                                }}
                                disabled={!!bulkReassignDisabledReason || bulkActionMutation.isPending}
                                className={bulkToggleClass(bulkActionMode === "reassign")}
                                data-testid="cases-bulk-toggle-reassign"
                            >
                                Передать
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setBulkSummary(null);
                                    setBulkActionMode((current) => current === "route" ? null : "route");
                                }}
                                disabled={!!bulkRouteDisabledReason || bulkActionMutation.isPending}
                                className={bulkToggleClass(bulkActionMode === "route")}
                                data-testid="cases-bulk-toggle-route"
                            >
                                Распределить
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setBulkSummary(null);
                                    setBulkActionMode((current) => current === "snooze" ? null : "snooze");
                                }}
                                disabled={bulkActionMutation.isPending}
                                className={bulkToggleClass(bulkActionMode === "snooze")}
                                data-testid="cases-bulk-toggle-snooze"
                            >
                                Отложить
                            </button>
                            <button
                                type="button"
                                onClick={clearBulkSelection}
                                disabled={bulkActionMutation.isPending}
                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                data-testid="cases-bulk-clear"
                            >
                                Снять выбор
                            </button>
                        </div>
                    </div>

                    {bulkActionMode === "route" && (
                        <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-3" data-testid="cases-bulk-route-panel">
                            {bulkRouteDisabledReason ? (
                                <p className="text-xs text-amber-700" data-testid="cases-bulk-route-hint">
                                    {bulkRouteDisabledReason}
                                </p>
                            ) : (
                                <div className="flex flex-col gap-3">
                                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3">
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-900/70">
                                            Политика
                                        </p>
                                        <p className="mt-1 text-sm font-semibold text-emerald-950">
                                            Меньше всего открытых заявок
                                        </p>
                                        <p className="mt-1 text-xs text-emerald-900/80">
                                            Сервер сам распределит выборку внутри одного филиала и сохранит текущего владельца, если нагрузка уже минимальная.
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap justify-end gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setBulkActionMode(null)}
                                            disabled={bulkActionMutation.isPending}
                                            className="rounded-full border border-border/60 px-4 py-2 text-xs font-semibold text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Отмена
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => bulkActionMutation.mutate()}
                                            disabled={bulkActionMutation.isPending}
                                            className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                            data-testid="cases-bulk-route-submit"
                                        >
                                            {bulkActionMutation.isPending ? "Распределяем..." : "Распределить по политике"}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {bulkActionMode === "reassign" && (
                        <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-3" data-testid="cases-bulk-reassign-panel">
                            {bulkReassignDisabledReason ? (
                                <p className="text-xs text-amber-700" data-testid="cases-bulk-reassign-hint">
                                    {bulkReassignDisabledReason}
                                </p>
                            ) : (
                                <div className="flex flex-col gap-3">
                                    {recommendedBulkAssignee && (
                                        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3">
                                            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-900/70">
                                                Рекомендуем
                                            </p>
                                            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                                                <p
                                                    className="text-xs text-emerald-900"
                                                    data-testid="cases-bulk-reassign-recommendation"
                                                >
                                                    {recommendedBulkAssignee.agent_name} · {recommendedBulkAssignee.open_case_count ?? 0} в работе.
                                                </p>
                                                <button
                                                    type="button"
                                                    onClick={() => setBulkAssigneeId(String(recommendedBulkAssignee.agent_id))}
                                                    className="rounded-full border border-emerald-200 bg-white px-3 py-2 text-xs font-semibold text-emerald-900"
                                                    disabled={assigneesLoading || bulkActionMutation.isPending || bulkAssigneeId === String(recommendedBulkAssignee.agent_id)}
                                                    data-testid="cases-bulk-reassign-recommend"
                                                >
                                                    {bulkAssigneeId === String(recommendedBulkAssignee.agent_id)
                                                        ? "Рекомендация выбрана"
                                                        : `Выбрать ${recommendedBulkAssignee.agent_name}`}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                                        <select
                                            value={bulkAssigneeId}
                                            onChange={(event) => setBulkAssigneeId(event.target.value)}
                                            className="min-w-[220px] rounded-lg border border-border/60 bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            disabled={assigneesLoading || bulkActionMutation.isPending}
                                            data-testid="cases-bulk-reassign-select"
                                        >
                                            <option value="">Выберите менеджера</option>
                                            {bulkAssignees.map((option) => (
                                                <option key={option.agent_id} value={option.agent_id}>
                                                    {formatBulkAssigneeOptionLabel(option)}
                                                </option>
                                            ))}
                                        </select>
                                        <button
                                            type="button"
                                            onClick={() => bulkActionMutation.mutate()}
                                            disabled={!bulkAssigneeId || assigneesLoading || bulkActionMutation.isPending}
                                            className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                            data-testid="cases-bulk-reassign-submit"
                                        >
                                            {bulkActionMutation.isPending ? "Передаём..." : "Передать выбранному"}
                                        </button>
                                    </div>
                                    <div className="flex flex-wrap justify-end gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setBulkActionMode(null)}
                                            disabled={bulkActionMutation.isPending}
                                            className="rounded-full border border-border/60 px-4 py-2 text-xs font-semibold text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Отмена
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {bulkActionMode === "snooze" && (
                        <div className="mt-3 rounded-lg border border-border/60 bg-muted/30 p-3" data-testid="cases-bulk-snooze-panel">
                            <div className="flex flex-col gap-3">
                                <div className="flex flex-wrap items-center gap-2">
                                    <input
                                        type="number"
                                        min={1}
                                        max={1440}
                                        value={bulkSnoozeMinutes}
                                        onChange={(event) => {
                                            const next = Number(event.target.value);
                                            const normalized = Number.isFinite(next)
                                                ? Math.min(Math.max(next, 1), 1440)
                                                : 30;
                                            setBulkSnoozeMinutes(normalized);
                                        }}
                                        className="w-28 rounded-lg border border-border/60 bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        data-testid="cases-bulk-snooze-minutes"
                                    />
                                    <span className="text-xs text-muted-foreground">минут</span>
                                    {BULK_SNOOZE_PRESETS.map((preset) => (
                                        <button
                                            key={preset}
                                            type="button"
                                            onClick={() => setBulkSnoozeMinutes(preset)}
                                            className="rounded-full border border-border/60 px-3 py-1.5 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
                                            data-testid={`cases-bulk-snooze-preset-${preset}`}
                                        >
                                            {preset}
                                        </button>
                                    ))}
                                </div>
                                <input
                                    type="text"
                                    value={bulkSnoozeReason}
                                    onChange={(event) => setBulkSnoozeReason(event.target.value)}
                                    className="rounded-lg border border-border/60 bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    placeholder="Причина для команды, например: ждём подтверждение клиента"
                                    data-testid="cases-bulk-snooze-reason"
                                />
                                <div className="flex flex-wrap items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setBulkActionMode(null)}
                                        disabled={bulkActionMutation.isPending}
                                        className="rounded-full border border-border/60 px-4 py-2 text-xs font-semibold text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Отмена
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => bulkActionMutation.mutate()}
                                        disabled={bulkActionMutation.isPending}
                                        className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                        data-testid="cases-bulk-snooze-submit"
                                    >
                                        {bulkActionMutation.isPending ? "Сохраняем..." : "Отложить выборку"}
                                    </button>
                                    <p className="text-xs text-muted-foreground">
                                        Отсрочка убирает заявки из срочного фокуса, но не закрывает их.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {bulkSummary && (
                        <div
                            className={`mt-3 rounded-lg px-3 py-2 text-xs ${
                                bulkSummary.tone === "success"
                                    ? "bg-emerald-50 text-emerald-800"
                                    : bulkSummary.tone === "warning"
                                        ? "bg-amber-50 text-amber-800"
                                        : "bg-red-50 text-red-800"
                            }`}
                            data-testid="cases-bulk-summary"
                        >
                            <p className="font-semibold">{bulkSummary.label}</p>
                            <p>{bulkSummary.detail}</p>
                        </div>
                    )}
                </div>
            )}

            {isCompact ? (
                <div className="mt-3 flex flex-1 flex-col gap-3 overflow-y-auto pr-1" data-testid="cases-table">
                    {visibleCases.map((c) => {
                        const sla = getCaseSlaIndicator(c);
                        const businessStatus = getCaseBusinessStatusBadge(c);
                        const branchName = branchMap.get(c.branch_id || "") || "-";
                        const lastActivity = c.last_activity_at || c.last_inbound_at || c.created_at;
                        const activityLabel = formatCompactActivityLabel(lastActivity);
                        const contactName = c.customer_name || c.customer_phone || c.customer_remote_jid?.split("@")[0] || "Клиент";
                        const contactPhone = c.customer_phone || c.customer_remote_jid?.split("@")[0] || "";
                        const preview = c.last_message_preview || c.user_message || "-";
                        const isSelected = selectedCaseId === c.id;
                        const isBulkSelected = selectedCaseIdSet.has(c.id);
                        const priorityChip = getPriorityChip(c.priority_tier);
                        const secondaryAttention = c.attention_reason && !sla.state?.startsWith("reply") && sla.state !== "overdue"
                            ? c.attention_reason
                            : null;
                        const ownerLabel = c.assigned_to_name || "Без владельца";
                        const metaParts = [
                            visibleFields.branch ? branchName : null,
                            visibleFields.owner ? ownerLabel : null,
                            visibleFields.activity ? activityLabel : null,
                            visibleFields.channel ? c.channel : null,
                            visibleFields.priority && priorityChip ? priorityChip.label : null,
                        ].filter(Boolean);
                        const content = (
                            <div
                                className={`rounded-2xl border border-border/60 p-4 text-left transition ${
                                    isSelected ? "border-primary/60 bg-primary/5 shadow-sm" : "bg-card hover:bg-muted/60"
                                } ${isBulkSelected && !isSelected ? "border-amber-300 bg-amber-50/70" : ""}`}
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0 space-y-1">
                                        <p className="truncate text-sm font-semibold text-foreground">{contactName}</p>
                                        <p className="text-[11px] text-muted-foreground">
                                            {contactPhone || `Заявка ${c.id.slice(0, 8)}`}
                                        </p>
                                    </div>
                                    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${businessStatus.className}`} data-testid="cases-business-status">
                                        {businessStatus.label}
                                    </span>
                                </div>
                                <p className="mt-3 text-xs leading-relaxed text-foreground/80">
                                    {preview}
                                </p>
                                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
                                    <span className={`rounded-full px-2 py-1 font-semibold ${sla.className}`}>
                                        {sla.label}
                                    </span>
                                    {metaParts.slice(0, 2).map((part) => (
                                        <span key={part} className="text-muted-foreground">
                                            {part}
                                        </span>
                                    ))}
                                </div>
                                {metaParts.length > 2 && (
                                    <p className="mt-2 text-[11px] text-muted-foreground">
                                        {metaParts.slice(2).join(" · ")}
                                    </p>
                                )}
                                {secondaryAttention && (
                                    <p className="mt-2 text-[11px] font-medium text-amber-700">
                                        {secondaryAttention}
                                    </p>
                                )}
                            </div>
                        );
                        const rowContent = onSelectCase ? (
                            <button
                                type="button"
                                onClick={() => onSelectCase(c.id)}
                                className="flex-1 text-left"
                                data-testid="cases-row"
                            >
                                {content}
                            </button>
                        ) : (
                            <Link key={c.id} href={`/cases/${c.id}`} className="flex-1" data-testid="cases-row">
                                {content}
                            </Link>
                        );
                        return (
                            <div key={c.id} className="flex items-start gap-2">
                                {canBulkManage && (
                                    <label className="mt-3 flex h-5 w-5 items-center justify-center">
                                        <input
                                            type="checkbox"
                                            checked={isBulkSelected}
                                            onChange={() => toggleCaseSelection(c.id)}
                                            className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                            data-testid="cases-bulk-select"
                                        />
                                    </label>
                                )}
                                {rowContent}
                            </div>
                        );
                    })}
                    {visibleCases.length === 0 && (
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
                                {canBulkManage && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">
                                        <input
                                            type="checkbox"
                                            checked={allVisibleSelected}
                                            onChange={toggleSelectAllVisible}
                                            className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                            data-testid="cases-bulk-select-all-table"
                                        />
                                    </th>
                                )}
                                <th className="p-4 text-sm font-medium text-muted-foreground">ID</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Статус</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">SLA</th>
                                {visibleFields.branch && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">Филиал</th>
                                )}
                                {visibleFields.channel && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">Канал</th>
                                )}
                                {visibleFields.owner && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">Назначено</th>
                                )}
                                {visibleFields.priority && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">Приоритет</th>
                                )}
                                <th className="p-4 text-sm font-medium text-muted-foreground">Сообщение</th>
                                {visibleFields.activity && (
                                    <th className="p-4 text-sm font-medium text-muted-foreground">Активность</th>
                                )}
                                <th className="p-4 text-sm font-medium text-muted-foreground">Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {visibleCases.map((c) => {
                                const sla = getCaseSlaIndicator(c);
                                const businessStatus = getCaseBusinessStatusBadge(c);
                                const branchName = branchMap.get(c.branch_id || "") || "-";
                                const lastInbound = c.last_inbound_at ? new Date(c.last_inbound_at) : null;
                                const lastActivity = c.last_activity_at || c.last_inbound_at || c.created_at;
                                const isLive = lastInbound ? (Date.now() - lastInbound.getTime()) < 5 * 60 * 1000 : false;
                                const hasIssue = !!c.has_delivery_error || !!c.has_pending_outbox;
                                const priorityChip = getPriorityChip(c.priority_tier);
                                const isBulkSelected = selectedCaseIdSet.has(c.id);
                                return (
                                    <tr
                                        key={c.id}
                                        className={`border-b border-border/60 hover:bg-muted/60 ${isBulkSelected ? "bg-amber-50/60" : ""}`}
                                        data-testid="cases-row"
                                    >
                                        {canBulkManage && (
                                            <td className="p-4">
                                                <input
                                                    type="checkbox"
                                                    checked={isBulkSelected}
                                                    onChange={() => toggleCaseSelection(c.id)}
                                                    className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                                    data-testid="cases-bulk-select"
                                                />
                                            </td>
                                        )}
                                        <td className="p-4 font-mono text-sm">{c.id.slice(0, 8)}...</td>
                                        <td className="p-4">
                                            <div className="flex flex-col gap-1">
                                                <span
                                                    className={`inline-flex w-fit px-2 py-1 rounded text-xs font-medium ${businessStatus.className}`}
                                                    data-testid="cases-business-status"
                                                >
                                                    {businessStatus.label}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${sla.className}`}>
                                                {sla.label}
                                            </span>
                                        </td>
                                        {visibleFields.branch && <td className="p-4 text-sm">{branchName}</td>}
                                        {visibleFields.channel && <td className="p-4 text-sm">{c.channel}</td>}
                                        {visibleFields.owner && <td className="p-4 text-sm">{c.assigned_to_name || "Без владельца"}</td>}
                                        {visibleFields.priority && (
                                            <td className="p-4 text-sm">
                                                {priorityChip ? (
                                                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${priorityChip.className}`}>
                                                        {priorityChip.label}
                                                    </span>
                                                ) : (
                                                    "-"
                                                )}
                                            </td>
                                        )}
                                        <td className="p-4 text-sm max-w-xs">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="truncate max-w-[180px]">{c.last_message_preview || c.user_message || "-"}</span>
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
                                                {c.attention_reason && !sla.state?.startsWith("reply") && sla.state !== "overdue" && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary">
                                                        {c.attention_reason}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        {visibleFields.activity && (
                                            <td className="p-4 text-sm text-muted-foreground">
                                                <div className="flex flex-col">
                                                    <span>{new Date(lastActivity).toLocaleString("ru-RU")}</span>
                                                    <span className="text-xs text-muted-foreground">
                                                        {c.last_activity_channel || "—"}
                                                    </span>
                                                </div>
                                            </td>
                                        )}
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
                            {visibleCases.length === 0 && (
                                <tr>
                                    <td
                                        colSpan={1 + (canBulkManage ? 1 : 0) + (visibleFields.branch ? 1 : 0) + (visibleFields.channel ? 1 : 0) + (visibleFields.owner ? 1 : 0) + (visibleFields.priority ? 1 : 0) + (visibleFields.activity ? 1 : 0) + 4}
                                        className="p-8 text-center text-muted-foreground"
                                        data-testid="cases-empty"
                                    >
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
