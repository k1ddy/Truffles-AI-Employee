"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import TenantsActionQueuePanel from "@/components/TenantsActionQueuePanel";
import TenantsBranchChangeManagementPanel from "@/components/TenantsBranchChangeManagementPanel";
import TenantsClientLifecycleModal from "@/components/TenantsClientLifecycleModal";
import TenantsClientsPanel from "@/components/TenantsClientsPanel";
import TenantsDecommissionPanel from "@/components/TenantsDecommissionPanel";
import TenantsFleetAttentionPanel from "@/components/TenantsFleetAttentionPanel";
import TenantsOperationalKpiPanel from "@/components/TenantsOperationalKpiPanel";
import TenantsPortfolioCompaniesPanel from "@/components/TenantsPortfolioCompaniesPanel";
import TenantsQuickCreatePanel from "@/components/TenantsQuickCreatePanel";
import TenantsScopedErrorSummary from "@/components/TenantsScopedErrorSummary";
import type { TenantsSensitiveAction } from "@/components/TenantsSensitiveIdCell";
import TenantsTopControls from "@/components/TenantsTopControls";
import {
    adminApi,
    authApi,
    canAccessConsole,
    opsApi,
    type TenantsOperationalSnapshotPayload,
    type TenantsWeeklySnapshotRecord,
} from "@/lib/api-client";
import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import {
    readConsoleContextScopeFromStorage,
} from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";
import {
    asPercent,
    buildOperationalKpiDrilldown,
    formatOptionalHours,
    formatOptionalPercent,
    type OperationalKpiDrilldown,
    type OperationalKpiId,
    type OperationalKpiStatus,
} from "./operational-kpi";
import { useTenantsDataQueries } from "./use-tenants-data-queries";
import { useTenantsActions } from "./use-tenants-actions";
import { useTenantsActionQueue } from "./use-tenants-action-queue";
import { useTenantsPageFilters } from "./use-tenants-page-filters";
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

function toCsvCell(value: string | number): string {
    const raw = String(value);
    if (raw.includes(",") || raw.includes("\"") || raw.includes("\n")) {
        return `"${raw.replaceAll("\"", "\"\"")}"`;
    }
    return raw;
}

export default function TenantsPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const controlTowerEnabled = process.env.NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER !== "0";
    const { errors: inlineErrors, reportError, reportInlineError, clearErrors } = useInlineErrorSummary();
    const reportValidationError = (
        message: string,
        code = "VALIDATION_ERROR",
        scope?: string,
    ) => {
        const resolvedScope = scope ?? resolveErrorScopeFromWorkspace(controlTowerEnabled ? workspaceMode : "portfolio");
        reportInlineError({ code, message, scope: resolvedScope });
        toast.error(message);
    };
    const reportProvisioningError = (error: unknown, operation: string, endpoint: string) =>
        reportError(error, {
            includeProvisioningGuidance: true,
            operation,
            endpoint,
            scope: resolveErrorScopeFromWorkspace(controlTowerEnabled ? workspaceMode : "portfolio"),
        });
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
    const [weeklySnapshots, setWeeklySnapshots] = useState<TenantsOperationalSnapshot[]>([]);
    const [runningMetricsSnapshotMode, setRunningMetricsSnapshotMode] = useState<"dry_run" | "execute" | null>(null);
    const [lastMetricsSnapshotJob, setLastMetricsSnapshotJob] = useState<components["schemas"]["ConsoleOpsJobRecord"] | null>(null);
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
    useEffect(() => {
        if (!pageFilterClientId) {
            setWeeklySnapshots([]);
            return;
        }
        if (!weeklySnapshotsServerQuery.data) {
            return;
        }
        setWeeklySnapshots(weeklySnapshotsServerQuery.data);
    }, [pageFilterClientId, weeklySnapshotsServerQuery.data]);

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
    const onboardingThroughput = useMemo(
        () => clientsSummary?.onboarding_throughput ?? null,
        [clientsSummary],
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
    const activeErrorScope = useMemo(
        () => resolveErrorScopeFromWorkspace(effectiveWorkspaceMode),
        [effectiveWorkspaceMode],
    );
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
    const operationalKpi = useMemo(() => {
        const summary = clientsSummary;
        const attentionSummary = fleetAttention?.summary;
        const totalClients = summary?.total_clients ?? 0;
        const activeClients = summary?.active_clients ?? 0;
        const onboardingClients = summary?.onboarding_clients ?? 0;
        const goLiveReadyClients = summary?.go_live_ready_clients ?? 0;
        const archivedClients = summary?.archived_clients ?? 0;
        const degradedClients = summary?.degraded_clients ?? 0;

        const totalChanges = recentBranchChangesForKpi.length;
        const publishedChanges = recentBranchChangesForKpi.filter((item) => item.status === "published").length;
        const publishFailedChanges = recentBranchChangesForKpi.filter((item) => item.status === "publish_failed").length;
        const rolledBackChanges = recentBranchChangesForKpi.filter((item) => item.status === "rolled_back").length;

        return {
            onboardingCoveragePct: asPercent(onboardingClients + goLiveReadyClients, totalClients),
            goLiveReadinessPct: asPercent(goLiveReadyClients, onboardingClients + goLiveReadyClients),
            serviceStabilityPct: asPercent(Math.max(activeClients - degradedClients, 0), activeClients),
            decommissionSharePct: asPercent(archivedClients, totalClients),
            changeFailurePct: asPercent(publishFailedChanges, totalChanges),
            rollbackSharePct: asPercent(rolledBackChanges, publishedChanges + rolledBackChanges),
            blockedSignalsCount:
                (attentionSummary?.outbox_failed_24h_total ?? 0)
                + (attentionSummary?.pending_handovers_total ?? 0)
                + publishFailedChanges,
            sourceWindow: totalChanges,
            publishedChanges,
            publishFailedChanges,
            rolledBackChanges,
        };
    }, [clientsSummary, fleetAttention, recentBranchChangesForKpi]);
    const operationalKpiValues = useMemo<Record<OperationalKpiId, number>>(() => ({
        onboardingCoverage: operationalKpi.onboardingCoveragePct,
        goLiveReadiness: operationalKpi.goLiveReadinessPct,
        serviceStability: operationalKpi.serviceStabilityPct,
        decommissionShare: operationalKpi.decommissionSharePct,
        changeFailure: operationalKpi.changeFailurePct,
        rollbackShare: operationalKpi.rollbackSharePct,
        blockedSignals: operationalKpi.blockedSignalsCount,
    }), [operationalKpi]);
    const operationalKpiDrilldown = useMemo(
        () => buildOperationalKpiDrilldown(operationalKpiValues),
        [operationalKpiValues],
    );
    const operationalKpiById = useMemo(() => {
        const map = new Map<OperationalKpiId, OperationalKpiDrilldown>();
        for (const item of operationalKpiDrilldown) {
            map.set(item.id, item);
        }
        return map;
    }, [operationalKpiDrilldown]);
    const criticalKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "critical").length,
        [operationalKpiDrilldown],
    );
    const warnKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "warn").length,
        [operationalKpiDrilldown],
    );
    const alertHookPayload = useMemo(() => {
        const breaches = operationalKpiDrilldown
            .filter((item) => item.status !== "ok")
            .map((item) => ({
                metric: item.id,
                label: item.label,
                status: item.status,
                value: item.value,
                reason: item.reason,
                action: item.action,
            }));
        const severity = breaches.some((item) => item.status === "critical")
            ? "critical"
            : breaches.length > 0
                ? "warning"
                : "ok";
        return {
            generated_at: new Date().toISOString(),
            severity,
            source_window: operationalKpi.sourceWindow,
            breaches,
            attention_summary: {
                active_clients_total: fleetAttention?.summary?.active_clients_total ?? 0,
                high_risk_clients: fleetAttention?.summary?.high_risk_clients ?? 0,
                medium_risk_clients: fleetAttention?.summary?.medium_risk_clients ?? 0,
                outbox_failed_24h_total: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
                pending_handovers_total: fleetAttention?.summary?.pending_handovers_total ?? 0,
            },
        };
    }, [operationalKpiDrilldown, operationalKpi.sourceWindow, fleetAttention?.summary]);
    const operationalReport = useMemo<TenantsOperationalSnapshotPayload>(() => ({
        generatedAt: new Date().toISOString(),
        sourceWindow: operationalKpi.sourceWindow,
        workspaceMode: effectiveWorkspaceMode,
        lifecycleMode: tenantLifecycle,
        kpi: operationalKpiValues,
        drilldown: operationalKpiDrilldown.map((item) => ({
            id: item.id,
            status: item.status,
            value: item.value,
            reason: item.reason,
        })),
        attentionSummary: {
            activeClientsTotal: fleetAttention?.summary?.active_clients_total ?? 0,
            highRiskClients: fleetAttention?.summary?.high_risk_clients ?? 0,
            mediumRiskClients: fleetAttention?.summary?.medium_risk_clients ?? 0,
            outboxFailed24hTotal: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
            pendingHandoversTotal: fleetAttention?.summary?.pending_handovers_total ?? 0,
        },
    }), [operationalKpi.sourceWindow, operationalKpiValues, operationalKpiDrilldown, fleetAttention?.summary, effectiveWorkspaceMode, tenantLifecycle]);

    const refreshContext = () => {
        queryClient.invalidateQueries({ queryKey: ["console-me"] });
    };

    const refreshTenants = () => {
        queryClient.invalidateQueries({ queryKey: ["tenants-companies"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-clients"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branches"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-fleet-attention"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branch-changes-recent-kpi"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-client-lifecycle-audit-api"] });
    };
    const auditSensitiveAccess = async (input: {
        branchId: string;
        field: "instance_id";
        action: TenantsSensitiveAction;
        contextScope?: string;
    }) => {
        try {
            await adminApi.auditTenantsSensitiveAccess({
                branch_id: input.branchId,
                field: input.field,
                action: input.action,
                context: input.contextScope,
            });
        } catch (error) {
            reportError(error, { scope: "changes" });
            throw error;
        }
    };

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

    const exportOperationalReport = (format: "json" | "csv") => {
        const timestamp = new Date().toISOString().replaceAll(":", "-");
        if (format === "json") {
            const content = JSON.stringify(
                {
                    report: operationalReport,
                    alert_payload: alertHookPayload,
                },
                null,
                2,
            );
            const blob = new Blob([content], { type: "application/json;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `tenants-operational-report-${timestamp}.json`;
            link.click();
            URL.revokeObjectURL(url);
            toast.success("Отчёт JSON выгружен");
            return;
        }
        const rows = [
            ["metric", "value", "status", "reason"],
            ...operationalKpiDrilldown.map((item) => [
                item.id,
                item.displayValue,
                item.status,
                item.reason,
            ]),
        ];
        const csvContent = rows.map((row) => row.map((cell) => toCsvCell(cell)).join(",")).join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `tenants-operational-report-${timestamp}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success("Отчёт CSV выгружен");
    };

    const saveWeeklySnapshot = async () => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы", "VALIDATION_ERROR", "portfolio");
            return;
        }
        const now = new Date().toISOString();
        const weekKey = toIsoWeekKey(now);
        const localSnapshot: TenantsOperationalSnapshot = {
            id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : `${Date.now()}`,
            weekKey,
            createdAt: now,
            report: operationalReport,
        };
        const applySnapshot = (snapshot: TenantsOperationalSnapshot) => {
            setWeeklySnapshots((previous) => {
                const withoutWeek = previous.filter((item) => item.weekKey !== snapshot.weekKey);
                return [snapshot, ...withoutWeek].slice(0, MAX_WEEKLY_SNAPSHOTS);
            });
        };
        try {
            const response = await adminApi.saveTenantsWeeklySnapshot({
                client_id: pageFilterClientId,
                week_key: weekKey,
                snapshot: operationalReport,
            });
            const mappedSnapshot = mapWeeklySnapshotRecordToViewModel(response.data.item);
            applySnapshot(mappedSnapshot ?? localSnapshot);
                queryClient.invalidateQueries({
                    queryKey: ["tenants-weekly-snapshots", pageFilterClientId],
                });
            toast.success(`Недельный снимок сохранён (${weekKey})`);
        } catch (error) {
            reportError(error, { scope: "portfolio" });
            toast.error(`Не удалось сохранить недельный снимок (${weekKey})`);
        }
    };

    const copyAlertHookPayload = async () => {
        const serialized = JSON.stringify(alertHookPayload, null, 2);
        try {
            await navigator.clipboard.writeText(serialized);
            toast.success("Данные уведомления скопированы");
        } catch {
            reportValidationError("Не удалось скопировать данные уведомления");
        }
    };

    const runMetricsSnapshotHook = async (mode: "dry_run" | "execute") => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы");
            return;
        }
        setRunningMetricsSnapshotMode(mode);
        try {
            const response = await opsApi.runJob({
                job_type: "metrics_snapshot",
                mode,
                params: ({ days: 7 } as unknown as Record<string, never>),
            });
            setLastMetricsSnapshotJob(response.data.job);
            toast.success(mode === "dry_run" ? "Пробный снимок метрик выполнен" : "Снимок метрик выполнен");
        } catch (error) {
            reportError(error, { scope: resolveErrorScopeFromWorkspace(effectiveWorkspaceMode) });
        } finally {
            setRunningMetricsSnapshotMode(null);
        }
    };

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

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра вкладки «Тенанты».
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

    if (!canReadTenants) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к вкладке Тенанты." />
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="tenants-page">
            <div className="flex flex-col gap-2 mb-6">
                {!controlTowerEnabled ? (
                    <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-xs text-amber-900" data-testid="tenants-control-tower-flag-banner">
                        `TENANTS_V3_CONTROL_TOWER=0`: включён базовый режим Tenants без расширенной control-tower панели.
                    </div>
                ) : null}
                <TenantsTopControls
                    isPlatformPreset={isPlatformPreset}
                    contextCompanyName={selectedCompanyName}
                    contextClientName={selectedClientName}
                    contextBranchName={selectedBranchName}
                    contextCompanyId={selectedCompanyId}
                    contextClientId={selectedClientId}
                    contextBranchId={selectedBranchId}
                    onClearBranchContext={() => setBranchContext(null)}
                    onClearClientContext={() => {
                        const scope = readConsoleContextScopeFromStorage();
                        setClientContext(null, scope.companyId || null);
                    }}
                    onClearContext={clearContextLens}
                    pageFilterCompanyId={pageFilterCompanyId}
                    pageFilterClientId={pageFilterClientId}
                    pageFilterBranchId={pageFilterBranchId}
                    pageFilterCompanyOptions={pageFilterCompanyOptions}
                    pageFilterClientOptions={pageFilterClientOptions}
                    pageFilterBranchOptions={pageFilterBranchOptions}
                    hasPageFilters={hasPageFilters}
                    onPageFilterCompanyChange={setPageFilterCompany}
                    onPageFilterClientChange={setPageFilterClient}
                    onPageFilterBranchChange={setPageFilterBranch}
                    onApplyContextToPageFilters={applyContextToPageFilters}
                    onClearPageFilters={clearPageFilters}
                    controlTowerEnabled={controlTowerEnabled}
                    workspaceMode={effectiveWorkspaceMode}
                    onWorkspaceModeChange={(value) => {
                        if (controlTowerEnabled) {
                            setWorkspaceMode(value);
                        }
                    }}
                    viewPreset={viewPreset}
                    onViewPresetChange={setViewPreset}
                    canSwitchViewPreset={canSwitchViewPreset}
                />
                <TenantsScopedErrorSummary
                    errors={visibleInlineErrors}
                    scopeLabel={activeErrorScopeLabel}
                    showScopeClear
                    onClearScope={() => clearErrors(activeErrorScope)}
                    onClearAll={() => clearErrors()}
                />
                {canWriteTenants ? (
                    <TenantsQuickCreatePanel
                        form={quickCreateForm}
                        running={quickCreateRunning}
                        companyId={quickCreateCompanyId}
                        clientId={quickCreateClientId}
                        onChange={(patch) => setQuickCreateForm((prev) => ({ ...prev, ...patch }))}
                        onCreateCompany={() => void handleQuickCreateCompany()}
                        onCreateClient={() => void handleQuickCreateClient()}
                        onCreateBranch={() => void handleQuickCreateBranch()}
                        onOpenWorkspace={() => router.push("/company-workspace")}
                    />
                ) : null}
                {controlTowerEnabled ? (
                    <TenantsActionQueuePanel
                        items={actionQueue}
                        refreshing={
                            tenantsPortfolioQuery.isFetching
                            || tenantsCompanyCockpitQuery.isFetching
                            || fleetAttentionQuery.isFetching
                            || recentBranchChangesKpiQuery.isFetching
                            || clientsQuery.isFetching
                        }
                        onRefresh={() => {
                            tenantsPortfolioQuery.refetch();
                            if (pageFilterCompanyId) {
                                tenantsCompanyCockpitQuery.refetch();
                            }
                            fleetAttentionQuery.refetch();
                            recentBranchChangesKpiQuery.refetch();
                            clientsQuery.refetch();
                        }}
                        onRunIntent={runActionQueueIntent}
                        onSetClientContext={setClientContextAndPageFilters}
                    />
                ) : null}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-muted-foreground">Режим списка:</span>
                    <button
                        className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("active")}
                    >
                        Активные
                    </button>
                    <button
                        className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("archived")}
                    >
                        Архив
                    </button>
                    <button
                        className={tenantLifecycle === "all" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("all")}
                    >
                        Все
                    </button>
                </div>
            </div>

            <div className="grid gap-6">
                {controlTowerEnabled && showPortfolio && tenantLifecycle === "active" ? (
                    <TenantsOperationalKpiPanel
                        isRefreshing={
                            tenantsPortfolioQuery.isFetching
                            || tenantsCompanyCockpitQuery.isFetching
                            || fleetAttentionQuery.isFetching
                            || recentBranchChangesKpiQuery.isFetching
                        }
                        onRefresh={() => {
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
                        }}
                        onExportJson={() => exportOperationalReport("json")}
                        onExportCsv={() => exportOperationalReport("csv")}
                        onSaveWeeklySnapshot={saveWeeklySnapshot}
                        canSaveWeeklySnapshot={Boolean(pageFilterClientId)}
                        operationalKpi={operationalKpi}
                        criticalKpiCount={criticalKpiCount}
                        warnKpiCount={warnKpiCount}
                        kpiStatuses={{
                            onboardingCoverage: operationalKpiById.get("onboardingCoverage")?.status ?? "ok",
                            goLiveReadiness: operationalKpiById.get("goLiveReadiness")?.status ?? "ok",
                            serviceStability: operationalKpiById.get("serviceStability")?.status ?? "ok",
                            decommissionShare: operationalKpiById.get("decommissionShare")?.status ?? "ok",
                            changeFailure: operationalKpiById.get("changeFailure")?.status ?? "ok",
                            rollbackShare: operationalKpiById.get("rollbackShare")?.status ?? "ok",
                            blockedSignals: operationalKpiById.get("blockedSignals")?.status ?? "ok",
                        }}
                        kpiDrilldown={operationalKpiDrilldown}
                        onRunKpiAction={runKpiAction}
                        onboardingThroughput={onboardingThroughput}
                        formatOptionalHours={formatOptionalHours}
                        formatOptionalPercent={formatOptionalPercent}
                        alertSeverity={alertHookPayload.severity}
                        alertBreachesCount={alertHookPayload.breaches.length}
                        onCopyAlertPayload={copyAlertHookPayload}
                        onRunMetricsSnapshot={runMetricsSnapshotHook}
                        runningMetricsSnapshotMode={runningMetricsSnapshotMode}
                        lastMetricsSnapshotJob={lastMetricsSnapshotJob}
                        pageFilterClientId={pageFilterClientId}
                        weeklySnapshotsFetching={weeklySnapshotsServerQuery.isFetching}
                        weeklySnapshots={weeklySnapshots}
                        formatDateTimeLabel={formatDateTimeLabel}
                    />
                ) : null}

                {controlTowerEnabled && showPortfolio && tenantLifecycle === "active" ? (
                    <TenantsFleetAttentionPanel
                        fleetAttention={fleetAttention}
                        loading={fleetAttentionLoading}
                        errored={fleetAttentionErrored}
                        refreshing={tenantsPortfolioQuery.isFetching || fleetAttentionQuery.isFetching}
                        onRefresh={() => {
                            tenantsPortfolioQuery.refetch();
                            fleetAttentionQuery.refetch();
                        }}
                        attentionLevelClass={attentionLevelClass}
                        formatLifecycleLabel={(value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS)}
                        formatServiceLabel={(value) => formatStateLabel(value, FLEET_SERVICE_LABELS)}
                        formatReferenceScopeReason={formatReferenceScopeReason}
                        onSetClientContext={setClientContextAndPageFilters}
                        onOpenIntegrations={(clientId, companyId) => openClientContextTarget("/integrations", clientId, companyId)}
                        onOpenCases={(clientId, companyId) => openClientContextTarget("/", clientId, companyId)}
                    />
                ) : null}

                {showPortfolio ? (
                    <TenantsPortfolioCompaniesPanel
                        companies={companies}
                        loading={companiesQuery.isLoading}
                        errored={companiesQuery.isError}
                        query={companyQuery}
                        onQueryChange={setCompanyQuery}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedCompanyId={selectedCompanyId}
                        companyEditor={companyEditor}
                        savingCompany={savingCompany}
                        hasNextPage={Boolean(companiesQuery.hasNextPage)}
                        isFetchingNextPage={companiesQuery.isFetchingNextPage}
                        onFetchNextPage={() => companiesQuery.fetchNextPage()}
                        onStartEdit={startCompanyEdit}
                        onSetContext={setCompanyContext}
                        onCancelEdit={() => setCompanyEditor(null)}
                        onSaveEdit={handleSaveCompany}
                        onChangeEditorName={(value) => {
                            setCompanyEditor((prev) => (prev ? { ...prev, name: value } : prev));
                        }}
                        onChangeEditorBillingInfo={(value) => {
                            setCompanyEditor((prev) => (prev ? { ...prev, billingInfo: value } : prev));
                        }}
                    />
                ) : null}

                {showDecommission ? (
                    <TenantsDecommissionPanel
                        tenantLifecycle={tenantLifecycle}
                        onTenantLifecycleChange={setTenantLifecycle}
                    />
                ) : null}

                {showClientsSection ? (
                    <TenantsClientsPanel
                        decommissionFocused={decommissionFocused}
                        clientsLoading={clientsLoading}
                        clientsErrored={clientsErrored}
                        clients={clients}
                        clientsSummary={clientsSummary}
                        pageFilterCompanyId={pageFilterCompanyId}
                        clientQuery={clientQuery}
                        onClientQueryChange={setClientQuery}
                        fleetLifecycleFilter={fleetLifecycleFilter}
                        onFleetLifecycleFilterChange={setFleetLifecycleFilter}
                        fleetPaymentFilter={fleetPaymentFilter}
                        onFleetPaymentFilterChange={setFleetPaymentFilter}
                        fleetServiceFilter={fleetServiceFilter}
                        onFleetServiceFilterChange={setFleetServiceFilter}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedClientId={selectedClientId}
                        pageFilterClientId={pageFilterClientId}
                        clientEditor={clientEditor}
                        savingClient={savingClient}
                        knownCompanies={knownCompanies}
                        clientLifecyclePendingId={clientLifecyclePendingId}
                        clientLifecycleAuditFilterById={clientLifecycleAuditFilterById}
                        clientLifecycleAuditById={clientLifecycleAuditById}
                        selectedClientApiAuditEntries={selectedClientApiAuditEntries}
                        selectedClientAuditIsFetching={selectedClientAuditQuery.isFetching}
                        onRefreshSelectedClientAudit={() => selectedClientAuditQuery.refetch()}
                        onSetClientLifecycleAuditFilter={(clientId, filter) => {
                            setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientId]: filter }));
                        }}
                        mergeLifecycleAuditEntries={mergeLifecycleAuditEntries}
                        formatLifecycleLabel={(value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS)}
                        formatPaymentLabel={(value) => formatStateLabel(value, FLEET_PAYMENT_LABELS)}
                        formatServiceLabel={(value) => formatStateLabel(value, FLEET_SERVICE_LABELS)}
                        formatReferenceScopeReason={formatReferenceScopeReason}
                        formatDateTimeLabel={formatDateTimeLabel}
                        isClientArchived={isClientArchived}
                        onStartClientEdit={startClientEdit}
                        onOpenClientLifecycleAction={openClientLifecycleAction}
                        onSetClientContext={setClientContextAndPageFilters}
                        onClientEditorSlugChange={(value) => {
                            setClientEditor((prev) => (prev ? { ...prev, slug: value } : prev));
                        }}
                        onClientEditorCompanyChange={(value) => {
                            setClientEditor((prev) => (prev ? { ...prev, companyId: value } : prev));
                        }}
                        onSaveClientEdit={handleSaveClient}
                        onCancelClientEdit={() => setClientEditor(null)}
                        clientsUsingServerContract={clientsUsingServerContract}
                        clientsHasNextPage={Boolean(clientsQuery.hasNextPage)}
                        clientsFetchingNextPage={clientsQuery.isFetchingNextPage}
                        onFetchNextClientsPage={() => clientsQuery.fetchNextPage()}
                    />
                ) : null}

                {showChangeManagement ? (
                    <TenantsBranchChangeManagementPanel
                        branchesLoading={branchesLoading}
                        branchesErrored={branchesErrored}
                        branches={branches}
                        pageFilterClientId={pageFilterClientId}
                        selectedClientName={selectedClientName}
                        branchQuery={branchQuery}
                        onBranchQueryChange={setBranchQuery}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedBranchId={selectedBranchId}
                        contextScope={effectiveWorkspaceMode}
                        onAuditSensitiveAccess={auditSensitiveAccess}
                        onStartBranchEdit={startBranchEdit}
                        onSetBranchContext={(branch) =>
                            setBranchContextAndPageFilters({
                                branchId: branch.id,
                                clientId: branch.id ? (branchClientIdById.get(branch.id) ?? null) : null,
                                companyId: branch.id ? (branchCompanyIdById.get(branch.id) ?? null) : null,
                            })
                        }
                        branchEditor={branchEditor}
                        onPatchBranchEditor={(patch) => {
                            setBranchEditor((prev) => (prev ? { ...prev, ...patch } : prev));
                        }}
                        requiresBranchConfirmation={requiresBranchConfirmation}
                        savingBranch={savingBranch}
                        publishingBranchChange={publishingBranchChange}
                        rollingBackBranchChange={rollingBackBranchChange}
                        onPreviewBranchChange={handlePreviewBranchChange}
                        onPublishBranchChange={handlePublishBranchChange}
                        onRollbackBranchChange={handleRollbackBranchChange}
                        onCancelBranchEdit={cancelBranchEdit}
                        branchChangePreview={branchChangePreview}
                        previewValidationErrors={previewValidationErrors}
                        previewDiffEntries={previewDiffEntries}
                        hasPublishedBranchChange={Boolean(latestPublishedBranchChange)}
                        branchChangesLoading={branchChangesQuery.isLoading}
                        branchChangesItems={branchChangesQuery.data?.items ?? []}
                        formatBranchChangeStatus={(value) => formatStateLabel(value, BRANCH_CHANGE_STATUS_LABELS)}
                        branchesHasNextPage={Boolean(branchesQuery.hasNextPage)}
                        branchesFetchingNextPage={branchesQuery.isFetchingNextPage}
                        onFetchNextBranchesPage={() => branchesQuery.fetchNextPage()}
                    />
                ) : null}
            </div>

            <TenantsClientLifecycleModal
                draft={clientLifecycleDraft}
                pending={Boolean(clientLifecyclePendingId)}
                onClose={closeClientLifecycleDraft}
                onSubmit={handleClientLifecycleAction}
                onPatchDraft={(patch) => {
                    setClientLifecycleDraft((prev) => (prev ? { ...prev, ...patch } : prev));
                }}
            />

            {showOnboarding ? (
                <div className="mt-10" data-testid="tenants-onboarding-section">
                    <div className="mb-3 rounded-lg border border-blue-300/60 bg-blue-50 p-3 text-xs text-blue-900">
                        Канонический execution-flow: выполняйте remediation и go-live в `Company Workspace`.
                        <button
                            className="btn-ghost ml-2"
                            onClick={() => router.push("/company-workspace")}
                            data-testid="tenants-open-workspace-from-onboarding"
                        >
                            Открыть Workspace
                        </button>
                    </div>
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
