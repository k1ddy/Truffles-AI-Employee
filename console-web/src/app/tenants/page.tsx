"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import type { components } from "@/types/api.generated";
import {
    authApi,
    canAccessConsole,
    type TenantsWeeklySnapshotRecord,
} from "@/lib/api-client";
import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import {
    readConsoleContextScopeFromStorage,
} from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";
import {
    formatOptionalHours,
    formatOptionalPercent,
    type OperationalKpiId,
    type OperationalKpiStatus,
} from "./operational-kpi";
import { useTenantsDataQueries } from "./use-tenants-data-queries";
import { useTenantsActions } from "./use-tenants-actions";
import { useTenantsActionQueue } from "./use-tenants-action-queue";
import { useTenantsOperationalModel } from "./use-tenants-operational-model";
import { useTenantsPageOrchestration } from "./use-tenants-page-orchestration";
import { useTenantsPageOperations } from "./use-tenants-page-operations";
import { useTenantsPageFilters } from "./use-tenants-page-filters";
import TenantsPageView from "./tenants-page-view";
import {
    BRANCH_PHONE_INPUT_PATTERN,
    buildBranchChangePatch,
    formatDateTimeLabel,
    formatReferenceScopeReason,
    formatStateLabel,
    isValidTimezoneName,
    LIFECYCLE_AUDIT_STORAGE_KEY,
    mapAuditEventToLifecycleEntry,
    mergeLifecycleAuditEntries,
    pushLifecycleAuditEntry,
    safeParseLifecycleAuditMap,
    SLUG_INPUT_PATTERN,
    toIsoWeekKey,
    type ClientLifecycleAuditEntry,
    type ClientLifecycleAuditMap,
    type ClientLifecycleMode,
    applyBranchSnapshotToEditor,
} from "./tenants-page-helpers";
import { useTenantsScopeDerivedState } from "./use-tenants-scope-derived-state";

type CompanyEditorState = {
    id: string;
    name: string;
    billingInfo: string;
    originalName: string;
    originalBillingInfo: string;
};

type ClientEditorState = {
    id: string;
    slug: string;
    companyId: string;
    originalSlug: string;
    originalCompanyId: string;
    totalBranches: number;
};

type ClientLifecycleAuditFilter = "all" | "success" | "error";
type ClientLifecycleDraftState = {
    clientId: string;
    clientLabel: string;
    companyLabel: string;
    mode: ClientLifecycleMode;
    currentLifecycleLabel: string;
    targetLifecycleLabel: string;
    activeBranches: number;
    totalBranches: number;
    degradedBranches: number;
    reason: string;
    confirmChecked: boolean;
    checkClientScope: boolean;
    checkImpactReview: boolean;
    checkOwnerAligned: boolean;
};

type BranchEditorState = {
    id: string;
    name: string;
    slug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    telegramChatId: string;
    knowledgeTag: string;
    isActive: boolean;
    changeReason: string;
    confirmReason: string;
    rollbackReason: string;
    original: {
        name: string;
        slug: string;
        timezone: string;
        phone: string;
        instanceId: string;
        telegramChatId: string;
        knowledgeTag: string;
        isActive: boolean;
    };
};

type QuickCreateFormState = {
    companyName: string;
    clientSlug: string;
    branchName: string;
    branchSlug: string;
    branchTimezone: string;
    branchPhone: string;
    branchInstanceId: string;
    companyId: string;
    clientId: string;
};

type BranchChangeRecord = components["schemas"]["ConsoleBranchChangeRecord"];

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetLifecycleFilter = "all" | "lead" | "contracting" | "onboarding" | "go_live_ready" | "active" | "paused" | "archived";
type FleetPaymentFilter = "all" | "pending" | "confirmed" | "rejected" | "unknown";
type FleetServiceFilter = "all" | "ok" | "degraded" | "attention";
type FleetAttentionLevel = "high" | "medium" | "low";
type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";
type TenantsViewPreset = "operator" | "platform";

type TenantsOperationalSnapshot = {
    id: string;
    weekKey: string;
    createdAt: string;
    report: {
        generatedAt: string;
        sourceWindow: number;
        workspaceMode: TenantsWorkspaceMode;
        lifecycleMode: TenantLifecycleMode;
        kpi: Record<OperationalKpiId, number>;
        drilldown: Array<{
            id: OperationalKpiId;
            status: OperationalKpiStatus;
            value: number;
            reason: string;
        }>;
        attentionSummary: {
            activeClientsTotal: number;
            highRiskClients: number;
            mediumRiskClients: number;
            outboxFailed24hTotal: number;
            pendingHandoversTotal: number;
        };
    };
};

const MAX_WEEKLY_SNAPSHOTS = 12;

function attentionLevelClass(level?: FleetAttentionLevel): string {
    if (level === "high") {
        return "bg-red-100 text-red-700";
    }
    if (level === "medium") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-blue-100 text-blue-700";
}

const FLEET_LIFECYCLE_LABELS: Record<string, string> = {
    lead: "Лид",
    contracting: "Договор",
    onboarding: "Онбординг",
    go_live_ready: "Готов к запуску",
    active: "Активный",
    paused: "Пауза",
    archived: "Архив",
};

const FLEET_PAYMENT_LABELS: Record<string, string> = {
    pending: "Ожидает",
    confirmed: "Подтверждена",
    rejected: "Отклонена",
    unknown: "Не задана",
};

const FLEET_SERVICE_LABELS: Record<string, string> = {
    ok: "Стабильно",
    degraded: "Деградация",
    attention: "Требует внимания",
};

const BRANCH_CHANGE_STATUS_LABELS: Record<string, string> = {
    draft: "Черновик",
    validated: "Проверено",
    published: "Применено",
    publish_failed: "Ошибка применения",
    rolled_back: "Откат выполнен",
    rollback_failed: "Ошибка отката",
};

function resolveErrorScopeFromWorkspace(workspaceMode: TenantsWorkspaceMode): string {
    return workspaceMode;
}

function mapWeeklySnapshotRecordToViewModel(
    record: TenantsWeeklySnapshotRecord,
): TenantsOperationalSnapshot | null {
    if (!record?.id || !record?.created_at || !record?.week_key) {
        return null;
    }
    if (!record.snapshot || typeof record.snapshot !== "object") {
        return null;
    }
    const report = record.snapshot as Partial<TenantsOperationalSnapshot["report"]>;
    if (!report.generatedAt || !report.kpi || typeof report.kpi !== "object") {
        return null;
    }
    return {
        id: record.id,
        weekKey: record.week_key,
        createdAt: record.created_at,
        report: report as TenantsOperationalSnapshot["report"],
    };
}

export default function TenantsPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const controlTowerEnabled = process.env.NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER !== "0";
    const { errors: inlineErrors, reportError, reportInlineError, clearErrors } = useInlineErrorSummary();
    const [clientQuery, setClientQuery] = useState("");
    const [branchQuery, setBranchQuery] = useState("");
    const [companyQuery, setCompanyQuery] = useState("");
    const [tenantLifecycle, setTenantLifecycle] = useState<TenantLifecycleMode>("active");
    const [workspaceMode, setWorkspaceMode] = useState<TenantsWorkspaceMode>("portfolio");
    const [viewPreset, setViewPreset] = useState<TenantsViewPreset>("operator");
    const [fleetLifecycleFilter, setFleetLifecycleFilter] = useState<FleetLifecycleFilter>("all");
    const [fleetPaymentFilter, setFleetPaymentFilter] = useState<FleetPaymentFilter>("all");
    const [fleetServiceFilter, setFleetServiceFilter] = useState<FleetServiceFilter>("all");
    const [companyEditor, setCompanyEditor] = useState<CompanyEditorState | null>(null);
    const [clientEditor, setClientEditor] = useState<ClientEditorState | null>(null);
    const [branchEditor, setBranchEditor] = useState<BranchEditorState | null>(null);
    const [savingCompany, setSavingCompany] = useState(false);
    const [savingClient, setSavingClient] = useState(false);
    const [savingBranch, setSavingBranch] = useState(false);
    const [publishingBranchChange, setPublishingBranchChange] = useState(false);
    const [rollingBackBranchChange, setRollingBackBranchChange] = useState(false);
    const [branchChangePreview, setBranchChangePreview] = useState<components["schemas"]["ConsoleBranchChangeResponse"] | null>(null);
    const [clientLifecyclePendingId, setClientLifecyclePendingId] = useState<string | null>(null);
    const [clientLifecycleDraft, setClientLifecycleDraft] = useState<ClientLifecycleDraftState | null>(null);
    const [clientLifecycleAuditById, setClientLifecycleAuditById] = useState<ClientLifecycleAuditMap>({});
    const [clientLifecycleAuditFilterById, setClientLifecycleAuditFilterById] = useState<Record<string, ClientLifecycleAuditFilter>>({});
    const [quickCreateForm, setQuickCreateForm] = useState<QuickCreateFormState>({
        companyName: "",
        clientSlug: "",
        branchName: "",
        branchSlug: "",
        branchTimezone: "Asia/Almaty",
        branchPhone: "",
        branchInstanceId: "",
        companyId: "",
        clientId: "",
    });
    const [quickCreateRunning, setQuickCreateRunning] = useState<"company" | "client" | "branch" | null>(null);
    const effectiveWorkspaceMode: TenantsWorkspaceMode = controlTowerEnabled ? workspaceMode : "portfolio";
    const {
        activeErrorScope,
        reportValidationError,
        reportProvisioningError,
        refreshContext,
        refreshTenants,
        auditSensitiveAccess,
    } = useTenantsPageOrchestration({
        controlTowerEnabled,
        workspaceMode,
        queryClient,
        reportInlineError,
        reportError,
        resolveErrorScopeFromWorkspace,
    });

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const isPlatformAdmin = role === "platform_admin";
    const canSwitchViewPreset = isPlatformAdmin;
    const isPlatformPreset = viewPreset === "platform";
    const canReadTenants = canAccessConsole(role, "tenants", "read");
    const canWriteTenants = canAccessConsole(role, "tenants", "write");

    const selectedClientId = meData?.client?.id ?? null;
    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? null;
    const selectedBranchId = meData?.selected_branch_id ?? null;
    const {
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
        hasPageFilters,
        setPageFilterCompany,
        setPageFilterClient,
        setPageFilterBranch,
        applyScopeToPageFilters,
        clearPageFilters,
    } = useTenantsPageFilters({
        searchParams,
        router,
        initialContext: {
            companyId: selectedCompanyId,
            clientId: selectedClientId,
            branchId: selectedBranchId,
        },
        canInitialize: Boolean(meData),
    });
    const knownCompanies = meData?.companies ?? [];
    const knownClients = meData?.clients ?? [];
    const knownBranches = meData?.branches ?? [];
    const quickCreateCompanyId = quickCreateForm.companyId || selectedCompanyId || "";
    const quickCreateClientId = quickCreateForm.clientId || selectedClientId || "";

    const tenantsEnabled = Boolean(session && canReadTenants);
    const companyQueryValue = companyQuery.trim() || undefined;
    const clientQueryValue = clientQuery.trim() || undefined;
    const branchQueryValue = branchQuery.trim() || undefined;

    useEffect(() => {
        setClientLifecycleAuditById(safeParseLifecycleAuditMap(readBrowserStorage(LIFECYCLE_AUDIT_STORAGE_KEY)));
    }, []);

    useEffect(() => {
        writeBrowserStorage(
            LIFECYCLE_AUDIT_STORAGE_KEY,
            JSON.stringify(clientLifecycleAuditById),
        );
    }, [clientLifecycleAuditById]);

    const {
        companiesQuery,
        tenantsPortfolioQuery,
        tenantsCompanyCockpitQuery,
        clientsQuery,
        branchesQuery,
        fleetAttentionQuery,
        branchChangesQuery,
        recentBranchChangesKpiQuery,
        selectedClientAuditQuery,
        weeklySnapshotsServerQuery,
    } = useTenantsDataQueries<TenantsOperationalSnapshot>({
        tenantsEnabled,
        companyQueryValue,
        clientQueryValue,
        branchQueryValue,
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
        tenantLifecycle,
        fleetLifecycleFilter,
        fleetPaymentFilter,
        fleetServiceFilter,
        branchEditorId: branchEditor?.id,
        maxWeeklySnapshots: MAX_WEEKLY_SNAPSHOTS,
        mapWeeklySnapshotRecordToViewModel,
    });

    const companies = useMemo(
        () => companiesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [companiesQuery.data],
    );
    const clients = useMemo(() => {
        const cockpitItems = tenantsCompanyCockpitQuery.data?.clients.items ?? [];
        if (pageFilterCompanyId && (cockpitItems.length > 0 || tenantsCompanyCockpitQuery.isSuccess)) {
            return cockpitItems;
        }
        const portfolioItems = tenantsPortfolioQuery.data?.clients.items ?? [];
        if (portfolioItems.length > 0 || tenantsPortfolioQuery.isSuccess) {
            return portfolioItems;
        }
        return clientsQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [];
    }, [
        clientsQuery.data,
        pageFilterCompanyId,
        tenantsCompanyCockpitQuery.data?.clients.items,
        tenantsCompanyCockpitQuery.isSuccess,
        tenantsPortfolioQuery.data?.clients.items,
        tenantsPortfolioQuery.isSuccess,
    ]);
    const clientsSummary = useMemo(
        () => tenantsPortfolioQuery.data?.clients.summary ?? clientsQuery.data?.pages[0]?.summary ?? null,
        [clientsQuery.data, tenantsPortfolioQuery.data?.clients.summary],
    );
    const branches = useMemo(() => {
        const items = branchesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [];
        if (!pageFilterBranchId) {
            return items;
        }
        return items.filter((branch) => branch.id === pageFilterBranchId);
    }, [branchesQuery.data, pageFilterBranchId]);
    const clientsUsingServerContract = pageFilterCompanyId
        ? tenantsCompanyCockpitQuery.isSuccess
        : tenantsPortfolioQuery.isSuccess;
    const {
        clientCompanyIdById,
        branchClientIdById,
        branchCompanyIdById,
        selectedCompanyName,
        selectedClientName,
        selectedBranchName,
        pageFilterCompanyOptions,
        pageFilterClientOptions,
        pageFilterBranchOptions,
    } = useTenantsScopeDerivedState({
        companies,
        clients,
        branches,
        knownCompanies,
        knownClients,
        knownBranches,
        selectedCompanyId,
        selectedClientId,
        selectedBranchId,
        meClientId: meData?.client?.id ?? null,
        meClientName: meData?.client?.name ?? null,
    });
    const visibleInlineErrors = useMemo(() => {
        return inlineErrors.filter((error) => error.scope === "global" || error.scope === activeErrorScope);
    }, [activeErrorScope, inlineErrors]);
    const activeErrorScopeLabel = activeErrorScope;
    const latestPublishedBranchChange = useMemo(() => {
        const items = branchChangesQuery.data?.items ?? [];
        return (
            (items.find((item) => item.status === "published") as BranchChangeRecord | undefined) ?? null
        );
    }, [branchChangesQuery.data]);
    const previewChange = branchChangePreview?.change as BranchChangeRecord | undefined;
    const previewDiffEntries = useMemo(() => {
        const diff = previewChange?.diff_payload;
        if (!diff || typeof diff !== "object") {
            return [] as Array<{ field: string; before: string; after: string }>;
        }
        return Object.entries(diff as Record<string, unknown>).map(([field, rawValue]) => {
            const value = rawValue && typeof rawValue === "object"
                ? (rawValue as Record<string, unknown>)
                : {};
            return {
                field,
                before: JSON.stringify(value.before ?? null),
                after: JSON.stringify(value.after ?? null),
            };
        });
    }, [previewChange]);
    const previewValidationErrors = useMemo(() => {
        const payload = previewChange?.validation_payload;
        if (!payload || typeof payload !== "object") {
            return [] as string[];
        }
        const errors = (payload as Record<string, unknown>).errors;
        if (!Array.isArray(errors)) {
            return [] as string[];
        }
        return errors
            .map((item) => (typeof item === "string" ? item : ""))
            .filter((item) => item.length > 0);
    }, [previewChange]);
    const fleetAttention = useMemo(
        () => tenantsPortfolioQuery.data?.fleet_attention ?? fleetAttentionQuery.data ?? null,
        [fleetAttentionQuery.data, tenantsPortfolioQuery.data?.fleet_attention],
    );
    const fleetAttentionLoading = tenantsPortfolioQuery.isLoading || fleetAttentionQuery.isLoading;
    const fleetAttentionErrored = !fleetAttention && (tenantsPortfolioQuery.isError || fleetAttentionQuery.isError);
    const clientsLoading = tenantsPortfolioQuery.isLoading || clientsQuery.isLoading || tenantsCompanyCockpitQuery.isLoading;
    const clientsErrored = clients.length === 0 && (
        tenantsPortfolioQuery.isError
        || clientsQuery.isError
        || tenantsCompanyCockpitQuery.isError
    );
    const branchesLoading = branchesQuery.isLoading || tenantsCompanyCockpitQuery.isLoading;
    const branchesErrored = branches.length === 0 && (branchesQuery.isError || tenantsCompanyCockpitQuery.isError);
    const recentBranchChangesForKpi = useMemo(
        () => recentBranchChangesKpiQuery.data?.items ?? [],
        [recentBranchChangesKpiQuery.data],
    );
    const selectedClientApiAuditEntries = useMemo(() => {
        const events = selectedClientAuditQuery.data ?? [];
        return events
            .map((event) => mapAuditEventToLifecycleEntry(event))
            .filter((entry): entry is ClientLifecycleAuditEntry => entry !== null);
    }, [selectedClientAuditQuery.data]);
    const {
        onboardingThroughput,
        operationalKpi,
        operationalKpiDrilldown,
        operationalKpiById,
        criticalKpiCount,
        warnKpiCount,
        alertHookPayload,
        operationalReport,
    } = useTenantsOperationalModel({
        clientsSummary,
        fleetAttention,
        recentBranchChangesForKpi,
        effectiveWorkspaceMode,
        tenantLifecycle,
    });

    const {
        setCompanyContext,
        setClientContext,
        setBranchContext,
        clearContextLens,
        setClientContextAndPageFilters,
        setBranchContextAndPageFilters,
        applyContextToPageFilters,
        openClientContextTarget,
        runActionQueueIntent,
        runKpiAction,
        startCompanyEdit,
        startClientEdit,
        startBranchEdit,
        openClientLifecycleAction,
        closeClientLifecycleDraft,
        handleClientLifecycleAction,
        requiresBranchConfirmation,
        handlePreviewBranchChange,
        handlePublishBranchChange,
        handleRollbackBranchChange,
        cancelBranchEdit,
        handleSaveCompany,
        handleSaveClient,
        handleQuickCreateCompany,
        handleQuickCreateClient,
        handleQuickCreateBranch,
    } = useTenantsActions({
        clientCompanyIdById,
        branchClientIdById,
        branchCompanyIdById,
        pageFilterCompanyId,
        pageFilterClientId,
        applyScopeToPageFilters,
        refreshContext,
        reportValidationError,
        setWorkspaceMode,
        setTenantLifecycle,
        navigateTo: (target) => router.push(target),
        quickCreateForm,
        quickCreateCompanyId,
        quickCreateClientId,
        setQuickCreateForm,
        setQuickCreateRunning,
        branchEditor,
        branchChangePreview,
        latestPublishedBranchChange,
        clientLifecycleDraft,
        clientLifecyclePendingId,
        setBranchEditor,
        setBranchChangePreview,
        setSavingBranch,
        setPublishingBranchChange,
        setRollingBackBranchChange,
        setClientLifecycleDraft,
        setClientLifecyclePendingId,
        setClientLifecycleAuditById,
        companyEditor,
        clientEditor,
        setCompanyEditor,
        setClientEditor,
        setSavingCompany,
        setSavingClient,
        role,
        actorLabel: meData?.agent?.name ?? role,
        lifecycleArchivedLabel: FLEET_LIFECYCLE_LABELS.archived,
        lifecycleActiveLabel: FLEET_LIFECYCLE_LABELS.active,
        formatLifecycleLabel: (value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS),
        pushLifecycleAuditEntry,
        buildBranchChangePatch,
        applyBranchSnapshotToEditor,
        refetchBranchChanges: () => branchChangesQuery.refetch(),
        refreshTenants,
        reportProvisioningError,
        slugInputPattern: SLUG_INPUT_PATTERN,
        branchPhoneInputPattern: BRANCH_PHONE_INPUT_PATTERN,
        isValidTimezoneName,
    });

    const {
        weeklySnapshots,
        runningMetricsSnapshotMode,
        lastMetricsSnapshotJob,
        exportOperationalReport,
        saveWeeklySnapshot,
        copyAlertHookPayload,
        runMetricsSnapshotHook,
    } = useTenantsPageOperations<TenantsOperationalSnapshot>({
        pageFilterClientId,
        operationalReport,
        alertHookPayload,
        operationalKpiDrilldown,
        queryClient,
        weeklySnapshotsServerData: weeklySnapshotsServerQuery.data,
        mapWeeklySnapshotRecordToViewModel,
        buildLocalSnapshot: ({ id, createdAt, weekKey, report }) => ({
            id,
            createdAt,
            weekKey,
            report,
        }),
        buildWeekKey: toIsoWeekKey,
        maxWeeklySnapshots: MAX_WEEKLY_SNAPSHOTS,
        reportValidationError,
        reportError,
        activeErrorScope,
    });

    const { actionQueue, isClientArchived } = useTenantsActionQueue({
        tenantLifecycle,
        fleetAttention,
        operationalKpi,
        clientsSummary,
    });

    const showPortfolio = effectiveWorkspaceMode === "portfolio";
    const showOnboarding = effectiveWorkspaceMode === "onboarding";
    const showChangeManagement = effectiveWorkspaceMode === "changes";
    const showDecommission = effectiveWorkspaceMode === "decommission";
    const showClientsSection = showPortfolio || showDecommission;
    const decommissionFocused = effectiveWorkspaceMode === "decommission";

    const refreshActionQueue = () => {
        tenantsPortfolioQuery.refetch();
        if (pageFilterCompanyId) {
            tenantsCompanyCockpitQuery.refetch();
        }
        fleetAttentionQuery.refetch();
        recentBranchChangesKpiQuery.refetch();
        clientsQuery.refetch();
    };
    const refreshOperationalPanels = () => {
        tenantsPortfolioQuery.refetch();
        if (pageFilterCompanyId) {
            tenantsCompanyCockpitQuery.refetch();
        }
        fleetAttentionQuery.refetch();
        recentBranchChangesKpiQuery.refetch();
        selectedClientAuditQuery.refetch();
        if (pageFilterClientId) {
            weeklySnapshotsServerQuery.refetch();
        }
    };
    const refreshFleetAttention = () => {
        tenantsPortfolioQuery.refetch();
        fleetAttentionQuery.refetch();
    };

    return (
        <TenantsPageView
            session={session}
            meLoading={meLoading}
            canReadTenants={canReadTenants}
            canWriteTenants={canWriteTenants}
            controlTowerEnabled={controlTowerEnabled}
            tenantLifecycle={tenantLifecycle}
            onTenantLifecycleChange={setTenantLifecycle}
            topControlsProps={{
                isPlatformPreset,
                contextCompanyName: selectedCompanyName,
                contextClientName: selectedClientName,
                contextBranchName: selectedBranchName,
                contextCompanyId: selectedCompanyId,
                contextClientId: selectedClientId,
                contextBranchId: selectedBranchId,
                onClearBranchContext: () => setBranchContext(null),
                onClearClientContext: () => {
                    const scope = readConsoleContextScopeFromStorage();
                    setClientContext(null, scope.companyId || null);
                },
                onClearContext: clearContextLens,
                pageFilterCompanyId,
                pageFilterClientId,
                pageFilterBranchId,
                pageFilterCompanyOptions,
                pageFilterClientOptions,
                pageFilterBranchOptions,
                hasPageFilters,
                onPageFilterCompanyChange: setPageFilterCompany,
                onPageFilterClientChange: setPageFilterClient,
                onPageFilterBranchChange: setPageFilterBranch,
                onApplyContextToPageFilters: applyContextToPageFilters,
                onClearPageFilters: clearPageFilters,
                controlTowerEnabled,
                workspaceMode: effectiveWorkspaceMode,
                onWorkspaceModeChange: (value) => {
                    if (controlTowerEnabled) {
                        setWorkspaceMode(value);
                    }
                },
                viewPreset,
                onViewPresetChange: setViewPreset,
                canSwitchViewPreset,
            }}
            scopedErrorSummaryProps={{
                errors: visibleInlineErrors,
                scopeLabel: activeErrorScopeLabel,
                showScopeClear: true,
                onClearScope: () => clearErrors(activeErrorScope),
                onClearAll: () => clearErrors(),
            }}
            quickCreatePanelProps={{
                form: quickCreateForm,
                running: quickCreateRunning,
                companyId: quickCreateCompanyId,
                clientId: quickCreateClientId,
                onChange: (patch) => setQuickCreateForm((prev) => ({ ...prev, ...patch })),
                onCreateCompany: () => void handleQuickCreateCompany(),
                onCreateClient: () => void handleQuickCreateClient(),
                onCreateBranch: () => void handleQuickCreateBranch(),
                onOpenWorkspace: () => router.push("/company-workspace"),
            }}
            actionQueue={{
                show: controlTowerEnabled,
                items: actionQueue,
                refreshing: (
                    tenantsPortfolioQuery.isFetching
                    || tenantsCompanyCockpitQuery.isFetching
                    || fleetAttentionQuery.isFetching
                    || recentBranchChangesKpiQuery.isFetching
                    || clientsQuery.isFetching
                ),
                onRefresh: refreshActionQueue,
                onRunIntent: runActionQueueIntent,
                onSetClientContext: setClientContextAndPageFilters,
            }}
            operationalKpiPanel={{
                show: controlTowerEnabled && showPortfolio && tenantLifecycle === "active",
                props: {
                    isRefreshing: (
                        tenantsPortfolioQuery.isFetching
                        || tenantsCompanyCockpitQuery.isFetching
                        || fleetAttentionQuery.isFetching
                        || recentBranchChangesKpiQuery.isFetching
                    ),
                    onRefresh: refreshOperationalPanels,
                    onExportJson: () => exportOperationalReport("json"),
                    onExportCsv: () => exportOperationalReport("csv"),
                    onSaveWeeklySnapshot: saveWeeklySnapshot,
                    canSaveWeeklySnapshot: Boolean(pageFilterClientId),
                    operationalKpi,
                    criticalKpiCount,
                    warnKpiCount,
                    kpiStatuses: {
                        onboardingCoverage: operationalKpiById.get("onboardingCoverage")?.status ?? "ok",
                        goLiveReadiness: operationalKpiById.get("goLiveReadiness")?.status ?? "ok",
                        serviceStability: operationalKpiById.get("serviceStability")?.status ?? "ok",
                        decommissionShare: operationalKpiById.get("decommissionShare")?.status ?? "ok",
                        changeFailure: operationalKpiById.get("changeFailure")?.status ?? "ok",
                        rollbackShare: operationalKpiById.get("rollbackShare")?.status ?? "ok",
                        blockedSignals: operationalKpiById.get("blockedSignals")?.status ?? "ok",
                    },
                    kpiDrilldown: operationalKpiDrilldown,
                    onRunKpiAction: runKpiAction,
                    onboardingThroughput,
                    formatOptionalHours,
                    formatOptionalPercent,
                    alertSeverity: alertHookPayload.severity,
                    alertBreachesCount: alertHookPayload.breaches.length,
                    onCopyAlertPayload: copyAlertHookPayload,
                    onRunMetricsSnapshot: runMetricsSnapshotHook,
                    runningMetricsSnapshotMode,
                    lastMetricsSnapshotJob,
                    pageFilterClientId,
                    weeklySnapshotsFetching: weeklySnapshotsServerQuery.isFetching,
                    weeklySnapshots,
                    formatDateTimeLabel,
                },
            }}
            fleetAttentionPanel={{
                show: controlTowerEnabled && showPortfolio && tenantLifecycle === "active",
                props: {
                    fleetAttention,
                    loading: fleetAttentionLoading,
                    errored: fleetAttentionErrored,
                    refreshing: tenantsPortfolioQuery.isFetching || fleetAttentionQuery.isFetching,
                    onRefresh: refreshFleetAttention,
                    attentionLevelClass,
                    formatLifecycleLabel: (value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS),
                    formatServiceLabel: (value) => formatStateLabel(value, FLEET_SERVICE_LABELS),
                    formatReferenceScopeReason,
                    onSetClientContext: setClientContextAndPageFilters,
                    onOpenIntegrations: (clientId, companyId) => openClientContextTarget("/integrations", clientId, companyId),
                    onOpenCases: (clientId, companyId) => openClientContextTarget("/", clientId, companyId),
                },
            }}
            portfolioCompaniesPanel={{
                show: showPortfolio,
                props: {
                    companies,
                    loading: companiesQuery.isLoading,
                    errored: companiesQuery.isError,
                    query: companyQuery,
                    onQueryChange: setCompanyQuery,
                    isPlatformPreset,
                    canWriteTenants,
                    selectedCompanyId,
                    companyEditor,
                    savingCompany,
                    hasNextPage: Boolean(companiesQuery.hasNextPage),
                    isFetchingNextPage: companiesQuery.isFetchingNextPage,
                    onFetchNextPage: () => companiesQuery.fetchNextPage(),
                    onStartEdit: startCompanyEdit,
                    onSetContext: setCompanyContext,
                    onCancelEdit: () => setCompanyEditor(null),
                    onSaveEdit: handleSaveCompany,
                    onChangeEditorName: (value) => {
                        setCompanyEditor((prev) => (prev ? { ...prev, name: value } : prev));
                    },
                    onChangeEditorBillingInfo: (value) => {
                        setCompanyEditor((prev) => (prev ? { ...prev, billingInfo: value } : prev));
                    },
                },
            }}
            decommissionPanel={{
                show: showDecommission,
                props: {
                    tenantLifecycle,
                    onTenantLifecycleChange: setTenantLifecycle,
                },
            }}
            clientsPanel={{
                show: showClientsSection,
                props: {
                    decommissionFocused,
                    clientsLoading,
                    clientsErrored,
                    clients,
                    clientsSummary,
                    pageFilterCompanyId,
                    clientQuery,
                    onClientQueryChange: setClientQuery,
                    fleetLifecycleFilter,
                    onFleetLifecycleFilterChange: setFleetLifecycleFilter,
                    fleetPaymentFilter,
                    onFleetPaymentFilterChange: setFleetPaymentFilter,
                    fleetServiceFilter,
                    onFleetServiceFilterChange: setFleetServiceFilter,
                    isPlatformPreset,
                    canWriteTenants,
                    selectedClientId,
                    pageFilterClientId,
                    clientEditor,
                    savingClient,
                    knownCompanies,
                    clientLifecyclePendingId,
                    clientLifecycleAuditFilterById,
                    clientLifecycleAuditById,
                    selectedClientApiAuditEntries,
                    selectedClientAuditIsFetching: selectedClientAuditQuery.isFetching,
                    onRefreshSelectedClientAudit: () => selectedClientAuditQuery.refetch(),
                    onSetClientLifecycleAuditFilter: (clientId, filter) => {
                        setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientId]: filter }));
                    },
                    mergeLifecycleAuditEntries,
                    formatLifecycleLabel: (value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS),
                    formatPaymentLabel: (value) => formatStateLabel(value, FLEET_PAYMENT_LABELS),
                    formatServiceLabel: (value) => formatStateLabel(value, FLEET_SERVICE_LABELS),
                    formatReferenceScopeReason,
                    formatDateTimeLabel,
                    isClientArchived,
                    onStartClientEdit: startClientEdit,
                    onOpenClientLifecycleAction: openClientLifecycleAction,
                    onSetClientContext: setClientContextAndPageFilters,
                    onClientEditorSlugChange: (value) => {
                        setClientEditor((prev) => (prev ? { ...prev, slug: value } : prev));
                    },
                    onClientEditorCompanyChange: (value) => {
                        setClientEditor((prev) => (prev ? { ...prev, companyId: value } : prev));
                    },
                    onSaveClientEdit: handleSaveClient,
                    onCancelClientEdit: () => setClientEditor(null),
                    clientsUsingServerContract,
                    clientsHasNextPage: Boolean(clientsQuery.hasNextPage),
                    clientsFetchingNextPage: clientsQuery.isFetchingNextPage,
                    onFetchNextClientsPage: () => clientsQuery.fetchNextPage(),
                },
            }}
            branchChangePanel={{
                show: showChangeManagement,
                props: {
                    branchesLoading,
                    branchesErrored,
                    branches,
                    pageFilterClientId,
                    selectedClientName,
                    branchQuery,
                    onBranchQueryChange: setBranchQuery,
                    isPlatformPreset,
                    canWriteTenants,
                    selectedBranchId,
                    contextScope: effectiveWorkspaceMode,
                    onAuditSensitiveAccess: auditSensitiveAccess,
                    onStartBranchEdit: startBranchEdit,
                    onSetBranchContext: (branch) =>
                        setBranchContextAndPageFilters({
                            branchId: branch.id,
                            clientId: branch.id ? (branchClientIdById.get(branch.id) ?? null) : null,
                            companyId: branch.id ? (branchCompanyIdById.get(branch.id) ?? null) : null,
                        }),
                    branchEditor,
                    onPatchBranchEditor: (patch) => {
                        setBranchEditor((prev) => (prev ? { ...prev, ...patch } : prev));
                    },
                    requiresBranchConfirmation,
                    savingBranch,
                    publishingBranchChange,
                    rollingBackBranchChange,
                    onPreviewBranchChange: handlePreviewBranchChange,
                    onPublishBranchChange: handlePublishBranchChange,
                    onRollbackBranchChange: handleRollbackBranchChange,
                    onCancelBranchEdit: cancelBranchEdit,
                    branchChangePreview,
                    previewValidationErrors,
                    previewDiffEntries,
                    hasPublishedBranchChange: Boolean(latestPublishedBranchChange),
                    branchChangesLoading: branchChangesQuery.isLoading,
                    branchChangesItems: branchChangesQuery.data?.items ?? [],
                    formatBranchChangeStatus: (value) => formatStateLabel(value, BRANCH_CHANGE_STATUS_LABELS),
                    branchesHasNextPage: Boolean(branchesQuery.hasNextPage),
                    branchesFetchingNextPage: branchesQuery.isFetchingNextPage,
                    onFetchNextBranchesPage: () => branchesQuery.fetchNextPage(),
                },
            }}
            lifecycleModalProps={{
                draft: clientLifecycleDraft,
                pending: Boolean(clientLifecyclePendingId),
                onClose: closeClientLifecycleDraft,
                onSubmit: handleClientLifecycleAction,
                onPatchDraft: (patch) => {
                    setClientLifecycleDraft((prev) => (prev ? { ...prev, ...patch } : prev));
                },
            }}
            showOnboarding={showOnboarding}
            onOpenWorkspaceFromOnboarding={() => router.push("/company-workspace")}
        />
    );
}
