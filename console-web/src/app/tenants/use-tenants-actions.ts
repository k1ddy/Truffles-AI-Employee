"use client";

import { type Dispatch, type SetStateAction, useCallback } from "react";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import { adminApi, confirmationsApi } from "@/lib/api-client";
import {
    readConsoleContextScopeFromStorage,
    setConsoleContextScope,
} from "@/lib/console-context-storage";
import type { OperationalKpiAction } from "./operational-kpi";

type ScopeValue = {
    companyId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
};

type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";
type TenantLifecycleMode = "active" | "archived" | "all";
type ActionQueueIntent =
    | "set_context"
    | "open_cases"
    | "open_integrations"
    | "workspace_portfolio"
    | "workspace_onboarding"
    | "workspace_changes"
    | "workspace_decommission"
    | "none";
type ActionQueueItemForIntent = {
    intent: ActionQueueIntent;
    clientId?: string | null;
    companyId?: string | null;
};
type ClientTargetPath = "/" | "/integrations" | "/ops";
type ClientLifecycleMode = "archive" | "restore";
type ClientLifecycleAuditSource = "session" | "api";

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

type ClientLifecycleAuditEntry = {
    clientId: string;
    mode: ClientLifecycleMode;
    previousLifecycleLabel: string;
    targetLifecycleLabel: string;
    reason: string;
    status: "success" | "error";
    message: string;
    traceId?: string;
    actorLabel: string;
    happenedAt: string;
    source: ClientLifecycleAuditSource;
    sourceEventId?: string;
};

type ClientLifecycleAuditMap = Record<string, ClientLifecycleAuditEntry[]>;

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
type BranchChangeRecord = components["schemas"]["ConsoleBranchChangeRecord"];
type PushLifecycleAuditEntry = (
    previous: ClientLifecycleAuditMap,
    entry: ClientLifecycleAuditEntry,
) => ClientLifecycleAuditMap;

type UseTenantsActionsParams = {
    clientCompanyIdById: Map<string, string>;
    branchClientIdById: Map<string, string>;
    branchCompanyIdById: Map<string, string>;
    pageFilterCompanyId: string | null;
    pageFilterClientId: string | null;
    applyScopeToPageFilters: (scope: ScopeValue) => void;
    refreshContext: () => void;
    reportValidationError: (message: string, code?: string, scope?: string) => void;
    setWorkspaceMode: (mode: TenantsWorkspaceMode) => void;
    setTenantLifecycle: (mode: TenantLifecycleMode) => void;
    navigateTo: (target: ClientTargetPath) => void;
    quickCreateForm: QuickCreateFormState;
    quickCreateCompanyId: string;
    quickCreateClientId: string;
    setQuickCreateForm: Dispatch<SetStateAction<QuickCreateFormState>>;
    setQuickCreateRunning: Dispatch<SetStateAction<QuickCreateRunning>>;
    branchEditor: BranchEditorState | null;
    branchChangePreview: components["schemas"]["ConsoleBranchChangeResponse"] | null;
    latestPublishedBranchChange: BranchChangeRecord | null;
    clientLifecycleDraft: ClientLifecycleDraftState | null;
    clientLifecyclePendingId: string | null;
    setBranchEditor: Dispatch<SetStateAction<BranchEditorState | null>>;
    setBranchChangePreview: Dispatch<SetStateAction<components["schemas"]["ConsoleBranchChangeResponse"] | null>>;
    setSavingBranch: Dispatch<SetStateAction<boolean>>;
    setPublishingBranchChange: Dispatch<SetStateAction<boolean>>;
    setRollingBackBranchChange: Dispatch<SetStateAction<boolean>>;
    setClientLifecycleDraft: Dispatch<SetStateAction<ClientLifecycleDraftState | null>>;
    setClientLifecyclePendingId: Dispatch<SetStateAction<string | null>>;
    setClientLifecycleAuditById: Dispatch<SetStateAction<ClientLifecycleAuditMap>>;
    companyEditor: CompanyEditorState | null;
    clientEditor: ClientEditorState | null;
    setCompanyEditor: Dispatch<SetStateAction<CompanyEditorState | null>>;
    setClientEditor: Dispatch<SetStateAction<ClientEditorState | null>>;
    setSavingCompany: Dispatch<SetStateAction<boolean>>;
    setSavingClient: Dispatch<SetStateAction<boolean>>;
    role: string;
    actorLabel: string;
    lifecycleArchivedLabel: string;
    lifecycleActiveLabel: string;
    formatLifecycleLabel: (value: string | null | undefined) => string;
    pushLifecycleAuditEntry: PushLifecycleAuditEntry;
    buildBranchChangePatch: (editor: BranchEditorState) => {
        patch: components["schemas"]["ConsoleBranchChangePatch"];
        hasChanges: boolean;
        error?: string;
    };
    applyBranchSnapshotToEditor: (
        editor: BranchEditorState,
        branch?: components["schemas"]["ConsoleBranch"] | null,
    ) => BranchEditorState;
    refetchBranchChanges: () => Promise<unknown>;
    refreshTenants: () => void;
    reportProvisioningError: (error: unknown, operation: string, endpoint: string) => void;
    slugInputPattern: RegExp;
    branchPhoneInputPattern: RegExp;
    isValidTimezoneName: (value: string) => boolean;
};

type QuickCreateRunning = "company" | "client" | "branch" | null;
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

function normalizeOptionalId(value: string | null | undefined): string | null {
    const normalized = value?.trim();
    return normalized ? normalized : null;
}

function parseOptionalJson(value: string, label: string): { value?: Record<string, unknown>; error?: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return { value: {} };
    }
    try {
        const parsed = JSON.parse(trimmed) as unknown;
        if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
            return { error: `${label} должен быть JSON-объектом` };
        }
        return { value: parsed as Record<string, unknown> };
    } catch {
        return { error: `${label} должен быть валидным JSON` };
    }
}

function stringifyOptionalJson(value: unknown): string {
    if (!value || typeof value !== "object") {
        return "";
    }
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) {
        return "";
    }
    return JSON.stringify(value, null, 2);
}

export function useTenantsActions({
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
    navigateTo,
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
    actorLabel,
    lifecycleArchivedLabel,
    lifecycleActiveLabel,
    formatLifecycleLabel,
    pushLifecycleAuditEntry,
    buildBranchChangePatch,
    applyBranchSnapshotToEditor,
    refetchBranchChanges,
    refreshTenants,
    reportProvisioningError,
    slugInputPattern,
    branchPhoneInputPattern,
    isValidTimezoneName,
}: UseTenantsActionsParams) {
    const completeContextScope = useCallback((scope: ScopeValue) => {
        const normalizedBranchId = normalizeOptionalId(scope.branchId);
        let normalizedClientId = normalizeOptionalId(scope.clientId);
        let normalizedCompanyId = normalizeOptionalId(scope.companyId);
        if (normalizedBranchId) {
            const branchClientId = branchClientIdById.get(normalizedBranchId);
            if (!normalizedClientId && branchClientId) {
                normalizedClientId = branchClientId;
            }
            if (!normalizedCompanyId) {
                const branchCompanyId = branchCompanyIdById.get(normalizedBranchId);
                if (branchCompanyId) {
                    normalizedCompanyId = branchCompanyId;
                }
            }
        }
        if (!normalizedCompanyId && normalizedClientId) {
            normalizedCompanyId = clientCompanyIdById.get(normalizedClientId) ?? null;
        }
        return {
            companyId: normalizedCompanyId,
            clientId: normalizedClientId,
            branchId: normalizedBranchId,
        };
    }, [branchClientIdById, branchCompanyIdById, clientCompanyIdById]);

    const validateScopeForBranchActions = useCallback((
        scope: ScopeValue,
        actionLabel: string,
    ) => {
        const normalized = completeContextScope(scope);
        if (normalized.branchId && (!normalized.clientId || !normalized.companyId)) {
            reportValidationError(
                `Нельзя выполнить "${actionLabel}": для филиала требуется связка company + client.`,
                "TENANTS_SCOPE_INVALID",
                "filters",
            );
            return null;
        }
        return normalized;
    }, [completeContextScope, reportValidationError]);

    const writeContextScope = useCallback((scope: ScopeValue) => {
        const normalized = completeContextScope(scope);
        setConsoleContextScope({
            companyId: normalized.companyId ?? "",
            clientId: normalized.clientId ?? "",
            branchId: normalized.branchId ?? "",
        });
        refreshContext();
        return normalized;
    }, [completeContextScope, refreshContext]);

    const setCompanyContext = useCallback((companyId?: string | null) => {
        writeContextScope({
            companyId,
            clientId: null,
            branchId: null,
        });
    }, [writeContextScope]);

    const setClientContext = useCallback((clientId?: string | null, companyId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: companyId ?? storedScope.companyId,
            clientId,
            branchId: null,
        });
    }, [writeContextScope]);

    const setBranchContext = useCallback((branchId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: storedScope.companyId,
            clientId: storedScope.clientId,
            branchId,
        });
    }, [writeContextScope]);

    const clearContextLens = useCallback(() => {
        setCompanyContext(null);
    }, [setCompanyContext]);

    const setClientContextAndPageFilters = useCallback((clientId?: string | null, companyId?: string | null) => {
        const nextScope = writeContextScope({
            companyId,
            clientId,
            branchId: null,
        });
        applyScopeToPageFilters(nextScope);
    }, [applyScopeToPageFilters, writeContextScope]);

    const setBranchContextAndPageFilters = useCallback((
        input?: string | ScopeValue | null,
    ) => {
        const branchPatch = typeof input === "string" || input == null ? { branchId: input ?? null } : input;
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScopeCandidate = validateScopeForBranchActions(
            {
                companyId: branchPatch.companyId ?? pageFilterCompanyId ?? storedScope.companyId,
                clientId: branchPatch.clientId ?? pageFilterClientId ?? storedScope.clientId,
                branchId: branchPatch.branchId ?? null,
            },
            "В контекст филиала",
        );
        if (!nextScopeCandidate) {
            return;
        }
        const nextScope = writeContextScope({
            companyId: nextScopeCandidate.companyId,
            clientId: nextScopeCandidate.clientId,
            branchId: nextScopeCandidate.branchId,
        });
        applyScopeToPageFilters(nextScope);
    }, [
        applyScopeToPageFilters,
        pageFilterCompanyId,
        pageFilterClientId,
        validateScopeForBranchActions,
        writeContextScope,
    ]);

    const applyContextToPageFilters = useCallback(() => {
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScope = validateScopeForBranchActions(storedScope, "Взять из рабочего контура");
        if (!nextScope) {
            return;
        }
        applyScopeToPageFilters(nextScope);
        if (
            (nextScope.companyId ?? "") !== storedScope.companyId
            || (nextScope.clientId ?? "") !== storedScope.clientId
            || (nextScope.branchId ?? "") !== storedScope.branchId
        ) {
            setConsoleContextScope({
                companyId: nextScope.companyId ?? "",
                clientId: nextScope.clientId ?? "",
                branchId: nextScope.branchId ?? "",
            });
            refreshContext();
        }
    }, [applyScopeToPageFilters, refreshContext, validateScopeForBranchActions]);

    const openClientContextTarget = useCallback((target: ClientTargetPath, clientId?: string | null, companyId?: string | null) => {
        if (!clientId) {
            return;
        }
        setClientContextAndPageFilters(clientId, companyId);
        navigateTo(target);
    }, [navigateTo, setClientContextAndPageFilters]);

    const runActionQueueIntent = useCallback((item: ActionQueueItemForIntent) => {
        if (item.intent === "set_context") {
            setClientContextAndPageFilters(item.clientId, item.companyId);
            return;
        }
        if (item.intent === "open_cases") {
            openClientContextTarget("/", item.clientId, item.companyId);
            return;
        }
        if (item.intent === "open_integrations") {
            openClientContextTarget("/integrations", item.clientId, item.companyId);
            return;
        }
        if (item.intent === "workspace_portfolio") {
            setWorkspaceMode("portfolio");
            return;
        }
        if (item.intent === "workspace_onboarding") {
            setWorkspaceMode("onboarding");
            return;
        }
        if (item.intent === "workspace_changes") {
            setWorkspaceMode("changes");
            return;
        }
        if (item.intent === "workspace_decommission") {
            setWorkspaceMode("decommission");
        }
    }, [openClientContextTarget, setClientContextAndPageFilters, setWorkspaceMode]);

    const runKpiAction = useCallback((action: OperationalKpiAction) => {
        if (action === "onboarding") {
            setWorkspaceMode("onboarding");
            setTenantLifecycle("active");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-onboarding-section"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        if (action === "changes") {
            setWorkspaceMode("changes");
            setTenantLifecycle("active");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-change-management"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        if (action === "decommission") {
            setWorkspaceMode("decommission");
            setTenantLifecycle("all");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-decommission-center"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        setWorkspaceMode("portfolio");
        setTenantLifecycle("active");
        setTimeout(() => {
            document.querySelector('[data-testid="tenants-fleet-attention"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
    }, [setTenantLifecycle, setWorkspaceMode]);

    const startCompanyEdit = useCallback((company: components["schemas"]["ConsoleCompany"]) => {
        if (!company.id) {
            reportValidationError("Не удалось открыть компанию без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setClientEditor(null);
        setBranchEditor(null);
        const billingInfo = stringifyOptionalJson(company.billing_info);
        setCompanyEditor({
            id: company.id,
            name: company.name ?? "",
            billingInfo,
            originalName: company.name ?? "",
            originalBillingInfo: billingInfo,
        });
    }, [
        reportValidationError,
        setBranchChangePreview,
        setBranchEditor,
        setClientEditor,
        setClientLifecycleDraft,
        setCompanyEditor,
    ]);

    const startClientEdit = useCallback((client: components["schemas"]["ConsoleClient"]) => {
        if (!client.id) {
            reportValidationError("Не удалось открыть клиента без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setCompanyEditor(null);
        setBranchEditor(null);
        setClientEditor({
            id: client.id,
            slug: client.slug ?? client.name ?? "",
            companyId: client.company_id ?? "",
            originalSlug: client.slug ?? client.name ?? "",
            originalCompanyId: client.company_id ?? "",
            totalBranches: client.total_branches ?? 0,
        });
    }, [
        reportValidationError,
        setBranchChangePreview,
        setBranchEditor,
        setClientEditor,
        setClientLifecycleDraft,
        setCompanyEditor,
    ]);

    const startBranchEdit = useCallback((branch: components["schemas"]["ConsoleBranch"]) => {
        if (!branch.id) {
            reportValidationError("Не удалось открыть филиал без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setCompanyEditor(null);
        setClientEditor(null);
        setBranchEditor({
            id: branch.id,
            name: branch.name ?? "",
            slug: branch.slug ?? "",
            timezone: branch.timezone ?? "",
            phone: branch.phone ?? "",
            instanceId: branch.instance_id ?? "",
            telegramChatId: branch.telegram_chat_id ?? "",
            knowledgeTag: branch.knowledge_tag ?? "",
            isActive: branch.is_active ?? false,
            changeReason: "",
            confirmReason: "",
            rollbackReason: "",
            original: {
                name: branch.name ?? "",
                slug: branch.slug ?? "",
                timezone: branch.timezone ?? "",
                phone: branch.phone ?? "",
                instanceId: branch.instance_id ?? "",
                telegramChatId: branch.telegram_chat_id ?? "",
                knowledgeTag: branch.knowledge_tag ?? "",
                isActive: branch.is_active ?? false,
            },
        });
    }, [
        reportValidationError,
        setBranchChangePreview,
        setBranchEditor,
        setClientEditor,
        setClientLifecycleDraft,
        setCompanyEditor,
    ]);

    const openClientLifecycleAction = useCallback((
        client: components["schemas"]["ConsoleClient"],
        mode: ClientLifecycleMode,
    ) => {
        if (!client.id) {
            reportValidationError("Не удалось выполнить действие без ID клиента");
            return;
        }
        setClientLifecycleDraft({
            clientId: client.id,
            clientLabel: client.name ?? client.slug ?? client.id,
            companyLabel: client.company_name ?? "—",
            mode,
            currentLifecycleLabel: formatLifecycleLabel(client.lifecycle_state),
            targetLifecycleLabel: mode === "archive" ? lifecycleArchivedLabel : lifecycleActiveLabel,
            activeBranches: client.active_branches ?? 0,
            totalBranches: client.total_branches ?? 0,
            degradedBranches: client.degraded_branches ?? 0,
            reason: "",
            confirmChecked: false,
            checkClientScope: false,
            checkImpactReview: false,
            checkOwnerAligned: false,
        });
    }, [
        formatLifecycleLabel,
        lifecycleActiveLabel,
        lifecycleArchivedLabel,
        reportValidationError,
        setClientLifecycleDraft,
    ]);

    const closeClientLifecycleDraft = useCallback(() => {
        if (clientLifecyclePendingId) {
            return;
        }
        setClientLifecycleDraft(null);
    }, [clientLifecyclePendingId, setClientLifecycleDraft]);

    const handleClientLifecycleAction = useCallback(async () => {
        if (!clientLifecycleDraft) {
            reportValidationError("Сначала подготовьте действие");
            return;
        }
        const lifecycleDraft = clientLifecycleDraft;
        const clientId = lifecycleDraft.clientId;
        if (!clientId) {
            reportValidationError("Не удалось выполнить действие без ID клиента");
            return;
        }
        const reason = clientLifecycleDraft.reason.trim();
        if (!reason) {
            reportValidationError("Укажите причину");
            return;
        }
        if (!clientLifecycleDraft.confirmChecked) {
            reportValidationError("Подтвердите действие");
            return;
        }
        if (
            !clientLifecycleDraft.checkClientScope
            || !clientLifecycleDraft.checkImpactReview
            || !clientLifecycleDraft.checkOwnerAligned
        ) {
            reportValidationError("Заполните checklist перед выполнением действия");
            return;
        }

        const mode = lifecycleDraft.mode;
        const effectiveActorLabel = actorLabel || role;
        setClientLifecyclePendingId(clientId);
        let lifecycleCompleted = false;
        try {
            if (mode === "archive") {
                await adminApi.archiveClient(clientId, { reason });
                toast.success("Клиент архивирован");
            } else {
                await adminApi.restoreClient(clientId, { reason });
                toast.success("Клиент восстановлен");
            }
            lifecycleCompleted = true;
            setClientLifecycleAuditById((prev) => pushLifecycleAuditEntry(prev, {
                clientId,
                mode,
                previousLifecycleLabel: lifecycleDraft.currentLifecycleLabel,
                targetLifecycleLabel: lifecycleDraft.targetLifecycleLabel,
                reason,
                status: "success",
                message: mode === "archive" ? "Архивация подтверждена API" : "Восстановление подтверждено API",
                actorLabel: effectiveActorLabel,
                happenedAt: new Date().toISOString(),
                source: "session",
            }));
            if (clientEditor?.id === clientId) {
                setClientEditor(null);
            }
            refreshTenants();
            refreshContext();
        } catch (error) {
            const parsed = reportProvisioningError(
                error,
                mode === "archive" ? "архивация клиента" : "восстановление клиента",
                mode === "archive"
                    ? "POST /api/proxy/admin/clients/:id/archive"
                    : "POST /api/proxy/admin/clients/:id/restore",
            ) as
                | { message?: string; trace_id?: string }
                | undefined;
            setClientLifecycleAuditById((prev) => pushLifecycleAuditEntry(prev, {
                clientId,
                mode,
                previousLifecycleLabel: lifecycleDraft.currentLifecycleLabel,
                targetLifecycleLabel: lifecycleDraft.targetLifecycleLabel,
                reason,
                status: "error",
                message: parsed?.message ?? "Ошибка выполнения lifecycle-действия",
                traceId: parsed?.trace_id,
                actorLabel: effectiveActorLabel,
                happenedAt: new Date().toISOString(),
                source: "session",
            }));
        } finally {
            setClientLifecyclePendingId(null);
            if (lifecycleCompleted) {
                setClientLifecycleDraft(null);
            }
        }
    }, [
        actorLabel,
        clientEditor?.id,
        clientLifecycleDraft,
        pushLifecycleAuditEntry,
        refreshContext,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        role,
        setClientEditor,
        setClientLifecycleAuditById,
        setClientLifecycleDraft,
        setClientLifecyclePendingId,
    ]);

    const requiresBranchConfirmation = useCallback((editor: BranchEditorState) => {
        const removedInstance = editor.original.instanceId && !editor.instanceId.trim();
        const deactivated = editor.original.isActive && !editor.isActive;
        return removedInstance || deactivated;
    }, []);

    const createBranchDeactivateConfirmation = useCallback(async (branchId: string, reason: string) => {
        const confirmation = await confirmationsApi.create({
            action: "branch_deactivate",
            target_type: "branch",
            target_id: branchId,
            reason,
        });
        return confirmation.data.confirmation_id;
    }, []);

    const handlePreviewBranchChange = useCallback(async () => {
        if (!branchEditor) {
            return;
        }
        const reason = branchEditor.changeReason.trim();
        if (!reason) {
            reportValidationError("Укажите причину изменения");
            return;
        }
        const { patch, hasChanges, error } = buildBranchChangePatch(branchEditor);
        if (error) {
            reportValidationError(error);
            return;
        }
        if (!hasChanges) {
            toast("Нет изменений");
            return;
        }
        setSavingBranch(true);
        try {
            const draftResponse = await adminApi.draftBranchChange({
                branch_id: branchEditor.id,
                reason,
                patch,
            });
            const draftChangeId = draftResponse.data.change?.id;
            if (!draftChangeId) {
                reportValidationError("Не удалось создать черновик");
                return;
            }
            const validateResponse = await adminApi.validateBranchChange(draftChangeId);
            setBranchChangePreview(validateResponse.data);
            const status = validateResponse.data.change?.status;
            if (status === "validated") {
                toast.success("Черновик прошел проверку. Можно применять.");
            } else {
                reportValidationError("Черновик не прошел проверку. Исправьте ошибки.");
            }
            await refetchBranchChanges();
        } catch (error) {
            reportProvisioningError(
                error,
                "черновик и валидация изменения филиала",
                "POST /api/proxy/admin/branch-changes + /validate",
            );
        } finally {
            setSavingBranch(false);
        }
    }, [
        branchEditor,
        buildBranchChangePatch,
        refetchBranchChanges,
        reportProvisioningError,
        reportValidationError,
        setBranchChangePreview,
        setSavingBranch,
    ]);

    const handlePublishBranchChange = useCallback(async () => {
        if (!branchEditor) {
            return;
        }
        const changeId = branchChangePreview?.change?.id;
        if (!changeId) {
            reportValidationError("Сначала подготовьте и проверьте черновик");
            return;
        }
        setPublishingBranchChange(true);
        try {
            let confirmationId: string | undefined;
            if (requiresBranchConfirmation(branchEditor)) {
                const confirmationReason = branchEditor.confirmReason.trim() || branchEditor.changeReason.trim();
                if (!confirmationReason) {
                    reportValidationError("Укажите причину подтверждения");
                    return;
                }
                confirmationId = await createBranchDeactivateConfirmation(branchEditor.id, confirmationReason);
            }
            const publishResponse = await adminApi.publishBranchChange(changeId, {
                confirmation_id: confirmationId,
            });
            setBranchChangePreview(publishResponse.data);
            setBranchEditor((prev) => (prev ? applyBranchSnapshotToEditor(prev, publishResponse.data.branch) : prev));
            toast.success("Изменение опубликовано");
            await refetchBranchChanges();
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "публикация изменения филиала", "POST /api/proxy/admin/branch-changes/:id/publish");
        } finally {
            setPublishingBranchChange(false);
        }
    }, [
        applyBranchSnapshotToEditor,
        branchChangePreview?.change?.id,
        branchEditor,
        createBranchDeactivateConfirmation,
        refetchBranchChanges,
        refreshContext,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        requiresBranchConfirmation,
        setBranchChangePreview,
        setBranchEditor,
        setPublishingBranchChange,
    ]);

    const handleRollbackBranchChange = useCallback(async () => {
        if (!branchEditor) {
            return;
        }
        const targetChange = branchChangePreview?.change?.status === "published"
            ? branchChangePreview.change
            : latestPublishedBranchChange;
        const changeId = targetChange?.id;
        if (!changeId) {
            reportValidationError("Нет примененного изменения для отката");
            return;
        }
        const reason = branchEditor.rollbackReason.trim();
        if (!reason) {
            reportValidationError("Укажите причину отката");
            return;
        }

        setRollingBackBranchChange(true);
        try {
            const runRollback = async (confirmationId?: string) =>
                adminApi.rollbackBranchChange(changeId, {
                    reason,
                    confirmation_id: confirmationId,
                });

            let rollbackResponse;
            try {
                rollbackResponse = await runRollback();
            } catch (error: unknown) {
                const apiCode = (error as { response?: { data?: { error?: { code?: string } } } })
                    ?.response?.data?.error?.code;
                if (apiCode !== "CONFIRMATION_REQUIRED") {
                    throw error;
                }
                const confirmationReason = branchEditor.confirmReason.trim() || reason;
                const confirmationId = await createBranchDeactivateConfirmation(branchEditor.id, confirmationReason);
                rollbackResponse = await runRollback(confirmationId);
            }

            setBranchChangePreview(rollbackResponse.data);
            setBranchEditor((prev) => (prev ? applyBranchSnapshotToEditor(prev, rollbackResponse.data.branch) : prev));
            toast.success("Откат выполнен");
            await refetchBranchChanges();
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "откат изменения филиала", "POST /api/proxy/admin/branch-changes/:id/rollback");
        } finally {
            setRollingBackBranchChange(false);
        }
    }, [
        applyBranchSnapshotToEditor,
        branchChangePreview,
        branchEditor,
        createBranchDeactivateConfirmation,
        latestPublishedBranchChange,
        refetchBranchChanges,
        refreshContext,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setBranchChangePreview,
        setBranchEditor,
        setRollingBackBranchChange,
    ]);

    const cancelBranchEdit = useCallback(() => {
        setBranchEditor(null);
        setBranchChangePreview(null);
    }, [setBranchChangePreview, setBranchEditor]);

    const handleSaveCompany = useCallback(async () => {
        if (!companyEditor) {
            return;
        }
        const name = companyEditor.name.trim();
        if (!name) {
            reportValidationError("Укажите название компании");
            return;
        }
        const billing = parseOptionalJson(companyEditor.billingInfo, "billing_info");
        if (billing.error) {
            reportValidationError(billing.error);
            return;
        }
        const payload: components["schemas"]["ConsoleCompanyUpdateRequest"] = {};
        if (name !== companyEditor.originalName) {
            payload.name = name;
        }
        if (companyEditor.billingInfo.trim() !== companyEditor.originalBillingInfo.trim()) {
            payload.billing_info = (billing.value ?? {}) as Record<string, never>;
        }
        if (Object.keys(payload).length === 0) {
            toast("Нет изменений");
            return;
        }
        setSavingCompany(true);
        try {
            await adminApi.patchCompany(companyEditor.id, payload);
            toast.success("Компания обновлена");
            setCompanyEditor(null);
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "обновление компании", "PATCH /api/proxy/admin/companies/:id");
        } finally {
            setSavingCompany(false);
        }
    }, [
        companyEditor,
        refreshContext,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setCompanyEditor,
        setSavingCompany,
    ]);

    const handleSaveClient = useCallback(async () => {
        if (!clientEditor) {
            return;
        }
        const slug = clientEditor.slug.trim();
        if (!slug) {
            reportValidationError("Укажите slug клиента");
            return;
        }
        if (!slugInputPattern.test(slug)) {
            reportValidationError("slug: [a-z0-9_-], без пробелов");
            return;
        }
        const payload: components["schemas"]["ConsoleClientUpdateRequest"] = {};
        if (slug !== clientEditor.originalSlug) {
            payload.slug = slug;
        }
        const companyId = clientEditor.companyId.trim();
        const companyLocked = clientEditor.totalBranches > 0 && !!clientEditor.originalCompanyId;
        if (companyLocked && companyId !== clientEditor.originalCompanyId) {
            reportValidationError("company_id нельзя менять после создания филиалов");
            return;
        }
        if (companyId !== clientEditor.originalCompanyId) {
            payload.company_id = companyId || null;
        }
        if (Object.keys(payload).length === 0) {
            toast("Нет изменений");
            return;
        }
        setSavingClient(true);
        try {
            await adminApi.patchClient(clientEditor.id, payload);
            toast.success("Клиент обновлён");
            setClientEditor(null);
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "обновление клиента", "PATCH /api/proxy/admin/clients/:id");
        } finally {
            setSavingClient(false);
        }
    }, [
        clientEditor,
        refreshContext,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setClientEditor,
        setSavingClient,
        slugInputPattern,
    ]);

    const handleQuickCreateCompany = useCallback(async () => {
        const companyName = quickCreateForm.companyName.trim();
        if (!companyName) {
            reportValidationError("Укажите название компании");
            return;
        }
        setQuickCreateRunning("company");
        try {
            const response = await adminApi.createCompany({ name: companyName });
            const companyId = response.data.company?.id;
            if (!companyId) {
                reportValidationError("Компания создана, но company_id не вернулся");
                return;
            }
            setQuickCreateForm((prev) => ({
                ...prev,
                companyId,
                companyName,
            }));
            setCompanyContext(companyId);
            refreshTenants();
            toast.success("Компания создана");
        } catch (error) {
            reportProvisioningError(error, "создание компании", "POST /api/proxy/admin/companies");
        } finally {
            setQuickCreateRunning(null);
        }
    }, [
        quickCreateForm.companyName,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setCompanyContext,
        setQuickCreateForm,
        setQuickCreateRunning,
    ]);

    const handleQuickCreateClient = useCallback(async () => {
        const slug = quickCreateForm.clientSlug.trim().toLowerCase();
        const companyId = quickCreateCompanyId;
        if (!companyId) {
            reportValidationError("Сначала выберите или создайте компанию");
            return;
        }
        if (!slug) {
            reportValidationError("Укажите slug клиента");
            return;
        }
        if (!slugInputPattern.test(slug)) {
            reportValidationError("slug: [a-z0-9_-], без пробелов");
            return;
        }
        setQuickCreateRunning("client");
        try {
            const response = await adminApi.createClient({
                slug,
                company_id: companyId,
                status: null,
            });
            const clientId = response.data.client?.id;
            if (!clientId) {
                reportValidationError("Клиент создан, но client_id не вернулся");
                return;
            }
            setQuickCreateForm((prev) => ({
                ...prev,
                clientSlug: slug,
                companyId,
                clientId,
            }));
            setClientContextAndPageFilters(clientId, companyId);
            refreshTenants();
            toast.success("Клиент создан");
        } catch (error) {
            reportProvisioningError(error, "создание клиента", "POST /api/proxy/admin/clients");
        } finally {
            setQuickCreateRunning(null);
        }
    }, [
        quickCreateCompanyId,
        quickCreateForm.clientSlug,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setClientContextAndPageFilters,
        setQuickCreateForm,
        setQuickCreateRunning,
        slugInputPattern,
    ]);

    const handleQuickCreateBranch = useCallback(async () => {
        const clientId = quickCreateClientId;
        const branchName = quickCreateForm.branchName.trim();
        const branchSlug = quickCreateForm.branchSlug.trim().toLowerCase();
        const timezone = quickCreateForm.branchTimezone.trim();
        const phone = quickCreateForm.branchPhone.trim();
        const instanceId = quickCreateForm.branchInstanceId.trim();
        if (!clientId) {
            reportValidationError("Сначала выберите или создайте клиента");
            return;
        }
        if (!branchName || !branchSlug) {
            reportValidationError("Укажите название и slug филиала");
            return;
        }
        if (!slugInputPattern.test(branchSlug)) {
            reportValidationError("branch slug: [a-z0-9_-], без пробелов");
            return;
        }
        if (timezone && !isValidTimezoneName(timezone)) {
            reportValidationError("timezone должен быть в формате IANA, например Asia/Almaty");
            return;
        }
        if (phone && !branchPhoneInputPattern.test(phone)) {
            reportValidationError("phone: 7-15 цифр (допускаются +, пробелы, скобки и -)");
            return;
        }
        if (instanceId && !phone) {
            reportValidationError("Для instance_id укажите phone филиала");
            return;
        }
        setQuickCreateRunning("branch");
        try {
            const response = await adminApi.createBranch({
                client_id: clientId,
                name: branchName,
                slug: branchSlug,
                timezone: timezone || undefined,
                phone: phone || undefined,
                instance_id: instanceId || undefined,
                is_active: Boolean(phone && instanceId),
                bootstrap_accounts: [],
            });
            const branchId = response.data.branch?.id;
            if (!branchId) {
                reportValidationError("Филиал создан, но branch_id не вернулся");
                return;
            }
            setBranchContextAndPageFilters({
                branchId,
                clientId,
                companyId: quickCreateCompanyId,
            });
            refreshTenants();
            toast.success("Филиал создан и выбран в контексте");
        } catch (error) {
            reportProvisioningError(error, "создание филиала", "POST /api/proxy/admin/branches");
        } finally {
            setQuickCreateRunning(null);
        }
    }, [
        branchPhoneInputPattern,
        isValidTimezoneName,
        quickCreateClientId,
        quickCreateCompanyId,
        quickCreateForm.branchInstanceId,
        quickCreateForm.branchName,
        quickCreateForm.branchPhone,
        quickCreateForm.branchSlug,
        quickCreateForm.branchTimezone,
        refreshTenants,
        reportProvisioningError,
        reportValidationError,
        setBranchContextAndPageFilters,
        setQuickCreateRunning,
        slugInputPattern,
    ]);

    return {
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
    };
}
