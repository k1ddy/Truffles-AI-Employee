"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    adminApi,
    authApi,
    canAccessConsole,
    confirmationsApi,
    onboardingApi,
    type IntegrationBranchActionRequest,
    type ProviderOpsAction,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

type ProviderActionDialogState = {
    action: ProviderOpsAction;
    mode: "dry_run" | "execute";
    reason: string;
    notes: string;
    paidUntil: string;
    nextRenewalAt: string;
    instanceId: string;
};

type WizardStep = {
    id: string;
    title: string;
    passed: boolean;
    detail: string;
    fix: string;
};

function readLocalStorageValue(key: string): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    return window.localStorage.getItem(key);
}

function setLocalStorageValue(key: string, value?: string | null) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}

function formatDateLabel(value?: string | null): string {
    if (!value) {
        return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("ru-RU");
}

function statusPill(status: "ok" | "warn" | "error"): string {
    if (status === "error") {
        return "bg-red-100 text-red-700";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-green-100 text-green-700";
}

function providerOpsActionLabel(action: ProviderOpsAction): string {
    if (action === "provider_start_rebind") {
        return "Start rebind";
    }
    if (action === "provider_complete_rebind") {
        return "Complete rebind";
    }
    if (action === "provider_renewal_confirmed") {
        return "Confirm renewal";
    }
    if (action === "provider_webhook_updated") {
        return "Webhook updated";
    }
    if (action === "provider_send_reminder") {
        return "Send reminder";
    }
    return "Reconcile";
}

function defaultExecuteReason(action: ProviderOpsAction): string {
    if (action === "provider_send_reminder") {
        return "provider lifecycle reminder from workspace";
    }
    if (action === "provider_renewal_confirmed") {
        return "provider renewal confirmed in workspace";
    }
    if (action === "provider_webhook_updated") {
        return "provider webhook updated in workspace";
    }
    if (action === "provider_complete_rebind") {
        return "provider rebind completed in workspace";
    }
    if (action === "provider_start_rebind") {
        return "provider rebind started in workspace";
    }
    return "workspace integration reconcile";
}

export default function CompanyWorkspacePage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();

    const [scopeCompanyId, setScopeCompanyId] = useState("");
    const [scopeClientId, setScopeClientId] = useState("");
    const [scopeBranchId, setScopeBranchId] = useState("");
    const [scopeInitialized, setScopeInitialized] = useState(false);

    const [staleAfterMinutes] = useState(60);

    const [branchPhone, setBranchPhone] = useState("");
    const [branchInstanceId, setBranchInstanceId] = useState("");
    const [goLiveReason, setGoLiveReason] = useState("go-live approved from company workspace");

    const [webhookSecret, setWebhookSecret] = useState("");
    const [webhookUrl, setWebhookUrl] = useState("");

    const [runningAction, setRunningAction] = useState<{
        branchId: string;
        mode: "dry_run" | "execute";
        action: ProviderOpsAction;
    } | null>(null);
    const [actionSummary, setActionSummary] = useState<string>("");
    const [providerActionDialog, setProviderActionDialog] = useState<ProviderActionDialogState | null>(null);
    const [branchSaving, setBranchSaving] = useState(false);
    const [goLiveSaving, setGoLiveSaving] = useState<"approve" | "reject" | "waive" | null>(null);

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadTenants = canAccessConsole(role, "tenants", "read");
    const canWriteTenants = canAccessConsole(role, "tenants", "write");
    const canReadIntegrations = canAccessConsole(role, "integrations", "read");

    useEffect(() => {
        if (!meData || scopeInitialized) {
            return;
        }
        const storedCompanyId = readLocalStorageValue(COMPANY_ID_STORAGE_KEY);
        const storedClientId = readLocalStorageValue(CLIENT_ID_STORAGE_KEY);
        const storedBranchId = readLocalStorageValue(BRANCH_ID_STORAGE_KEY);
        setScopeCompanyId(meData.selected_company_id ?? meData.client?.company_id ?? storedCompanyId ?? "");
        setScopeClientId(meData.client?.id ?? storedClientId ?? "");
        setScopeBranchId(meData.selected_branch_id ?? storedBranchId ?? "");
        setScopeInitialized(true);
    }, [meData, scopeInitialized]);

    const syncScopeFromContext = () => {
        const storedCompanyId = readLocalStorageValue(COMPANY_ID_STORAGE_KEY);
        const storedClientId = readLocalStorageValue(CLIENT_ID_STORAGE_KEY);
        const storedBranchId = readLocalStorageValue(BRANCH_ID_STORAGE_KEY);
        setScopeCompanyId(meData?.selected_company_id ?? meData?.client?.company_id ?? storedCompanyId ?? "");
        setScopeClientId(meData?.client?.id ?? storedClientId ?? "");
        setScopeBranchId(meData?.selected_branch_id ?? storedBranchId ?? "");
    };

    const persistScopeAsContext = () => {
        setLocalStorageValue(COMPANY_ID_STORAGE_KEY, scopeCompanyId || null);
        setLocalStorageValue(CLIENT_ID_STORAGE_KEY, scopeClientId || null);
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, scopeBranchId || null);
        toast.success("Console context updated");
    };

    const { data: clientsData } = useQuery({
        queryKey: ["company-workspace-clients", scopeCompanyId],
        queryFn: async () => {
            const response = await adminApi.listClients({
                limit: 100,
                lifecycle: "active",
                company_id: scopeCompanyId || undefined,
                include_fleet: "true",
            });
            return response.data;
        },
        enabled: !!session && canReadTenants,
    });
    const clientOptions = useMemo(() => clientsData?.items ?? [], [clientsData?.items]);

    const { data: branchesData } = useQuery({
        queryKey: ["company-workspace-branches", scopeClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                limit: 100,
                lifecycle: "active",
                client_id: scopeClientId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadTenants && !!scopeClientId,
    });
    const branchOptions = useMemo(() => branchesData?.items ?? [], [branchesData?.items]);

    const {
        data: integrationsData,
        isLoading: integrationsLoading,
        error: integrationsError,
        refetch: refetchIntegrations,
    } = useQuery({
        queryKey: ["company-workspace-integrations", staleAfterMinutes, scopeCompanyId, scopeClientId, scopeBranchId],
        queryFn: async () => {
            const response = await adminApi.listIntegrations({
                stale_after_minutes: staleAfterMinutes,
                company_id: scopeCompanyId || undefined,
                client_id: scopeClientId || undefined,
                branch_id: scopeBranchId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
        refetchInterval: 60000,
    });

    const {
        data: onboardingScorecard,
        error: scorecardError,
        refetch: refetchScorecard,
    } = useQuery({
        queryKey: ["company-workspace-scorecard", scopeBranchId],
        queryFn: async () => {
            const response = await onboardingApi.scorecard(scopeBranchId);
            return response.data;
        },
        enabled: !!session && !!scopeBranchId && canReadTenants,
    });

    useEffect(() => {
        if (integrationsError) {
            handleError(integrationsError);
        }
    }, [integrationsError, handleError]);

    useEffect(() => {
        if (scorecardError) {
            handleError(scorecardError);
        }
    }, [scorecardError, handleError]);

    useEffect(() => {
        if (!scopeClientId) {
            return;
        }
        if (clientOptions.some((client) => client.id === scopeClientId)) {
            return;
        }
        setScopeClientId("");
        setScopeBranchId("");
    }, [clientOptions, scopeClientId]);

    useEffect(() => {
        if (!scopeBranchId) {
            return;
        }
        if (branchOptions.some((branch) => branch.id === scopeBranchId)) {
            return;
        }
        setScopeBranchId("");
    }, [branchOptions, scopeBranchId]);

    const selectedBranch = useMemo(
        () => branchOptions.find((branch) => branch.id === scopeBranchId) ?? null,
        [branchOptions, scopeBranchId],
    );

    const selectedIntegration = useMemo(() => {
        const items = integrationsData?.items ?? [];
        if (!scopeBranchId) {
            return items[0] ?? null;
        }
        return items.find((item) => item.branch_id === scopeBranchId) ?? null;
    }, [integrationsData?.items, scopeBranchId]);

    useEffect(() => {
        setBranchPhone(selectedBranch?.phone ?? "");
        setBranchInstanceId(selectedBranch?.instance_id ?? "");
    }, [selectedBranch?.id, selectedBranch?.phone, selectedBranch?.instance_id]);

    useEffect(() => {
        setWebhookSecret("");
        setWebhookUrl(selectedIntegration?.webhook_url ?? "");
        setActionSummary("");
    }, [selectedIntegration?.branch_id, selectedIntegration?.webhook_url]);

    const createBranchConfirmation = async (
        branchId: string,
        reason: string,
        action: "integration_reconcile" | "provider_ops_execute",
    ): Promise<string> => {
        const confirmation = await confirmationsApi.create({
            action,
            target_type: "branch",
            target_id: branchId,
            reason,
        });
        return confirmation.data.confirmation_id;
    };

    const runBranchAction = async (
        branchId: string,
        action: ProviderOpsAction,
        mode: "dry_run" | "execute",
        payload: Partial<IntegrationBranchActionRequest> = {},
        confirmationReason?: string,
    ) => {
        setRunningAction({ branchId, mode, action });
        try {
            const confirmationAction = action === "integration_reconcile" ? "integration_reconcile" : "provider_ops_execute";
            const runAction = async (confirmationId?: string) =>
                adminApi.reconcileIntegrationBranch(branchId, {
                    action,
                    mode,
                    confirmation_id: confirmationId,
                    ...payload,
                });

            let response;
            try {
                response = await runAction();
            } catch (error: unknown) {
                const apiCode = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
                if (mode !== "execute" || apiCode !== "CONFIRMATION_REQUIRED") {
                    throw error;
                }
                const normalizedReason = confirmationReason?.trim();
                if (!normalizedReason) {
                    toast.error("Reason is required");
                    return;
                }
                const confirmationId = await createBranchConfirmation(branchId, normalizedReason, confirmationAction);
                response = await runAction(confirmationId);
            }

            const result = response.data.result ?? {};
            setActionSummary(`${providerOpsActionLabel(action)}: ${JSON.stringify(result)}`);
            toast.success(mode === "dry_run" ? "Dry-run completed" : "Execute completed");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setRunningAction(null);
        }
    };

    const openProviderActionDialog = (action: ProviderOpsAction, mode: "dry_run" | "execute" = "execute") => {
        if (!selectedIntegration) {
            toast.error("Select branch integration first");
            return;
        }
        setProviderActionDialog({
            action,
            mode,
            reason: defaultExecuteReason(action),
            notes: `${providerOpsActionLabel(action)} for ${selectedIntegration.branch_slug}`,
            paidUntil: selectedIntegration.provider_binding_paid_until ?? "",
            nextRenewalAt: selectedIntegration.provider_binding_next_renewal_at ?? "",
            instanceId: branchInstanceId || selectedIntegration.instance_id || "",
        });
    };

    const closeProviderActionDialog = () => {
        if (runningAction) {
            return;
        }
        setProviderActionDialog(null);
    };

    const buildDialogPayload = (dialog: ProviderActionDialogState): Partial<IntegrationBranchActionRequest> | null => {
        if (dialog.mode === "execute" && !dialog.reason.trim()) {
            toast.error("Reason is required");
            return null;
        }
        if (dialog.action === "provider_renewal_confirmed") {
            const paidUntil = dialog.paidUntil.trim();
            const nextRenewalAt = dialog.nextRenewalAt.trim();
            if (!paidUntil && !nextRenewalAt) {
                toast.error("Specify paid_until or next_renewal_at");
                return null;
            }
            return {
                paid_until: paidUntil || undefined,
                next_renewal_at: nextRenewalAt || undefined,
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "provider_webhook_updated" || dialog.action === "provider_complete_rebind") {
            return {
                instance_id: dialog.instanceId.trim() || undefined,
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "provider_start_rebind" || dialog.action === "provider_send_reminder") {
            return {
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "integration_reconcile") {
            return {};
        }
        return null;
    };

    const submitProviderActionDialog = async () => {
        if (!providerActionDialog || !selectedIntegration) {
            return;
        }
        const payload = buildDialogPayload(providerActionDialog);
        if (payload === null) {
            return;
        }
        await runBranchAction(
            selectedIntegration.branch_id,
            providerActionDialog.action,
            providerActionDialog.mode,
            payload,
            providerActionDialog.reason,
        );
        setProviderActionDialog(null);
    };

    const saveBranchWhatsappIdentity = async () => {
        if (!scopeBranchId) {
            toast.error("Select branch");
            return;
        }
        const normalizedPhone = branchPhone.trim();
        const normalizedInstanceId = branchInstanceId.trim();
        if (!normalizedPhone || !normalizedInstanceId) {
            toast.error("phone and instance_id are required");
            return;
        }
        setBranchSaving(true);
        try {
            await adminApi.patchBranch(scopeBranchId, {
                phone: normalizedPhone,
                instance_id: normalizedInstanceId,
                is_active: true,
            });
            toast.success("Branch WhatsApp identity saved");
            await refetchIntegrations();
        } catch (error) {
            handleError(error);
        } finally {
            setBranchSaving(false);
        }
    };

    const refreshWebhookSecret = async () => {
        if (!scopeBranchId) {
            toast.error("Select branch");
            return;
        }
        try {
            const response = await adminApi.getWebhookSecret({
                branch_id: scopeBranchId,
                clientId: scopeClientId || undefined,
            });
            setWebhookSecret(response.data.webhook_secret ?? "");
            setWebhookUrl(response.data.webhook_url ?? "");
            toast.success("Webhook contract refreshed");
        } catch (error) {
            handleError(error);
        }
    };

    const approveGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Select branch");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Go-live reason is required");
            return;
        }
        setGoLiveSaving("approve");
        try {
            await adminApi.approveBranchGoLive(scopeBranchId, { reason });
            toast.success("Go-live approved");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const rejectGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Select branch");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Go-live reason is required");
            return;
        }
        setGoLiveSaving("reject");
        try {
            await adminApi.rejectBranchGoLive(scopeBranchId, { reason });
            toast.success("Go-live rejected");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const waiveGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Select branch");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Waiver reason is required");
            return;
        }
        setGoLiveSaving("waive");
        try {
            await adminApi.waiveBranchGoLive(scopeBranchId, { reason, ttl_hours: 24 });
            toast.success("Go-live waiver applied for 24h");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const wizardSteps = useMemo<WizardStep[]>(() => {
        const hasContext = Boolean(scopeCompanyId && scopeClientId && scopeBranchId);
        const hasIdentity = Boolean((selectedBranch?.phone ?? "").trim() && (selectedBranch?.instance_id ?? "").trim());
        const webhookConfigured = Boolean(
            selectedIntegration?.webhook_url_valid
            && selectedIntegration?.provider_binding_webhook_status === "configured",
        );
        const renewalTracked = Boolean(
            selectedIntegration
            && (
                (selectedIntegration.provider_binding_paid_until ?? "").trim()
                || (selectedIntegration.provider_binding_next_renewal_at ?? "").trim()
            )
            && (selectedIntegration.provider_binding_owner ?? "").trim(),
        );
        const scorecardReady = Boolean(onboardingScorecard?.ready);

        return [
            {
                id: "context",
                title: "Step 1: Select company/client/branch",
                passed: hasContext,
                detail: hasContext ? "Context selected" : "Company, client and branch are required",
                fix: "Use Scope selectors and persist context",
            },
            {
                id: "identity",
                title: "Step 2: Set WhatsApp identity",
                passed: hasIdentity,
                detail: hasIdentity ? "phone + instance_id ready" : "Branch phone and instance_id are mandatory",
                fix: "Save branch WhatsApp identity",
            },
            {
                id: "webhook",
                title: "Step 3: Verify webhook and binding",
                passed: webhookConfigured,
                detail: webhookConfigured ? "Webhook configured" : "Webhook must be valid and provider webhook_status=configured",
                fix: "Refresh webhook + run Webhook updated/Complete rebind",
            },
            {
                id: "renewal",
                title: "Step 4: Track renewal ownership",
                passed: renewalTracked,
                detail: renewalTracked ? "Renewal fields are tracked" : "owner + paid_until/next_renewal_at are required",
                fix: "Run Confirm renewal action",
            },
            {
                id: "go-live",
                title: "Step 5: Scorecard and go-live gate",
                passed: scorecardReady,
                detail: scorecardReady ? "Onboarding scorecard is ready" : "Onboarding scorecard is failing",
                fix: "Close missing scorecard checks before approve",
            },
        ];
    }, [scopeCompanyId, scopeClientId, scopeBranchId, selectedBranch?.phone, selectedBranch?.instance_id, selectedIntegration, onboardingScorecard?.ready]);

    const firstFailedStepIndex = wizardSteps.findIndex((step) => !step.passed);
    const hardStopActive = firstFailedStepIndex !== -1;

    if (!session) {
        return <div className="p-8 text-center text-muted-foreground">Sign in to use Company Workspace.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Loading role...</div>;
    }

    if (!canReadTenants && !canReadIntegrations) {
        return <AccessDenied message="No access to Company Workspace." />;
    }

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="company-workspace-page">
            <div className="rounded-lg border border-border/60 bg-card p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold">Company Workspace</h1>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Single control plane for onboarding and WhatsApp lifecycle.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Link href="/tenants" className="btn-ghost">Tenants</Link>
                        <Link href="/integrations" className="btn-ghost">Integrations</Link>
                        <Link href="/ops" className="btn-ghost">Ops</Link>
                    </div>
                </div>
            </div>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-scope">
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Scope</div>
                <div className="mt-3 grid gap-3 md:grid-cols-4">
                    <label className="text-xs text-muted-foreground">
                        company
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeCompanyId}
                            onChange={(event) => {
                                setScopeCompanyId(event.target.value);
                                setScopeClientId("");
                                setScopeBranchId("");
                            }}
                            data-testid="workspace-scope-company"
                        >
                            <option value="">select</option>
                            {(meData?.companies ?? []).map((company) => (
                                <option key={company.id} value={company.id ?? ""}>
                                    {company.name ?? company.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                        client
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeClientId}
                            onChange={(event) => {
                                setScopeClientId(event.target.value);
                                setScopeBranchId("");
                            }}
                            data-testid="workspace-scope-client"
                        >
                            <option value="">select</option>
                            {clientOptions.map((client) => (
                                <option key={client.id} value={client.id ?? ""}>
                                    {client.name ?? client.slug ?? client.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                        branch
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeBranchId}
                            onChange={(event) => setScopeBranchId(event.target.value)}
                            disabled={!scopeClientId}
                            data-testid="workspace-scope-branch"
                        >
                            <option value="">select</option>
                            {branchOptions.map((branch) => (
                                <option key={branch.id} value={branch.id ?? ""}>
                                    {branch.name ?? branch.slug ?? branch.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <div className="flex flex-wrap items-end gap-2">
                        <button className="btn-ghost" onClick={syncScopeFromContext}>From context</button>
                        <button className="btn-primary" onClick={persistScopeAsContext}>Set context</button>
                    </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                    active: company <span className="font-mono">{scopeCompanyId || "-"}</span> · client <span className="font-mono">{scopeClientId || "-"}</span> · branch <span className="font-mono">{scopeBranchId || "-"}</span>
                </div>
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-whatsapp-panel">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">WhatsApp Control Panel</h2>
                        <p className="text-xs text-muted-foreground mt-1">
                            Instance, webhook, renewal and rebind in one operational flow.
                        </p>
                    </div>
                    <button
                        className="btn-ghost"
                        onClick={() => refetchIntegrations()}
                        disabled={integrationsLoading}
                    >
                        {integrationsLoading ? "Refreshing..." : "Refresh"}
                    </button>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                        branch phone
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={branchPhone}
                            onChange={(event) => setBranchPhone(event.target.value)}
                            placeholder="+77000000000"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        instance_id
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={branchInstanceId}
                            onChange={(event) => setBranchInstanceId(event.target.value)}
                            placeholder="instance-xxxxxxxx"
                        />
                    </label>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                        className="btn-primary"
                        onClick={() => void saveBranchWhatsappIdentity()}
                        disabled={!scopeBranchId || branchSaving}
                    >
                        {branchSaving ? "Saving..." : "Save WA identity"}
                    </button>
                    <button className="btn-ghost" onClick={() => void refreshWebhookSecret()} disabled={!scopeBranchId}>
                        Get webhook contract
                    </button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("integration_reconcile", "dry_run")} disabled={!scopeBranchId || !!runningAction}>
                        Dry-run reconcile
                    </button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("integration_reconcile", "execute")} disabled={!scopeBranchId || !!runningAction}>
                        Execute reconcile
                    </button>
                </div>

                <div className="mt-3 grid gap-2 text-xs text-muted-foreground">
                    <div>webhook_url: <span className="font-mono">{webhookUrl || selectedIntegration?.webhook_url || "-"}</span></div>
                    <div>webhook_secret: <span className="font-mono">{webhookSecret || "-"}</span></div>
                    <div>provider owner: <span className="font-mono">{selectedIntegration?.provider_binding_owner || "-"}</span></div>
                    <div>paid_until: <span className="font-mono">{selectedIntegration?.provider_binding_paid_until || "-"}</span> · next_renewal_at: <span className="font-mono">{selectedIntegration?.provider_binding_next_renewal_at || "-"}</span></div>
                    <div>binding webhook: <span className="font-mono">{selectedIntegration?.provider_binding_webhook_status || "-"}</span> · status: <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusPill(selectedIntegration?.status ?? "ok")}`}>{selectedIntegration?.status ?? "-"}</span></div>
                    <div>last inbound: <span className="font-mono">{formatDateLabel(selectedIntegration?.last_inbound_at)}</span></div>
                    <div>action summary: <span className="font-mono">{actionSummary || "-"}</span></div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2" data-testid="company-workspace-provider-actions">
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_start_rebind")} disabled={!scopeBranchId || !!runningAction}>Start rebind</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_complete_rebind")} disabled={!scopeBranchId || !!runningAction}>Complete rebind</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_webhook_updated")} disabled={!scopeBranchId || !!runningAction}>Webhook updated</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_renewal_confirmed")} disabled={!scopeBranchId || !!runningAction}>Confirm renewal</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_send_reminder")} disabled={!scopeBranchId || !!runningAction}>Send reminder</button>
                </div>
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-hardstop-wizard">
                <h2 className="text-lg font-semibold">Linear Onboarding Hard-Stop</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                    Flow: Create -&gt; WA identity -&gt; Webhook verify -&gt; Renewal tracking -&gt; Go-live.
                </p>

                <div className="mt-3 space-y-2">
                    {wizardSteps.map((step, index) => {
                        const isCurrentBlocker = !step.passed && firstFailedStepIndex === index;
                        return (
                            <div key={step.id} className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="text-sm font-medium">{step.title}</div>
                                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${step.passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                        {step.passed ? "pass" : "fail"}
                                    </span>
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground">{step.detail}</div>
                                {!step.passed ? (
                                    <div className={`mt-1 text-xs ${isCurrentBlocker ? "text-red-700" : "text-muted-foreground"}`}>
                                        fix: {step.fix}{isCurrentBlocker ? " (current blocker)" : ""}
                                    </div>
                                ) : null}
                            </div>
                        );
                    })}
                </div>

                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-sm font-medium">Go-live decision</div>
                    <label className="mt-2 block text-xs text-muted-foreground">
                        reason
                        <textarea
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            rows={2}
                            value={goLiveReason}
                            onChange={(event) => setGoLiveReason(event.target.value)}
                            placeholder="go-live decision reason"
                        />
                    </label>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button
                            className="btn-primary"
                            onClick={() => void approveGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || hardStopActive || goLiveSaving !== null}
                        >
                            {goLiveSaving === "approve" ? "Approving..." : "Approve go-live"}
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => void rejectGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || goLiveSaving !== null}
                        >
                            {goLiveSaving === "reject" ? "Rejecting..." : "Reject"}
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => void waiveGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || hardStopActive || goLiveSaving !== null}
                        >
                            {goLiveSaving === "waive" ? "Waiving..." : "Waive 24h"}
                        </button>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        hard-stop: {hardStopActive ? "active" : "clear"} · scorecard: {onboardingScorecard?.status ?? "-"}
                    </div>
                </div>
            </section>

            {providerActionDialog && selectedIntegration ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="workspace-action-modal-overlay">
                    <div className="w-full max-w-xl rounded-xl border border-border/60 bg-card p-5 shadow-xl" role="dialog" aria-modal="true" data-testid="workspace-action-modal">
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-semibold">{providerOpsActionLabel(providerActionDialog.action)}</h2>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {selectedIntegration.client_slug} / {selectedIntegration.branch_name} · mode: {providerActionDialog.mode}
                                </p>
                            </div>
                            <button type="button" className="btn-ghost" onClick={closeProviderActionDialog} disabled={!!runningAction}>Close</button>
                        </div>

                        <div className="mt-4 space-y-3">
                            {providerActionDialog.mode === "execute" ? (
                                <label className="text-xs text-muted-foreground">
                                    reason (required)
                                    <textarea
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        rows={2}
                                        value={providerActionDialog.reason}
                                        onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, reason: event.target.value } : prev))}
                                        placeholder="execute reason"
                                    />
                                </label>
                            ) : null}

                            <label className="text-xs text-muted-foreground">
                                notes
                                <textarea
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    rows={2}
                                    value={providerActionDialog.notes}
                                    onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, notes: event.target.value } : prev))}
                                    placeholder="operation notes"
                                />
                            </label>

                            {providerActionDialog.action === "provider_complete_rebind" || providerActionDialog.action === "provider_webhook_updated" ? (
                                <label className="text-xs text-muted-foreground">
                                    instance_id
                                    <input
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={providerActionDialog.instanceId}
                                        onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, instanceId: event.target.value } : prev))}
                                        placeholder="instance-xxxxxxxx"
                                    />
                                </label>
                            ) : null}

                            {providerActionDialog.action === "provider_renewal_confirmed" ? (
                                <div className="grid gap-3 sm:grid-cols-2">
                                    <label className="text-xs text-muted-foreground">
                                        paid_until
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={providerActionDialog.paidUntil}
                                            onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, paidUntil: event.target.value } : prev))}
                                            placeholder="2026-12-31"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        next_renewal_at
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={providerActionDialog.nextRenewalAt}
                                            onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, nextRenewalAt: event.target.value } : prev))}
                                            placeholder="2026-12-31"
                                        />
                                    </label>
                                </div>
                            ) : null}
                        </div>

                        <div className="mt-4 flex items-center justify-end gap-2">
                            <button type="button" className="btn-ghost" onClick={closeProviderActionDialog} disabled={!!runningAction}>Cancel</button>
                            <button type="button" className="btn-primary" onClick={() => void submitProviderActionDialog()} disabled={!!runningAction}>
                                {runningAction ? "Running..." : providerActionDialog.mode === "execute" ? "Execute" : "Dry-run"}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
