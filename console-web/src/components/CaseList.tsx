"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/useAuthenticatedApi";
import Link from "next/link";
import { Case } from "@/types";
import { getCaseBusinessStatusBadge, getCaseSlaIndicator } from "@/utils/labels";
import {
    casesApi,
    canAccessConsole,
    DEFAULT_CASE_ROUTING_POLICY,
    type CaseAssigneeOption,
    type CaseBulkActionResponse,
    type CaseRoutingPolicy,
    type ConsoleRole,
    type QueueSavedView,
    queueStateApi,
} from "@/lib/api-client";
import {
    buildCaseListSearchParams,
    buildOwnerScopeOptions,
    DEFAULT_OWNER_SCOPE,
    deriveModeScopeFromLegacyStatus,
    getDefaultSortForModeScope,
    hasAdvancedCaseRefinements,
    hasAnyCaseFiltersApplied,
    normalizeOwnerScopeForRole,
    normalizeStoredSortBy,
    ownerScopeToSelectValue,
    parseOwnerScopeValue,
    resolveEffectiveSortBy,
    resolveOwnerScopeLabel,
} from "@/lib/inbox-case-filters";
import {
    type InboxCaseFilters,
    type InboxCaseListPrefs,
    type InboxCaseModeScope,
    type InboxCaseVisibleField,
    type InboxCaseVisibleFields,
    type InboxOwnerScope,
    type InboxQueueViewId,
    normalizeInboxCaseModeScope,
    normalizeInboxOwnerScope,
    normalizeInboxQueueViewId,
    readInboxCaseListPrefs,
    writeInboxCaseListPrefs,
} from "@/lib/inbox-workspace";
import {
    buildCasesQueueHref,
    buildCasesQueueStatePayload,
    findPreferredDefaultSavedView,
    findSavedViewByFingerprint,
    getCasesQueueStateFingerprint,
    getSavedViewFingerprint,
    isTeamSavedView,
    readCasesQueueStateFromServer,
    readCasesQueueStateFromSavedView,
    readCasesQueueStateFromUrl,
    readQueueStateViewIdFromUrl,
    type CasesQueueStateSnapshot,
} from "@/lib/queue-state";
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
    serverView?: "needs_reply" | "waiting_client" | "snoozed" | "delivery";
};
type ModeScopeDefinition = {
    id: InboxCaseModeScope;
    label: string;
    description: string;
};

function resolveServerQueueView(viewId: InboxQueueViewId): QueueViewDefinition["serverView"] {
    if (
        viewId === "needs_reply"
        || viewId === "waiting_client"
        || viewId === "snoozed"
        || viewId === "delivery"
    ) {
        return viewId;
    }
    return undefined;
}

function buildModeScopes(): ModeScopeDefinition[] {
    return [
        {
            id: "open",
            label: "Открытые",
            description: "Текущая операционная очередь для работы менеджера.",
        },
        {
            id: "resolved",
            label: "Закрытые",
            description: "Уже завершённые заявки и недавняя история.",
        },
        {
            id: "all",
            label: "Все",
            description: "Общий поиск по открытым и закрытым заявкам.",
        },
    ];
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
    status: undefined,
    branchId: undefined,
    query: undefined,
    hasDeliveryError: false,
    hasPendingOutbox: false,
    hasHumanLock: false,
    dateFrom: undefined,
    dateTo: undefined,
    sortBy: undefined,
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
const SAVED_VIEW_SCOPE_LABELS = {
    personal: "Личный",
    team: "Команда",
} as const;
const SAVED_VIEW_ROLE_LABELS: Record<ConsoleRole, string> = {
    platform_admin: "Платформа",
    owner: "Owner",
    admin: "Админ",
    manager: "Менеджер",
    support: "Поддержка",
    specialist: "Специалист",
    viewer: "Наблюдатель",
};
const SAVED_VIEW_TARGET_ROLES: ConsoleRole[] = [
    "platform_admin",
    "owner",
    "admin",
    "manager",
    "support",
    "specialist",
    "viewer",
];

const CASE_ROUTING_POLICY_LABELS: Record<CaseRoutingPolicy, string> = {
    follow_up_sla_balance: "Follow-up + SLA баланс",
    least_open_cases: "Меньше всего открытых заявок",
};

const CASE_ROUTING_POLICY_HINTS: Record<CaseRoutingPolicy, string> = {
    follow_up_sla_balance: "Сохраняет continuity по no-show follow-up и жёстче учитывает нагрузку, если у заявки уже появился SLA-риск.",
    least_open_cases: "Распределяет только по текущему числу открытых заявок и сохраняет владельца при равной нагрузке.",
};

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

function getCasePrimaryTimelineBadge(caseItem: Case, modeScope: InboxCaseModeScope) {
    const resolvedLabel = caseItem.resolved_at
        ? `Закрыта ${formatCompactActivityLabel(caseItem.resolved_at)}`
        : "Закрыта";
    if (modeScope === "resolved" || (modeScope === "all" && caseItem.status === "resolved")) {
        return {
            label: resolvedLabel,
            className: "bg-emerald-100 text-emerald-900",
            state: "resolved",
        };
    }
    return getCaseSlaIndicator(caseItem);
}

function getCaseActivityValue(caseItem: Case, modeScope: InboxCaseModeScope) {
    if (modeScope === "resolved" && caseItem.resolved_at) {
        return caseItem.resolved_at;
    }
    if (modeScope === "all" && caseItem.status === "resolved" && caseItem.resolved_at) {
        return caseItem.resolved_at;
    }
    return caseItem.last_activity_at || caseItem.last_inbound_at || caseItem.created_at;
}

function isPrivilegedQueueRole(role?: string): boolean {
    return role === "owner" || role === "admin" || role === "platform_admin";
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

function buildQueueViews(): QueueViewDefinition[] {
    const sharedViews: QueueViewDefinition[] = [
        {
            id: "all_open",
            label: "Все открытые",
            description: "Базовая очередь для менеджера.",
        },
        {
            id: "needs_reply",
            label: "Требуют ответа",
            description: "Срочный фокус на кейсах, где клиент ждёт менеджера.",
            serverView: "needs_reply",
        },
        {
            id: "waiting_client",
            label: "Ждём клиента",
            description: "Диалоги, где менеджер уже ответил и ждёт следующий шаг клиента.",
            serverView: "waiting_client",
        },
        {
            id: "snoozed",
            label: "Отложенные",
            description: "Диалоги, которые менеджер сознательно отложил до следующего срока.",
            serverView: "snoozed",
        },
        {
            id: "delivery",
            label: "Проблемы доставки",
            description: "Ошибки отправки и зависшие исходящие.",
            serverView: "delivery",
        },
    ];
    return sharedViews;
}

function getApiErrorMessage(error: unknown, fallback: string): string {
    return (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message
        || (error as Error)?.message
        || fallback;
}

async function copyText(text: string): Promise<void> {
    try {
        await navigator.clipboard.writeText(text);
        return;
    } catch {
        window.prompt("Скопируйте ссылку", text);
    }
}

function getSavedViewBranchLabel(branchId: string | null | undefined, branchMap: Map<string, string>): string | null {
    if (!branchId) {
        return null;
    }
    return branchMap.get(branchId) ?? branchId;
}

function getSavedViewRoleLabel(role: string | null | undefined): string | null {
    if (!role) {
        return null;
    }
    return SAVED_VIEW_ROLE_LABELS[role as ConsoleRole] ?? role;
}

function buildSavedViewOptionLabel(view: QueueSavedView, branchMap: Map<string, string>): string {
    const parts = [view.name, SAVED_VIEW_SCOPE_LABELS[view.scope ?? "personal"]];
    const branchLabel = getSavedViewBranchLabel(view.target_branch_id, branchMap);
    const roleLabel = getSavedViewRoleLabel(view.target_role);
    if (branchLabel) {
        parts.push(branchLabel);
    }
    if (roleLabel) {
        parts.push(roleLabel);
    }
    if (view.is_default) {
        parts.push("default");
    }
    if (isTeamSavedView(view) && view.is_applicable === false) {
        parts.push("вне текущего контура");
    }
    return parts.join(" · ");
}

function countMatchingSavedViews(
    savedViews: QueueSavedView[],
    {
        scope,
        targetBranchId,
        targetRole,
    }: {
        scope: "personal" | "team";
        targetBranchId: string;
        targetRole: string;
    },
): number {
    return savedViews.filter((view) => {
        if ((view.scope ?? "personal") !== scope) {
            return false;
        }
        if (scope === "personal") {
            return true;
        }
        return (view.target_branch_id ?? "") === targetBranchId
            && (view.target_role ?? "") === targetRole;
    }).length;
}

function hasDefaultSavedViewForTarget(
    savedViews: QueueSavedView[],
    {
        scope,
        targetBranchId,
        targetRole,
    }: {
        scope: "personal" | "team";
        targetBranchId: string;
        targetRole: string;
    },
): boolean {
    return savedViews.some((view) => {
        if (!view.is_default || (view.scope ?? "personal") !== scope) {
            return false;
        }
        if (scope === "personal") {
            return true;
        }
        return (view.target_branch_id ?? "") === targetBranchId
            && (view.target_role ?? "") === targetRole;
    });
}

function normalizeStoredPrefs(
    raw: InboxCaseListPrefs | null,
    {
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
    }: {
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
    },
): InboxCaseListPrefs | null {
    if (!raw || typeof raw !== "object") {
        return null;
    }
    const filters = raw.filters;
    if (!filters || typeof filters !== "object") {
        return null;
    }
    const rawActiveViewId = raw.activeViewId as string | undefined;
    const activeViewId = normalizeInboxQueueViewId(rawActiveViewId);
    const modeScope = normalizeInboxCaseModeScope(
        raw.modeScope ?? deriveModeScopeFromLegacyStatus(filters.status),
    );
    const legacyFilters = raw.filters as Partial<{
        assignedToMe: boolean;
        assigneeId: string;
        unassigned: boolean;
    }>;
    const rawOwnerScope = raw.ownerScope
        ? normalizeInboxOwnerScope(raw.ownerScope)
        : legacyFilters.assignedToMe
            ? { kind: "mine" as const }
            : legacyFilters.unassigned
                ? { kind: "unassigned" as const }
                : typeof legacyFilters.assigneeId === "string" && legacyFilters.assigneeId
                    ? { kind: "agent" as const, agentId: legacyFilters.assigneeId }
                    : { ...DEFAULT_OWNER_SCOPE };
    const ownerScope = normalizeOwnerScopeForRole(rawOwnerScope, privilegedOwnerFilterVisible);
    const normalizedFilters: InboxCaseFilters = {
        status: undefined,
        branchId: branchFilterEnabled && typeof filters.branchId === "string" && filters.branchId.trim()
            ? filters.branchId
            : undefined,
        query: typeof filters.query === "string" && filters.query.trim()
            ? filters.query.trim()
            : undefined,
        hasDeliveryError: modeScope === "open" ? Boolean(filters.hasDeliveryError) : false,
        hasPendingOutbox: modeScope === "open" ? Boolean(filters.hasPendingOutbox) : false,
        hasHumanLock: modeScope === "open" && rawActiveViewId !== "paused" ? Boolean(filters.hasHumanLock) : false,
        dateFrom: typeof filters.dateFrom === "string" && filters.dateFrom ? filters.dateFrom : undefined,
        dateTo: typeof filters.dateTo === "string" && filters.dateTo ? filters.dateTo : undefined,
        sortBy: normalizeStoredSortBy(filters.sortBy, { activeViewId, modeScope }),
    };
    return {
        filters: normalizedFilters,
        ownerScope,
        modeScope,
        searchValue: typeof raw.searchValue === "string" ? raw.searchValue : normalizedFilters.query ?? "",
        showAdvancedFilters: Boolean(raw.showAdvancedFilters),
        filtersCollapsed: Boolean(raw.filtersCollapsed),
        autoRefreshEnabled: typeof raw.autoRefreshEnabled === "boolean" ? raw.autoRefreshEnabled : true,
        activeViewId,
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
    const searchParams = useSearchParams();
    const api = useAuthenticatedApi();
    const queryClient = useQueryClient();
    const storageEnabled = Boolean(workspaceScope);
    const [stateReady, setStateReady] = useState(!storageEnabled);
    const restoredQueueStateRef = useRef<string | null>(null);
    const lastSavedQueueStateRef = useRef<string>("");
    const saveViewInputRef = useRef<HTMLInputElement | null>(null);
    const hasToken = !!(session as { accessToken?: string } | null)?.accessToken;

    const [filters, setFilters] = useState<CaseFilters>(DEFAULT_FILTERS);
    const [ownerScope, setOwnerScope] = useState<InboxOwnerScope>(DEFAULT_OWNER_SCOPE);
    const [cursor, setCursor] = useState<string | undefined>(undefined);
    const [caseItems, setCaseItems] = useState<Case[]>([]);
    const [searchValue, setSearchValue] = useState("");
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
    const [filtersCollapsed, setFiltersCollapsed] = useState(false);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
    const [modeScope, setModeScope] = useState<InboxCaseModeScope>("open");
    const [activeViewId, setActiveViewId] = useState<InboxQueueViewId>("all_open");
    const [activeSavedViewId, setActiveSavedViewId] = useState<string | null>(null);
    const [saveViewDraftName, setSaveViewDraftName] = useState("");
    const [saveViewComposerOpen, setSaveViewComposerOpen] = useState(false);
    const [saveViewScopeDraft, setSaveViewScopeDraft] = useState<"personal" | "team">("personal");
    const [saveViewTargetBranchIdDraft, setSaveViewTargetBranchIdDraft] = useState("");
    const [saveViewTargetRoleDraft, setSaveViewTargetRoleDraft] = useState<ConsoleRole | "">("");
    const [saveViewDefaultDraft, setSaveViewDefaultDraft] = useState(false);
    const [saveViewDefaultTouched, setSaveViewDefaultTouched] = useState(false);
    const [selectedTeamTargetBranchIdDraft, setSelectedTeamTargetBranchIdDraft] = useState("");
    const [selectedTeamTargetRoleDraft, setSelectedTeamTargetRoleDraft] = useState<ConsoleRole | "">("");
    const [visibleFields, setVisibleFields] = useState<InboxCaseVisibleFields>(DEFAULT_VISIBLE_FIELDS);
    const [fieldPanelOpen, setFieldPanelOpen] = useState(false);
    const [documentVisible, setDocumentVisible] = useState(true);
    const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
    const [bulkActionMode, setBulkActionMode] = useState<BulkActionMode>(null);
    const [bulkRoutingPolicy, setBulkRoutingPolicy] = useState<CaseRoutingPolicy>(DEFAULT_CASE_ROUTING_POLICY);
    const [bulkAssigneeId, setBulkAssigneeId] = useState("");
    const [bulkSnoozeMinutes, setBulkSnoozeMinutes] = useState(60);
    const [bulkSnoozeReason, setBulkSnoozeReason] = useState("");
    const [bulkSummary, setBulkSummary] = useState<BulkSummary | null>(null);
    const isCompact = variant === "compact";
    const filtersCompact = isCompact && !!selectedCaseId;
    const headingLabel = isCompact ? "Очередь" : "Заявки";
    const modeScopes = useMemo(
        () => buildModeScopes(),
        [],
    );
    const queueViews = useMemo(
        () => buildQueueViews(),
        [],
    );
    const queueViewMap = useMemo(
        () => new Map(queueViews.map((view) => [view.id, view])),
        [queueViews],
    );
    const sortOptions: { id: NonNullable<CaseFilters["sortBy"]>; label: string }[] = [
        { id: "activity", label: "По активности" },
        { id: "created_at", label: "По созданию" },
        { id: "resolved_at", label: "По закрытию" },
        { id: "sla", label: "По SLA" },
    ];
    const selectableBranches = branches.filter((branch) => !!branch.id);
    const branchMap = new Map(
        selectableBranches.map((branch) => [branch.id as string, branch.name ?? branch.id as string])
    );
    const canManageTeamPresets = canAccessConsole(viewerRole, "team", "write");
    const savedViewTargetRoleOptions = useMemo(
        () => SAVED_VIEW_TARGET_ROLES.filter((role) => canAccessConsole(role, "inbox", "read")),
        [],
    );
    const privilegedOwnerFilterVisible = isPrivilegedQueueRole(viewerRole);
    const branchFilterEnabled = showBranchFilter && selectableBranches.length > 1;
    const urlSavedViewId = useMemo(
        () => readQueueStateViewIdFromUrl(searchParams),
        [searchParams],
    );
    const urlQueueState = useMemo(
        () =>
            readCasesQueueStateFromUrl(searchParams, {
                branchFilterEnabled,
                privilegedOwnerFilterVisible,
            }),
        [branchFilterEnabled, privilegedOwnerFilterVisible, searchParams],
    );
    const urlQueueStateKey = useMemo(
        () => JSON.stringify({
            viewId: urlSavedViewId,
            queueState: urlQueueState ?? null,
        }),
        [urlQueueState, urlSavedViewId],
    );
    const resetPagination = () => {
        setCursor(undefined);
    };

    useEffect(() => {
        restoredQueueStateRef.current = null;
        lastSavedQueueStateRef.current = "";
        setActiveSavedViewId(null);
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        setSelectedTeamTargetBranchIdDraft("");
        setSelectedTeamTargetRoleDraft("");
        setStateReady(!workspaceScope);
    }, [urlQueueStateKey, workspaceScope]);

    const currentQueueStateQuery = useQuery({
        queryKey: ["queue-state", "cases", workspaceScope],
        queryFn: async () => {
            const response = await api.get("/queue-state/current", {
                params: { surface: "cases" },
            });
            return response.data as {
                found?: boolean;
                query_state?: Record<string, unknown> | null;
                updated_at?: string | null;
            };
        },
        enabled: hasToken && !!workspaceScope,
        retry: 1,
        staleTime: 60_000,
    });
    const savedViewsQuery = useQuery({
        queryKey: ["queue-state-views", "cases"],
        queryFn: async () => {
            const response = await queueStateApi.listViews("cases");
            return response.data;
        },
        enabled: hasToken,
        retry: 1,
        staleTime: 60_000,
    });
    const urlSavedViewQuery = useQuery({
        queryKey: ["queue-state-view", "cases", urlSavedViewId],
        queryFn: async () => {
            const response = await queueStateApi.getView(urlSavedViewId as string);
            return response.data;
        },
        enabled: hasToken && !!urlSavedViewId,
        retry: false,
        staleTime: 60_000,
    });
    const savedViews = useMemo(
        () => savedViewsQuery.data?.items ?? [],
        [savedViewsQuery.data?.items],
    );
    const defaultSavedView = useMemo(
        () => findPreferredDefaultSavedView(savedViews),
        [savedViews],
    );
    const personalSavedViews = useMemo(
        () => savedViews.filter((view) => !isTeamSavedView(view)),
        [savedViews],
    );
    const teamSavedViews = useMemo(
        () => savedViews.filter((view) => isTeamSavedView(view)),
        [savedViews],
    );
    const urlSavedView = useMemo(
        () => urlSavedViewQuery.data ?? savedViews.find((view) => view.id === urlSavedViewId) ?? null,
        [savedViews, urlSavedViewId, urlSavedViewQuery.data],
    );

    useEffect(() => {
        if (!workspaceScope) {
            setStateReady(true);
            return;
        }
        const restoreKey = `${workspaceScope}::${urlQueueStateKey}`;
        const currentQueueStateSettled = Boolean(urlQueueState)
            || !hasToken
            || currentQueueStateQuery.isFetched
            || currentQueueStateQuery.isError;
        const savedViewsSettled = !hasToken || savedViewsQuery.isFetched || savedViewsQuery.isError;
        const urlSavedViewSettled = !urlSavedViewId || urlSavedViewQuery.isFetched || urlSavedViewQuery.isError;
        if (
            !currentQueueStateSettled
            || !savedViewsSettled
            || !urlSavedViewSettled
            || restoredQueueStateRef.current === restoreKey
        ) {
            return;
        }
        const restored = normalizeStoredPrefs(readInboxCaseListPrefs(workspaceScope), {
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
        });
        const localSnapshot: CasesQueueStateSnapshot | null = restored
            ? {
                filters: restored.filters,
                ownerScope: restored.ownerScope ? normalizeInboxOwnerScope(restored.ownerScope) : { ...DEFAULT_OWNER_SCOPE },
                modeScope: restored.modeScope ?? "open",
                activeViewId: restored.activeViewId ?? "all_open",
                searchValue: restored.searchValue,
            }
            : null;
        const serverSnapshot = readCasesQueueStateFromServer(currentQueueStateQuery.data, {
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
        });
        const urlSavedViewSnapshot = readCasesQueueStateFromSavedView(urlSavedView, {
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
        });
        const defaultSavedViewSnapshot = readCasesQueueStateFromSavedView(defaultSavedView, {
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
        });
        const queueSnapshot = urlQueueState ?? urlSavedViewSnapshot ?? serverSnapshot ?? defaultSavedViewSnapshot ?? localSnapshot;
        const source = urlQueueState
            ? "url"
            : urlSavedViewSnapshot
                ? "url_view"
            : serverSnapshot
                ? "server"
                : defaultSavedViewSnapshot
                    ? "saved_default"
                    : localSnapshot
                    ? "local"
                    : "default";
        const matchedSavedView = (urlSavedView && (source === "url" || source === "url_view"))
            ? urlSavedView
            : source === "saved_default"
            ? defaultSavedView
            : queueSnapshot
                ? findSavedViewByFingerprint(
                    savedViews,
                    getCasesQueueStateFingerprint(queueSnapshot, { branchFilterEnabled }),
                    { includeNonApplicableTeam: false },
                )
                : null;

        if (queueSnapshot) {
            setFilters(queueSnapshot.filters);
            setOwnerScope(queueSnapshot.ownerScope);
            setModeScope(queueSnapshot.modeScope);
            setSearchValue(queueSnapshot.searchValue);
            setActiveViewId(queueSnapshot.activeViewId);
            setActiveSavedViewId(matchedSavedView?.id ?? null);
        } else {
            setFilters(DEFAULT_FILTERS);
            setOwnerScope({ ...DEFAULT_OWNER_SCOPE });
            setModeScope("open");
            setSearchValue("");
            setActiveViewId("all_open");
            setActiveSavedViewId(null);
        }
        setShowAdvancedFilters(
            source === "local" && restored
                ? restored.showAdvancedFilters
                : Boolean(
                    restored?.showAdvancedFilters
                    || (
                        queueSnapshot
                        && (
                            queueSnapshot.modeScope !== "open"
                            || hasAdvancedCaseRefinements(queueSnapshot.filters, { branchFilterEnabled })
                        )
                    )
                ),
        );
        setFiltersCollapsed(restored?.filtersCollapsed ?? false);
        setAutoRefreshEnabled(restored?.autoRefreshEnabled ?? true);
        setVisibleFields(normalizeVisibleFields(restored?.visibleFields));
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        setCursor(undefined);
        setCaseItems([]);
        if (source === "server" && queueSnapshot) {
            lastSavedQueueStateRef.current = JSON.stringify({
                surface: "cases",
                version: 1,
                query_state: buildCasesQueueStatePayload(queueSnapshot, { branchFilterEnabled }),
            });
        }
        restoredQueueStateRef.current = restoreKey;
        setStateReady(true);
    }, [
        branchFilterEnabled,
        currentQueueStateQuery.data,
        currentQueueStateQuery.isError,
        currentQueueStateQuery.isFetched,
        hasToken,
        privilegedOwnerFilterVisible,
        defaultSavedView,
        savedViews,
        savedViewsQuery.isError,
        savedViewsQuery.isFetched,
        urlSavedView,
        urlSavedViewId,
        urlSavedViewQuery.isError,
        urlSavedViewQuery.isFetched,
        urlQueueState,
        urlQueueStateKey,
        workspaceScope,
    ]);

    useEffect(() => {
        if (queueViewMap.has(activeViewId)) {
            return;
        }
        setActiveViewId("all_open");
    }, [activeViewId, queueViewMap]);

    useEffect(() => {
        if (!saveViewComposerOpen) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            saveViewInputRef.current?.focus();
            saveViewInputRef.current?.select();
        }, 0);
        return () => window.clearTimeout(timeoutId);
    }, [saveViewComposerOpen]);

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

    const activeMode = modeScopes.find((scope) => scope.id === modeScope) ?? modeScopes[0];
    const activeQueueView = queueViewMap.get(activeViewId) ?? queueViewMap.get("all_open") ?? queueViews[0];
    const activeServerQueueView = modeScope === "open" ? resolveServerQueueView(activeViewId) : undefined;
    const effectiveOwnerScope = useMemo(
        () => normalizeOwnerScopeForRole(ownerScope, privilegedOwnerFilterVisible),
        [ownerScope, privilegedOwnerFilterVisible],
    );
    const effectiveFilters = useMemo<CaseFilters>(
        () => ({
            status: undefined,
            branchId: branchFilterEnabled ? filters.branchId : undefined,
            query: typeof filters.query === "string" && filters.query.trim()
                ? filters.query.trim()
                : undefined,
            hasDeliveryError: modeScope === "open" ? Boolean(filters.hasDeliveryError) : false,
            hasPendingOutbox: modeScope === "open" ? Boolean(filters.hasPendingOutbox) : false,
            hasHumanLock: modeScope === "open" ? Boolean(filters.hasHumanLock) : false,
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            sortBy: normalizeStoredSortBy(filters.sortBy, { activeViewId, modeScope }),
        }),
        [activeViewId, branchFilterEnabled, filters, modeScope],
    );
    const currentQueueSnapshot = useMemo<CasesQueueStateSnapshot>(
        () => ({
            filters: effectiveFilters,
            ownerScope: effectiveOwnerScope,
            modeScope,
            activeViewId,
            searchValue: effectiveFilters.query ?? searchValue,
        }),
        [activeViewId, effectiveFilters, effectiveOwnerScope, modeScope, searchValue],
    );
    const currentQueueFingerprint = useMemo(
        () => getCasesQueueStateFingerprint(currentQueueSnapshot, { branchFilterEnabled }),
        [branchFilterEnabled, currentQueueSnapshot],
    );
    const selectedSavedView = useMemo(
        () => savedViews.find((view) => view.id === activeSavedViewId) ?? null,
        [activeSavedViewId, savedViews],
    );
    const matchingScopeSavedViewCount = useMemo(
        () => countMatchingSavedViews(savedViews, {
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        }),
        [saveViewScopeDraft, saveViewTargetBranchIdDraft, saveViewTargetRoleDraft, savedViews],
    );
    const suggestedSaveViewDefault = useMemo(
        () => !hasDefaultSavedViewForTarget(savedViews, {
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        }),
        [saveViewScopeDraft, saveViewTargetBranchIdDraft, saveViewTargetRoleDraft, savedViews],
    );
    const selectedSavedViewScope = selectedSavedView?.scope ?? "personal";
    const selectedSavedViewBranchLabel = getSavedViewBranchLabel(selectedSavedView?.target_branch_id, branchMap);
    const selectedSavedViewRoleLabel = getSavedViewRoleLabel(selectedSavedView?.target_role);
    const canMutateSelectedSavedView = Boolean(
        selectedSavedView && (
            selectedSavedViewScope === "personal"
            || canManageTeamPresets
        ),
    );
    const selectedTeamTargetingDirty = selectedSavedViewScope === "team" && (
        (selectedSavedView?.target_branch_id ?? "") !== selectedTeamTargetBranchIdDraft
        || (selectedSavedView?.target_role ?? "") !== selectedTeamTargetRoleDraft
    );
    const savedViewDirty = selectedSavedView
        ? getSavedViewFingerprint(selectedSavedView) !== currentQueueFingerprint
        : false;
    const savedViewsLoading = savedViewsQuery.isFetching && savedViews.length === 0;
    const queueShareHref = useMemo(() => {
        if (typeof window === "undefined") {
            return "";
        }
        return buildCasesQueueHref(currentQueueSnapshot, {
            pathname: window.location.pathname,
            currentSearch: window.location.search,
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
            viewId: activeSavedViewId,
        });
    }, [
        activeSavedViewId,
        branchFilterEnabled,
        currentQueueSnapshot,
        privilegedOwnerFilterVisible,
    ]);

    useEffect(() => {
        if (!saveViewComposerOpen || saveViewDefaultTouched) {
            return;
        }
        setSaveViewDefaultDraft(suggestedSaveViewDefault);
    }, [saveViewComposerOpen, saveViewDefaultTouched, suggestedSaveViewDefault]);

    useEffect(() => {
        if (selectedSavedViewScope !== "team") {
            setSelectedTeamTargetBranchIdDraft("");
            setSelectedTeamTargetRoleDraft("");
            return;
        }
        setSelectedTeamTargetBranchIdDraft(selectedSavedView?.target_branch_id ?? "");
        setSelectedTeamTargetRoleDraft(selectedSavedView?.target_role ?? "");
    }, [
        selectedSavedView?.id,
        selectedSavedView?.target_branch_id,
        selectedSavedView?.target_role,
        selectedSavedViewScope,
    ]);
    const visibleSortOptions = sortOptions.filter((option) => {
        if (modeScope === "open") {
            return option.id !== "resolved_at";
        }
        if (modeScope === "resolved") {
            return option.id === "created_at" || option.id === "resolved_at";
        }
        return option.id === "activity" || option.id === "created_at";
    });
    const effectiveSortBy = resolveEffectiveSortBy(modeScope, activeViewId, effectiveFilters.sortBy);
    const defaultSortBy = getDefaultSortForModeScope(modeScope, activeViewId);
    const defaultSortLabel = sortOptions.find((option) => option.id === defaultSortBy)?.label ?? "По умолчанию";
    const advancedFiltersActive = hasAdvancedCaseRefinements(effectiveFilters, { branchFilterEnabled });
    const filtersToggleLabel = filtersCollapsed
        ? advancedFiltersActive
            ? "Фильтры активны"
            : "Фильтры"
        : "Скрыть фильтры";
    const showAdvancedFiltersRow = !filtersCollapsed && showAdvancedFilters;
    const hasAnyFiltersApplied = hasAnyCaseFiltersApplied({
        modeScope,
        activeViewId,
        filters: effectiveFilters,
        ownerScope: effectiveOwnerScope,
        branchFilterEnabled,
    });
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
    const timelineColumnLabel = modeScope === "resolved"
        ? "Закрыта"
        : modeScope === "all"
            ? "Действие / итог"
            : "Следующее действие";

    const pillClass = (active: boolean) => (
        `rounded-full border px-3 py-1 text-xs font-semibold transition ${
            active
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border/60 text-muted-foreground hover:text-foreground"
        }`
    );
    const enabledFieldCount = FIELD_ORDER.filter((field) => visibleFields[field]).length;

    useEffect(() => {
        if (activeSavedViewId && selectedSavedView) {
            return;
        }
        if (activeSavedViewId && !selectedSavedView && !savedViewsQuery.isFetching) {
            setActiveSavedViewId(null);
            return;
        }
        if (activeSavedViewId || savedViews.length === 0) {
            return;
        }
        const matchedSavedView = findSavedViewByFingerprint(savedViews, currentQueueFingerprint, {
            includeNonApplicableTeam: false,
        });
        if (matchedSavedView) {
            setActiveSavedViewId(matchedSavedView.id);
        }
    }, [
        activeSavedViewId,
        currentQueueFingerprint,
        savedViews,
        savedViewsQuery.isFetching,
        selectedSavedView,
    ]);

    useEffect(() => {
        if (!stateReady || !restoredQueueStateRef.current || typeof window === "undefined") {
            return;
        }
        if (!queueShareHref) {
            return;
        }
        const currentHref = `${window.location.pathname}${window.location.search}`;
        if (currentHref === queueShareHref) {
            return;
        }
        window.history.replaceState(window.history.state, "", queueShareHref);
    }, [queueShareHref, stateReady]);

    useEffect(() => {
        if (!filtersCompact) {
            setFiltersCollapsed(false);
        }
    }, [filtersCompact]);

    const { data, isLoading, error, refetch, isFetching, dataUpdatedAt } = useQuery({
        queryKey: ["cases", modeScope, effectiveFilters, effectiveOwnerScope, activeServerQueueView || activeViewId, cursor],
        queryFn: async (): Promise<CasesResponse> => {
            const buildParams = (includeSort: boolean) => {
                return buildCaseListSearchParams({
                    filters: includeSort ? effectiveFilters : { ...effectiveFilters, sortBy: undefined },
                    ownerScope: effectiveOwnerScope,
                    modeScope,
                    activeViewId,
                    privilegedOwnerFilterVisible,
                    activeServerQueueView,
                    cursor,
                    limit: 20,
                });
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

    const visibleCases = cases;
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
        queryKey: ["case-assignees-queue", effectiveFilters.branchId || "all", viewerRole],
        queryFn: async () => {
            const response = await casesApi.listQueueAssignees(effectiveFilters.branchId);
            return response.data;
        },
        enabled: privilegedOwnerFilterVisible,
    });
    const queueAssignees = useMemo(
        () => sortAssigneeOptionsByName(queueAssigneesData?.items ?? []),
        [queueAssigneesData?.items],
    );
    const ownerScopeOptions = useMemo(
        () => buildOwnerScopeOptions({
            privileged: privilegedOwnerFilterVisible,
            assignees: queueAssignees,
        }),
        [privilegedOwnerFilterVisible, queueAssignees],
    );
    const ownerScopeValue = ownerScopeToSelectValue(effectiveOwnerScope);
    const ownerScopeLabel = resolveOwnerScopeLabel(effectiveOwnerScope, queueAssignees);
    const recommendedBulkAssignee = useMemo(
        () => resolveRecommendedAssignee(bulkAssignees),
        [bulkAssignees],
    );
    const refinementChips = [
        modeScope !== "open"
            ? {
                key: "mode",
                label: activeMode.label,
                onClear: () => {
                    resetPagination();
                    setModeScope("open");
                },
            }
            : null,
        effectiveOwnerScope.kind !== "all"
            ? {
                key: "owner",
                label: `Ответственный: ${ownerScopeLabel}`,
                onClear: () => {
                    resetPagination();
                    setOwnerScope({ ...DEFAULT_OWNER_SCOPE });
                },
            }
            : null,
        branchFilterEnabled && effectiveFilters.branchId
            ? {
                key: "branch",
                label: `Филиал: ${branchMap.get(effectiveFilters.branchId) ?? effectiveFilters.branchId}`,
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, branchId: undefined }));
                },
            }
            : null,
        effectiveFilters.sortBy
            ? {
                key: "sort",
                label: `Порядок: ${sortOptions.find((option) => option.id === effectiveSortBy)?.label ?? effectiveSortBy}`,
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, sortBy: undefined }));
                },
            }
            : null,
        effectiveFilters.dateFrom || effectiveFilters.dateTo
            ? {
                key: "dates",
                label: `${modeScope === "resolved" ? "Закрыта" : "Создана"}: ${effectiveFilters.dateFrom || "..." } — ${effectiveFilters.dateTo || "..."}`,
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, dateFrom: undefined, dateTo: undefined }));
                },
            }
            : null,
        effectiveFilters.hasDeliveryError
            ? {
                key: "delivery-error",
                label: "Есть ошибки доставки",
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, hasDeliveryError: false }));
                },
            }
            : null,
        effectiveFilters.hasPendingOutbox
            ? {
                key: "pending-outbox",
                label: "Есть исходящие в очереди",
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, hasPendingOutbox: false }));
                },
            }
            : null,
        effectiveFilters.hasHumanLock
            ? {
                key: "human-lock",
                label: "Бот на паузе",
                onClear: () => {
                    resetPagination();
                    setFilters((prev) => ({ ...prev, hasHumanLock: false }));
                },
            }
            : null,
    ].filter((item): item is { key: string; label: string; onClear: () => void } => Boolean(item));

    const applyCasesQueueSnapshot = (
        snapshot: CasesQueueStateSnapshot,
        {
            savedViewId = null,
        }: {
            savedViewId?: string | null;
        } = {},
    ) => {
        setBulkSummary(null);
        resetPagination();
        setCaseItems([]);
        setSelectedCaseIds([]);
        setFilters(snapshot.filters);
        setOwnerScope(snapshot.ownerScope);
        setModeScope(snapshot.modeScope);
        setSearchValue(snapshot.searchValue);
        setActiveViewId(snapshot.activeViewId);
        setActiveSavedViewId(savedViewId);
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        setShowAdvancedFilters(
            snapshot.modeScope !== "open"
            || hasAdvancedCaseRefinements(snapshot.filters, { branchFilterEnabled }),
        );
    };

    const createSavedViewMutation = useMutation({
        mutationFn: async (payload: {
            name: string;
            isDefault: boolean;
            scope: "personal" | "team";
            targetBranchId: string;
            targetRole: ConsoleRole | "";
        }) => {
            const response = await queueStateApi.createView({
                surface: "cases",
                name: payload.name,
                scope: payload.scope,
                version: 1,
                query_state: buildCasesQueueStatePayload(currentQueueSnapshot, { branchFilterEnabled }),
                is_default: payload.isDefault,
                target_branch_id: payload.scope === "team" ? (payload.targetBranchId || null) : null,
                target_role: payload.scope === "team" ? (payload.targetRole || null) : null,
            });
            return response.data;
        },
        onSuccess: async (savedView) => {
            setActiveSavedViewId(savedView.id);
            setSaveViewDraftName("");
            setSaveViewComposerOpen(false);
            setSaveViewScopeDraft("personal");
            setSaveViewTargetBranchIdDraft("");
            setSaveViewTargetRoleDraft("");
            setSaveViewDefaultDraft(false);
            setSaveViewDefaultTouched(false);
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "cases"] });
            toast.success(`Вид «${savedView.name}» сохранён`);
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось сохранить вид"));
        },
    });

    const updateSavedViewMutation = useMutation({
        mutationFn: async (payload: {
            viewId: string;
            queryState?: Record<string, unknown>;
            isDefault?: boolean;
            targetBranchId?: string | null;
            targetRole?: ConsoleRole | null;
        }) => {
            const response = await queueStateApi.updateView(payload.viewId, {
                query_state: payload.queryState,
                is_default: payload.isDefault,
                target_branch_id: payload.targetBranchId,
                target_role: payload.targetRole,
            });
            return response.data;
        },
        onSuccess: async (savedView) => {
            setActiveSavedViewId(savedView.id);
            setSelectedTeamTargetBranchIdDraft(savedView.target_branch_id ?? "");
            setSelectedTeamTargetRoleDraft(savedView.target_role ?? "");
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "cases"] });
            toast.success(`Вид «${savedView.name}» обновлён`);
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось обновить вид"));
        },
    });

    const deleteSavedViewMutation = useMutation({
        mutationFn: async (viewId: string) => {
            await queueStateApi.deleteView(viewId);
            return viewId;
        },
        onSuccess: async (viewId) => {
            if (activeSavedViewId === viewId) {
                setActiveSavedViewId(null);
            }
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "cases"] });
            toast.success("Вид удалён");
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось удалить вид"));
        },
    });
    const savedViewMutationPending = createSavedViewMutation.isPending
        || updateSavedViewMutation.isPending
        || deleteSavedViewMutation.isPending;

    const handleCopyQueueLink = async () => {
        if (!queueShareHref || typeof window === "undefined") {
            toast.error("Не удалось собрать ссылку на очередь");
            return;
        }
        const absoluteHref = new URL(queueShareHref, window.location.origin).toString();
        await copyText(absoluteHref);
        toast.success("Ссылка на очередь скопирована");
    };

    const handleOpenSaveViewComposer = () => {
        setSaveViewDraftName("");
        const nextScope = canManageTeamPresets && selectedSavedViewScope === "team"
            ? "team"
            : "personal";
        const nextTargetBranchId = nextScope === "team" ? (selectedSavedView?.target_branch_id ?? "") : "";
        const nextTargetRole = nextScope === "team" ? (selectedSavedView?.target_role ?? "") : "";
        setSaveViewScopeDraft(nextScope);
        setSaveViewTargetBranchIdDraft(nextTargetBranchId);
        setSaveViewTargetRoleDraft(nextTargetRole);
        setSaveViewDefaultTouched(false);
        setSaveViewDefaultDraft(!hasDefaultSavedViewForTarget(savedViews, {
            scope: nextScope,
            targetBranchId: nextTargetBranchId,
            targetRole: nextTargetRole,
        }));
        setSaveViewComposerOpen(true);
    };

    const handleSaveCurrentView = () => {
        const name = saveViewDraftName.trim();
        if (!name) {
            toast.error("Введите название вида");
            return;
        }
        createSavedViewMutation.mutate({
            name,
            isDefault: saveViewDefaultDraft,
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        });
    };

    const handleApplySavedView = (viewId: string) => {
        const savedView = savedViews.find((item) => item.id === viewId);
        const snapshot = readCasesQueueStateFromSavedView(savedView, {
            branchFilterEnabled,
            privilegedOwnerFilterVisible,
        });
        if (!savedView || !snapshot) {
            toast.error("Не удалось прочитать сохранённый вид");
            return;
        }
        applyCasesQueueSnapshot(snapshot, { savedViewId: savedView.id });
        toast.success(`Применён вид «${savedView.name}»`);
    };

    const handleUpdateSavedView = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        updateSavedViewMutation.mutate({
            viewId: selectedSavedView.id,
            queryState: buildCasesQueueStatePayload(currentQueueSnapshot, { branchFilterEnabled }),
            targetBranchId: selectedSavedViewScope === "team" ? (selectedTeamTargetBranchIdDraft || null) : undefined,
            targetRole: selectedSavedViewScope === "team" ? (selectedTeamTargetRoleDraft || null) : undefined,
        });
    };

    const handleToggleSavedViewDefault = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        updateSavedViewMutation.mutate({
            viewId: selectedSavedView.id,
            isDefault: !selectedSavedView.is_default,
        });
    };

    const handleDeleteSavedView = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        const confirmed = window.confirm(`Удалить вид «${selectedSavedView.name}»?`);
        if (!confirmed) {
            return;
        }
        deleteSavedViewMutation.mutate(selectedSavedView.id);
    };

    const bulkActionMutation = useMutation({
        mutationFn: async () => {
            if (selectedCaseIds.length === 0 || !bulkActionMode) {
                throw new Error("Выберите заявки и действие");
            }
            if (bulkActionMode === "route") {
                const response = await casesApi.bulkAction({
                    action: "route",
                    case_ids: selectedCaseIds,
                    policy: bulkRoutingPolicy,
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
            setBulkRoutingPolicy(DEFAULT_CASE_ROUTING_POLICY);
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
        setBulkRoutingPolicy(DEFAULT_CASE_ROUTING_POLICY);
        setBulkAssigneeId("");
    }, [selectedCaseIds.length]);

    useEffect(() => {
        if (bulkActionMode !== "reassign") {
            setBulkAssigneeId("");
        }
        if (bulkActionMode !== "route") {
            setBulkRoutingPolicy(DEFAULT_CASE_ROUTING_POLICY);
        }
    }, [bulkActionMode]);

    useEffect(() => {
        if (!workspaceScope || !stateReady) {
            return;
        }
        writeInboxCaseListPrefs(workspaceScope, {
            filters: effectiveFilters,
            ownerScope: effectiveOwnerScope,
            modeScope,
            searchValue,
            showAdvancedFilters,
            filtersCollapsed,
            autoRefreshEnabled,
            activeViewId,
            visibleFields,
        });
    }, [workspaceScope, stateReady, effectiveFilters, effectiveOwnerScope, modeScope, searchValue, showAdvancedFilters, filtersCollapsed, autoRefreshEnabled, activeViewId, visibleFields]);

    useEffect(() => {
        if (!workspaceScope || !stateReady || !hasToken) {
            return;
        }
        const payload = {
            surface: "cases" as const,
            version: 1,
            query_state: buildCasesQueueStatePayload(currentQueueSnapshot, { branchFilterEnabled }),
        };
        const fingerprint = JSON.stringify(payload);
        if (lastSavedQueueStateRef.current === fingerprint) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            if (lastSavedQueueStateRef.current === fingerprint) {
                return;
            }
            lastSavedQueueStateRef.current = fingerprint;
            void api.put("/queue-state/current", payload).catch(() => {
                if (lastSavedQueueStateRef.current === fingerprint) {
                    lastSavedQueueStateRef.current = "";
                }
            });
        }, 250);
        return () => window.clearTimeout(timeoutId);
    }, [
        api,
        branchFilterEnabled,
        currentQueueSnapshot,
        hasToken,
        stateReady,
        workspaceScope,
    ]);

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

    const applyOwnerScopeValue = (nextValue: string) => {
        resetPagination();
        setOwnerScope(
            parseOwnerScopeValue(nextValue, privilegedOwnerFilterVisible),
        );
    };

    const applyQueueView = (viewId: InboxQueueViewId) => {
        if (modeScope !== "open") {
            return;
        }
        if (!queueViewMap.has(viewId)) {
            return;
        }
        setBulkSummary(null);
        resetPagination();
        setSelectedCaseIds([]);
        setActiveViewId(viewId);
    };

    const applyModeScope = (nextModeScope: InboxCaseModeScope) => {
        setBulkSummary(null);
        resetPagination();
        setSelectedCaseIds([]);
        setModeScope(nextModeScope);
        setFilters((prev) => {
            const crossesResolvedBoundary = (modeScope === "resolved" || nextModeScope === "resolved")
                && modeScope !== nextModeScope;
            let nextSortBy = prev.sortBy;
            if (nextModeScope !== "open" && nextSortBy === "sla") {
                nextSortBy = undefined;
            }
            if (nextModeScope !== "resolved" && nextSortBy === "resolved_at") {
                nextSortBy = undefined;
            }
            return {
                ...prev,
                hasDeliveryError: nextModeScope === "open" ? prev.hasDeliveryError : false,
                hasPendingOutbox: nextModeScope === "open" ? prev.hasPendingOutbox : false,
                hasHumanLock: nextModeScope === "open" ? prev.hasHumanLock : false,
                dateFrom: crossesResolvedBoundary ? undefined : prev.dateFrom,
                dateTo: crossesResolvedBoundary ? undefined : prev.dateTo,
                sortBy: nextSortBy,
            };
        });
        if (nextModeScope !== "open") {
            setShowAdvancedFilters(true);
        }
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
        setBulkRoutingPolicy(DEFAULT_CASE_ROUTING_POLICY);
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
        setFiltersCollapsed(false);
        setSelectedCaseIds([]);
        setBulkSummary(null);
        setFieldPanelOpen(false);
        resetPagination();
        setModeScope("open");
        setActiveViewId("all_open");
        setFilters({ ...DEFAULT_FILTERS });
        setOwnerScope({ ...DEFAULT_OWNER_SCOPE });
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
                <div className="flex w-full flex-wrap items-center gap-2 border-b border-border/60 pb-2" data-testid="cases-mode-scopes">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        Список
                    </span>
                    {modeScopes.map((scope) => (
                        <button
                            key={scope.id}
                            type="button"
                            onClick={() => applyModeScope(scope.id)}
                            className={pillClass(modeScope === scope.id)}
                            data-testid={`cases-mode-scope-${scope.id}`}
                        >
                            {scope.label}
                        </button>
                    ))}
                </div>
                {modeScope === "open" && (
                    <div className="flex w-full flex-wrap items-center gap-2 border-b border-border/60 pb-2" data-testid="cases-queue-views">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                            Очередь
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
                )}
                {modeScope !== "open" && (
                    <div className="rounded-xl border border-border/60 bg-card/80 px-3 py-2 text-xs text-muted-foreground" data-testid="cases-history-hint">
                        {modeScope === "resolved"
                            ? "История закрытых заявок. Очередные режимы скрыты, чтобы не смешивать архив с текущей работой."
                            : "Поиск по открытым и закрытым заявкам. Очередные режимы доступны только в списке открытых заявок."}
                    </div>
                )}
                <div className="rounded-xl border border-border/60 bg-card/80 p-3" data-testid="cases-saved-views">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Сохранённые виды
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                                Личные виды и командные пресеты поверх текущего server-owned состояния.
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => {
                                    void handleCopyQueueLink();
                                }}
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                data-testid="cases-queue-copy-link"
                            >
                                Копировать ссылку
                            </button>
                            <button
                                type="button"
                                onClick={handleOpenSaveViewComposer}
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                disabled={savedViewMutationPending}
                                data-testid="cases-saved-view-save"
                            >
                                Сохранить текущий
                            </button>
                            {selectedSavedView && savedViewDirty && (
                                <>
                                    <button
                                        type="button"
                                        onClick={() => handleApplySavedView(selectedSavedView.id)}
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                        disabled={savedViewMutationPending}
                                        data-testid="cases-saved-view-reapply"
                                    >
                                        Вернуть вид
                                    </button>
                                    {canMutateSelectedSavedView && (
                                        <button
                                            type="button"
                                            onClick={handleUpdateSavedView}
                                            className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary"
                                            disabled={savedViewMutationPending}
                                            data-testid="cases-saved-view-update"
                                        >
                                            Обновить вид
                                        </button>
                                    )}
                                </>
                            )}
                            {selectedSavedView && !savedViewDirty && selectedTeamTargetingDirty && canMutateSelectedSavedView && (
                                <button
                                    type="button"
                                    onClick={handleUpdateSavedView}
                                    className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary"
                                    disabled={savedViewMutationPending}
                                    data-testid="cases-saved-view-update"
                                >
                                    Сохранить targeting
                                </button>
                            )}
                            {selectedSavedView && canMutateSelectedSavedView && (
                                <>
                                    <button
                                        type="button"
                                        onClick={handleToggleSavedViewDefault}
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                        disabled={savedViewMutationPending}
                                        data-testid="cases-saved-view-default"
                                    >
                                        {selectedSavedView.is_default ? "Снять дефолт" : "Сделать дефолтом"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleDeleteSavedView}
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-destructive"
                                        disabled={savedViewMutationPending}
                                        data-testid="cases-saved-view-delete"
                                    >
                                        Удалить
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                        <select
                            value={activeSavedViewId ?? ""}
                            onChange={(event) => {
                                const nextId = event.target.value;
                                if (!nextId) {
                                    setActiveSavedViewId(null);
                                    return;
                                }
                                handleApplySavedView(nextId);
                            }}
                            className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                            disabled={savedViewsLoading || savedViewMutationPending}
                            data-testid="cases-saved-view-select"
                        >
                            <option value="">
                                {savedViewsLoading
                                    ? "Загружаем виды..."
                                    : savedViews.length === 0
                                        ? "Нет сохранённых видов"
                                        : "Выберите сохранённый вид"}
                            </option>
                            {teamSavedViews.length > 0 && (
                                <optgroup label="Командные пресеты">
                                    {teamSavedViews.map((view) => (
                                        <option key={view.id} value={view.id}>
                                            {buildSavedViewOptionLabel(view, branchMap)}
                                        </option>
                                    ))}
                                </optgroup>
                            )}
                            {personalSavedViews.length > 0 && (
                                <optgroup label="Личные виды">
                                    {personalSavedViews.map((view) => (
                                        <option key={view.id} value={view.id}>
                                            {buildSavedViewOptionLabel(view, branchMap)}
                                        </option>
                                    ))}
                                </optgroup>
                            )}
                        </select>
                        {selectedSavedView && (
                            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                    {selectedSavedView.name}
                                </span>
                                <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                    {SAVED_VIEW_SCOPE_LABELS[selectedSavedViewScope]}
                                </span>
                                {selectedSavedViewBranchLabel && (
                                    <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                        {selectedSavedViewBranchLabel}
                                    </span>
                                )}
                                {selectedSavedViewRoleLabel && (
                                    <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                        {selectedSavedViewRoleLabel}
                                    </span>
                                )}
                                {selectedSavedView.is_default && (
                                    <span className="rounded-full bg-primary/10 px-2 py-1 font-semibold text-primary">
                                        default
                                    </span>
                                )}
                                {isTeamSavedView(selectedSavedView) && selectedSavedView.is_applicable === false && (
                                    <span className="rounded-full bg-slate-100 px-2 py-1 font-semibold text-slate-700">
                                        вне текущего контура
                                    </span>
                                )}
                                {savedViewDirty && (
                                    <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">
                                        изменён
                                    </span>
                                )}
                                {selectedTeamTargetingDirty && (
                                    <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">
                                        targeting изменён
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                    {selectedSavedViewScope === "team" && canManageTeamPresets && selectedSavedView && (
                        <div className="mt-3 grid gap-2 border-t border-border/60 pt-3 sm:grid-cols-2">
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Командный филиал
                                </span>
                                <select
                                    value={selectedTeamTargetBranchIdDraft}
                                    onChange={(event) => setSelectedTeamTargetBranchIdDraft(event.target.value)}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    disabled={savedViewMutationPending}
                                    data-testid="cases-saved-view-team-branch"
                                >
                                    <option value="">Все филиалы</option>
                                    {selectableBranches.map((branch) => (
                                        <option key={branch.id} value={branch.id}>
                                            {branch.name ?? branch.id}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Командная роль
                                </span>
                                <select
                                    value={selectedTeamTargetRoleDraft}
                                    onChange={(event) => setSelectedTeamTargetRoleDraft(event.target.value as ConsoleRole | "")}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    disabled={savedViewMutationPending}
                                    data-testid="cases-saved-view-team-role"
                                >
                                    <option value="">Все роли</option>
                                    {savedViewTargetRoleOptions.map((role) => (
                                        <option key={role} value={role}>
                                            {SAVED_VIEW_ROLE_LABELS[role]}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>
                    )}
                    {saveViewComposerOpen && (
                        <div className="mt-3 flex flex-col gap-3 border-t border-border/60 pt-3">
                            <input
                                ref={saveViewInputRef}
                                type="text"
                                value={saveViewDraftName}
                                onChange={(event) => setSaveViewDraftName(event.target.value)}
                                onKeyDown={(event) => {
                                    if (event.key === "Enter") {
                                        event.preventDefault();
                                        handleSaveCurrentView();
                                    }
                                }}
                                placeholder="Например: Мои открытые"
                                className="min-w-[220px] flex-1 rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                data-testid="cases-saved-view-name-input"
                            />
                            {canManageTeamPresets && (
                                <div className="grid gap-2 sm:grid-cols-3">
                                    <label className="space-y-1">
                                        <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                            Scope
                                        </span>
                                        <select
                                            value={saveViewScopeDraft}
                                            onChange={(event) => setSaveViewScopeDraft(event.target.value as "personal" | "team")}
                                            className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            disabled={createSavedViewMutation.isPending}
                                            data-testid="cases-saved-view-scope"
                                        >
                                            <option value="personal">Личный</option>
                                            <option value="team">Команда</option>
                                        </select>
                                    </label>
                                    {saveViewScopeDraft === "team" && (
                                        <>
                                            <label className="space-y-1">
                                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                    Филиал
                                                </span>
                                                <select
                                                    value={saveViewTargetBranchIdDraft}
                                                    onChange={(event) => setSaveViewTargetBranchIdDraft(event.target.value)}
                                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                    disabled={createSavedViewMutation.isPending}
                                                    data-testid="cases-saved-view-target-branch"
                                                >
                                                    <option value="">Все филиалы</option>
                                                    {selectableBranches.map((branch) => (
                                                        <option key={branch.id} value={branch.id}>
                                                            {branch.name ?? branch.id}
                                                        </option>
                                                    ))}
                                                </select>
                                            </label>
                                            <label className="space-y-1">
                                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                    Роль
                                                </span>
                                                <select
                                                    value={saveViewTargetRoleDraft}
                                                    onChange={(event) => setSaveViewTargetRoleDraft(event.target.value as ConsoleRole | "")}
                                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                    disabled={createSavedViewMutation.isPending}
                                                    data-testid="cases-saved-view-target-role"
                                                >
                                                    <option value="">Все роли</option>
                                                    {savedViewTargetRoleOptions.map((role) => (
                                                        <option key={role} value={role}>
                                                            {SAVED_VIEW_ROLE_LABELS[role]}
                                                        </option>
                                                    ))}
                                                </select>
                                            </label>
                                        </>
                                    )}
                                </div>
                            )}
                            <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                <input
                                    type="checkbox"
                                    checked={saveViewDefaultDraft}
                                    onChange={(event) => {
                                        setSaveViewDefaultTouched(true);
                                        setSaveViewDefaultDraft(event.target.checked);
                                    }}
                                    className="h-4 w-4 rounded border-border/60"
                                    disabled={createSavedViewMutation.isPending}
                                    data-testid="cases-saved-view-default-checkbox"
                                />
                                <span>
                                    {saveViewScopeDraft === "team"
                                        ? "Сделать дефолтным командным пресетом"
                                        : "Сделать дефолтным личным видом"}
                                </span>
                                {!saveViewDefaultTouched && (
                                    <span className="text-muted-foreground/80">
                                        {suggestedSaveViewDefault ? "рекомендуется" : "по желанию"}
                                    </span>
                                )}
                            </label>
                            <div className="text-xs text-muted-foreground">
                                {saveViewScopeDraft === "team"
                                    ? `Командных пресетов в этом targeting: ${matchingScopeSavedViewCount}`
                                    : `Личных видов: ${matchingScopeSavedViewCount}`}
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <button
                                    type="button"
                                    onClick={handleSaveCurrentView}
                                    className="rounded-full border border-primary/30 bg-primary/5 px-3 py-2 text-xs font-semibold text-primary"
                                    disabled={createSavedViewMutation.isPending}
                                    data-testid="cases-saved-view-name-submit"
                                >
                                    {createSavedViewMutation.isPending ? "Сохраняем..." : "Сохранить"}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setSaveViewDraftName("");
                                        setSaveViewComposerOpen(false);
                                        setSaveViewScopeDraft("personal");
                                        setSaveViewTargetBranchIdDraft("");
                                        setSaveViewTargetRoleDraft("");
                                        setSaveViewDefaultDraft(false);
                                        setSaveViewDefaultTouched(false);
                                    }}
                                    className="rounded-full border border-border/60 px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                    disabled={createSavedViewMutation.isPending}
                                >
                                    Отмена
                                </button>
                            </div>
                        </div>
                    )}
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
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Ответственный
                                </span>
                                <select
                                    value={ownerScopeValue}
                                    onChange={(event) => applyOwnerScopeValue(event.target.value)}
                                    className={compactSelectClass}
                                    disabled={queueAssigneesLoading}
                                    data-testid="cases-filter-owner-scope"
                                >
                                    {ownerScopeOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setShowAdvancedFilters((prev) => !prev)}
                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                data-testid="cases-filter-advanced-toggle"
                            >
                                {showAdvancedFilters ? "Скрыть фильтры" : "Фильтры"}
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
                            value={ownerScopeValue}
                            onChange={(event) => applyOwnerScopeValue(event.target.value)}
                            className={selectClass}
                            disabled={queueAssigneesLoading}
                            data-testid="cases-filter-owner-scope"
                        >
                            {ownerScopeOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                        {!filtersCollapsed && (
                            <button
                                type="button"
                                onClick={() => setShowAdvancedFilters((prev) => !prev)}
                                className="text-xs text-muted-foreground hover:text-foreground whitespace-nowrap"
                                data-testid="cases-filter-advanced-toggle"
                            >
                                {showAdvancedFilters ? "Скрыть фильтры" : "Фильтры"}
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
                        {activeMode.label}
                    </span>
                    {modeScope === "open" && activeViewId !== "all_open" && (
                        <span className="rounded-full border border-border/60 bg-card px-2 py-1 font-semibold text-foreground/80">
                            {activeQueueView?.label ?? "Все открытые"}
                        </span>
                    )}
                    {selectedSavedView && (
                        <span
                            className={`rounded-full border px-2 py-1 font-semibold ${
                                savedViewDirty
                                    ? "border-amber-300 bg-amber-100 text-amber-900"
                                    : "border-border/60 bg-card text-foreground/80"
                            }`}
                            data-testid="cases-saved-view-summary"
                        >
                            Вид: {selectedSavedView.name}{savedViewDirty ? " · изменён" : ""}
                        </span>
                    )}
                    {effectiveFilters.query && (
                        <button
                            type="button"
                            onClick={() => setSearchValue("")}
                            className="rounded-full border border-border/60 bg-card px-2 py-1 font-semibold text-foreground/80"
                            data-testid="cases-search-summary"
                        >
                            Поиск: {effectiveFilters.query} ×
                        </button>
                    )}
                    {refinementChips.map((chip) => (
                        <button
                            key={chip.key}
                            type="button"
                            onClick={chip.onClear}
                            className="rounded-full border border-border/60 bg-card px-2 py-1 font-semibold text-foreground/80"
                            data-testid={chip.key === "owner" ? "cases-owner-summary" : `cases-filter-chip-${chip.key}`}
                        >
                            {chip.label} ×
                        </button>
                    ))}
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
                        className="grid w-full gap-3 border-t border-border/60 pt-2 md:grid-cols-2 xl:grid-cols-4"
                        data-testid="cases-filters-advanced"
                    >
                        <label className="space-y-1">
                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                Порядок
                            </span>
                            <select
                                value={effectiveFilters.sortBy ?? "__default__"}
                                onChange={(e) => {
                                    resetPagination();
                                    const nextSortBy = e.target.value;
                                    setFilters({
                                        ...filters,
                                        sortBy: nextSortBy === "__default__"
                                            ? undefined
                                            : nextSortBy as NonNullable<CaseFilters["sortBy"]>,
                                    });
                                }}
                                className={compactSelectClass}
                                data-testid="cases-filter-sort-select"
                            >
                                <option value="__default__">
                                    По умолчанию для режима ({defaultSortLabel})
                                </option>
                                {visibleSortOptions.map((option) => (
                                    <option key={option.id} value={option.id}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        {branchFilterEnabled && (
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Филиал
                                </span>
                                <select
                                    value={filters.branchId || ""}
                                    onChange={(e) => { resetPagination(); setFilters({ ...filters, branchId: e.target.value || undefined }); }}
                                    className={compactSelectClass}
                                    data-testid="cases-filter-branch"
                                >
                                    <option value="">Все филиалы</option>
                                    {selectableBranches.map((branch) => (
                                        <option key={branch.id} value={branch.id}>
                                            {branch.name ?? branch.id}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}
                        <div className="grid gap-3 sm:grid-cols-2 xl:col-span-2">
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    {modeScope === "resolved" ? "Закрыта с" : "Создана с"}
                                </span>
                                <input
                                    type="date"
                                    value={filters.dateFrom || ""}
                                    onChange={(e) => { resetPagination(); setFilters({ ...filters, dateFrom: e.target.value || undefined }); }}
                                    className={compactSelectClass}
                                    data-testid="cases-filter-date-from"
                                />
                            </label>
                            <label className="space-y-1">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    {modeScope === "resolved" ? "Закрыта по" : "Создана по"}
                                </span>
                                <input
                                    type="date"
                                    value={filters.dateTo || ""}
                                    onChange={(e) => { resetPagination(); setFilters({ ...filters, dateTo: e.target.value || undefined }); }}
                                    className={compactSelectClass}
                                    data-testid="cases-filter-date-to"
                                />
                            </label>
                        </div>
                        {modeScope === "open" && (
                            <div className="flex flex-wrap items-center gap-3 xl:col-span-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={filters.hasDeliveryError}
                                        onChange={(e) => { resetPagination(); setFilters({ ...filters, hasDeliveryError: e.target.checked }); }}
                                        className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        data-testid="cases-filter-delivery-error"
                                    />
                                    <span className="text-sm text-foreground/80">Есть ошибки доставки</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={filters.hasPendingOutbox}
                                        onChange={(e) => { resetPagination(); setFilters({ ...filters, hasPendingOutbox: e.target.checked }); }}
                                        className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        data-testid="cases-filter-pending-outbox"
                                    />
                                    <span className="text-sm text-foreground/80">Есть исходящие в очереди</span>
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
                                        <select
                                            value={bulkRoutingPolicy}
                                            onChange={(event) => setBulkRoutingPolicy(event.target.value as CaseRoutingPolicy)}
                                            disabled={bulkActionMutation.isPending}
                                            className="mt-2 w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm font-semibold text-emerald-950 disabled:opacity-50"
                                            data-testid="cases-bulk-route-policy-select"
                                        >
                                            {Object.entries(CASE_ROUTING_POLICY_LABELS).map(([value, label]) => (
                                                <option key={value} value={value}>
                                                    {label}
                                                </option>
                                            ))}
                                        </select>
                                        <p className="mt-2 text-xs text-emerald-900/80">
                                            {CASE_ROUTING_POLICY_HINTS[bulkRoutingPolicy]}
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
                        const primaryTimelineBadge = getCasePrimaryTimelineBadge(c, modeScope);
                        const businessStatus = getCaseBusinessStatusBadge(c);
                        const branchName = branchMap.get(c.branch_id || "") || "-";
                        const activityValue = getCaseActivityValue(c, modeScope);
                        const activityLabel = formatCompactActivityLabel(activityValue);
                        const contactName = c.customer_name || c.customer_phone || c.customer_remote_jid?.split("@")[0] || "Клиент";
                        const contactPhone = c.customer_phone || c.customer_remote_jid?.split("@")[0] || "";
                        const preview = c.last_message_preview || c.user_message || "-";
                        const isSelected = selectedCaseId === c.id;
                        const isBulkSelected = selectedCaseIdSet.has(c.id);
                        const priorityChip = getPriorityChip(c.priority_tier);
                        const secondaryAttention = c.attention_reason
                            && !primaryTimelineBadge.state?.startsWith("reply")
                            && primaryTimelineBadge.state !== "overdue"
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
                                    <span className={`rounded-full px-2 py-1 font-semibold ${primaryTimelineBadge.className}`}>
                                        {primaryTimelineBadge.label}
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
                                <th className="p-4 text-sm font-medium text-muted-foreground">{timelineColumnLabel}</th>
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
                                const primaryTimelineBadge = getCasePrimaryTimelineBadge(c, modeScope);
                                const businessStatus = getCaseBusinessStatusBadge(c);
                                const branchName = branchMap.get(c.branch_id || "") || "-";
                                const lastInbound = c.last_inbound_at ? new Date(c.last_inbound_at) : null;
                                const lastActivity = getCaseActivityValue(c, modeScope);
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
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${primaryTimelineBadge.className}`}>
                                                {primaryTimelineBadge.label}
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
                                                {c.attention_reason
                                                    && !primaryTimelineBadge.state?.startsWith("reply")
                                                    && primaryTimelineBadge.state !== "overdue" && (
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
