"use client";

import { type Dispatch, type SetStateAction, useCallback } from "react";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import { adminApi } from "@/lib/api-client";
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
    companyEditor: CompanyEditorState | null;
    clientEditor: ClientEditorState | null;
    setCompanyEditor: Dispatch<SetStateAction<CompanyEditorState | null>>;
    setClientEditor: Dispatch<SetStateAction<ClientEditorState | null>>;
    setSavingCompany: Dispatch<SetStateAction<boolean>>;
    setSavingClient: Dispatch<SetStateAction<boolean>>;
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
    companyEditor,
    clientEditor,
    setCompanyEditor,
    setClientEditor,
    setSavingCompany,
    setSavingClient,
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
        handleSaveCompany,
        handleSaveClient,
        handleQuickCreateCompany,
        handleQuickCreateClient,
        handleQuickCreateBranch,
    };
}
