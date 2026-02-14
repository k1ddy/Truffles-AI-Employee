"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    adminApi,
    authApi,
    canAccessConsole,
    type BranchIntegrationStatus,
    type ProviderOpsAction,
    type ProviderOpsQueueItem,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

type ScopeTarget = {
    companyId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
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

function statusBadgeClass(status: string): string {
    if (status === "error") {
        return "bg-red-100 text-red-800";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-green-100 text-green-800";
}

function statusLabel(status: string): string {
    const labels: Record<string, string> = {
        ok: "OK",
        warn: "Warning",
        error: "Error",
        inactive: "Inactive",
        missing_instance_id: "Missing instance_id",
        instance_id_mismatch: "Instance mismatch",
        invalid_webhook_url: "Invalid webhook URL",
        invalid_webhook_secret: "Invalid webhook secret",
        webhook_secret_drift: "Webhook secret drift",
        no_recent_inbound: "No recent inbound",
        inbound_without_outbound: "Inbound without outbound",
        missing_bot_token: "Missing bot token",
        missing_chat_id: "Missing chat id",
        provider_binding_rebind_required: "Provider rebind required",
        provider_binding_expired: "Provider binding expired",
        provider_binding_expiring_soon: "Provider binding expiring soon",
        provider_binding_alert_critical: "Provider alert critical",
        provider_binding_alert_warn: "Provider alert warn",
    };
    return labels[status] ?? status;
}

function paymentStatusLabel(status?: string | null): string {
    if (status === "confirmed") {
        return "Confirmed";
    }
    if (status === "rejected") {
        return "Rejected";
    }
    if (status === "pending") {
        return "Pending";
    }
    return "Unknown";
}

function providerBindingExpiryLabel(status?: string | null): string {
    if (status === "ok") {
        return "OK";
    }
    if (status === "expiring_soon") {
        return "Expiring soon";
    }
    if (status === "expired") {
        return "Expired";
    }
    return "Unknown";
}

function providerBindingExpiryBadgeClass(status?: string | null): string {
    if (status === "expired") {
        return "bg-red-100 text-red-800";
    }
    if (status === "expiring_soon") {
        return "bg-amber-100 text-amber-800";
    }
    if (status === "ok") {
        return "bg-green-100 text-green-800";
    }
    return "bg-muted text-muted-foreground";
}

function providerBindingAlertLabel(status?: string | null): string {
    if (status === "ok") {
        return "Alert OK";
    }
    if (status === "warn") {
        return "Alert Warn";
    }
    if (status === "critical") {
        return "Alert Critical";
    }
    return "Alert Unknown";
}

function providerBindingAlertBadgeClass(status?: string | null): string {
    if (status === "critical") {
        return "bg-red-100 text-red-800";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    if (status === "ok") {
        return "bg-green-100 text-green-800";
    }
    return "bg-muted text-muted-foreground";
}

function formatTimestamp(value?: string | null): string {
    if (!value) {
        return "-";
    }
    return new Date(value).toLocaleString("ru-RU");
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
        return "Update webhook";
    }
    if (action === "provider_send_reminder") {
        return "Send reminder";
    }
    return "Reconcile";
}

function DriftIssues({ item }: { item: BranchIntegrationStatus }) {
    if (!item.drift_issues || item.drift_issues.length === 0) {
        return <span className="text-muted-foreground">-</span>;
    }
    return (
        <div className="flex flex-wrap gap-1">
            {item.drift_issues.map((issue) => (
                <span
                    key={`${item.branch_id}-${issue}`}
                    className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-800"
                >
                    {statusLabel(issue)}
                </span>
            ))}
        </div>
    );
}

export default function IntegrationsPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const { handleError } = useErrorHandler();
    const [staleAfterMinutes, setStaleAfterMinutes] = useState(60);
    const [scopeCompanyId, setScopeCompanyId] = useState("");
    const [scopeClientId, setScopeClientId] = useState("");
    const [scopeBranchId, setScopeBranchId] = useState("");
    const [scopeInitialized, setScopeInitialized] = useState(false);

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadIntegrations = canAccessConsole(role, "integrations", "read");
    const companyOptions = meData?.companies ?? [];

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

    const { data: clientsData } = useQuery({
        queryKey: ["integrations-scope-clients", scopeCompanyId],
        queryFn: async () => {
            const response = await adminApi.listClients({
                limit: 100,
                lifecycle: "active",
                company_id: scopeCompanyId || undefined,
                include_fleet: "true",
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
    });
    const clientOptions = useMemo(() => clientsData?.items ?? [], [clientsData?.items]);

    const { data: branchesData } = useQuery({
        queryKey: ["integrations-scope-branches", scopeClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                limit: 100,
                lifecycle: "active",
                client_id: scopeClientId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations && !!scopeClientId,
    });
    const branchOptions = useMemo(() => branchesData?.items ?? [], [branchesData?.items]);

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
        toast.success("Контекст сохранен");
    };

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ["integrations-registry", staleAfterMinutes, scopeCompanyId, scopeClientId, scopeBranchId],
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

    useEffect(() => {
        if (error) {
            handleError(error);
        }
    }, [error, handleError]);

    const clientCompanyMap = useMemo(() => {
        const result = new Map<string, string>();
        for (const client of meData?.clients ?? []) {
            if (client?.id && client?.company_id) {
                result.set(String(client.id), String(client.company_id));
            }
        }
        return result;
    }, [meData?.clients]);

    const persistScopeAndOpenWorkspace = (target: ScopeTarget, note?: string) => {
        const normalizedClient = target.clientId ? String(target.clientId) : "";
        const normalizedBranch = target.branchId ? String(target.branchId) : "";
        const fallbackCompany = readLocalStorageValue(COMPANY_ID_STORAGE_KEY) ?? "";
        const normalizedCompany = target.companyId
            ? String(target.companyId)
            : (normalizedClient ? clientCompanyMap.get(normalizedClient) : undefined) ?? scopeCompanyId ?? fallbackCompany;

        setLocalStorageValue(COMPANY_ID_STORAGE_KEY, normalizedCompany || null);
        setLocalStorageValue(CLIENT_ID_STORAGE_KEY, normalizedClient || null);
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, normalizedBranch || null);

        if (note) {
            toast.success(note);
        }
        router.push("/company-workspace");
    };

    const openWorkspaceForRow = (item: BranchIntegrationStatus) => {
        persistScopeAndOpenWorkspace(
            {
                clientId: item.client_id,
                branchId: item.branch_id,
            },
            "Переход в Workspace",
        );
    };

    const openWorkspaceForQueueItem = (queueItem: ProviderOpsQueueItem) => {
        persistScopeAndOpenWorkspace(
            {
                clientId: queueItem.client_id,
                branchId: queueItem.branch_id,
            },
            `Queue -> ${providerOpsActionLabel(queueItem.recommended_action)}`,
        );
    };

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра интеграций.
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

    if (!canReadIntegrations) {
        return <AccessDenied message="Эта роль не имеет доступа к интеграциям." />;
    }

    if (isLoading) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="integrations-title">Интеграции</h1>
                <div className="animate-pulse space-y-3">
                    {[...Array(8)].map((_, index) => (
                        <div key={index} className="h-12 bg-muted/70 rounded" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="integrations-title">Интеграции</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="integrations-error">
                    <p className="text-destructive mb-4">Не удалось загрузить интеграции</p>
                    <button
                        onClick={() => refetch()}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="integrations-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    const items = data?.items ?? [];
    const providerOpsQueue = data?.provider_ops_queue ?? [];

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="integrations-title">Интеграции</h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Реестр статусов WhatsApp/Telegram и provider lifecycle. Все execute-операции выполняются в Workspace.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <label className="text-sm text-muted-foreground" htmlFor="stale-after-select">
                        Stale threshold
                    </label>
                    <select
                        id="stale-after-select"
                        className="rounded border border-border/70 bg-background px-3 py-2 text-sm"
                        value={staleAfterMinutes}
                        onChange={(event) => setStaleAfterMinutes(Number(event.target.value))}
                        data-testid="integrations-stale-select"
                    >
                        <option value={15}>15 min</option>
                        <option value={30}>30 min</option>
                        <option value={60}>60 min</option>
                        <option value={180}>180 min</option>
                    </select>
                    <Link href="/" className="text-primary hover:text-primary/80">
                        ← Назад к заявкам
                    </Link>
                </div>
            </div>

            <section className="mb-4 rounded-lg border border-blue-300/50 bg-blue-50/60 p-4" data-testid="integrations-workspace-cta">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div className="text-sm font-semibold text-blue-900">Workspace-first operations</div>
                        <div className="text-xs text-blue-800/80 mt-1">
                            Rebind, renewal, webhook update и reconcile execute перенесены в единый cockpit `Company Workspace`.
                        </div>
                    </div>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={() => {
                            persistScopeAndOpenWorkspace({
                                companyId: scopeCompanyId || null,
                                clientId: scopeClientId || null,
                                branchId: scopeBranchId || null,
                            });
                        }}
                        data-testid="integrations-open-workspace"
                    >
                        Open Workspace
                    </button>
                </div>
            </section>

            <div className="mb-3 text-xs text-muted-foreground" data-testid="integrations-threshold-info">
                stale_after_minutes: {data?.stale_after_minutes ?? staleAfterMinutes}
            </div>

            <section className="mb-4 rounded-lg border border-border/60 bg-card p-4" data-testid="integrations-scope-controls">
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Scope</div>
                <div className="mt-2 grid gap-3 md:grid-cols-4">
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
                            data-testid="integrations-scope-company"
                        >
                            <option value="">all</option>
                            {companyOptions.map((company) => (
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
                            data-testid="integrations-scope-client"
                        >
                            <option value="">all</option>
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
                            data-testid="integrations-scope-branch"
                        >
                            <option value="">all</option>
                            {branchOptions.map((branch) => (
                                <option key={branch.id} value={branch.id ?? ""}>
                                    {branch.name ?? branch.slug ?? branch.id}
                                </option>
                            ))}
                        </select>
                    </label>

                    <div className="flex flex-wrap items-end gap-2">
                        <button
                            className="btn-ghost"
                            onClick={() => {
                                setScopeCompanyId("");
                                setScopeClientId("");
                                setScopeBranchId("");
                            }}
                            data-testid="integrations-scope-reset"
                        >
                            Сбросить
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={syncScopeFromContext}
                            data-testid="integrations-scope-sync"
                        >
                            Из контекста
                        </button>
                        <button
                            className="btn-primary"
                            onClick={persistScopeAsContext}
                            data-testid="integrations-scope-save"
                        >
                            В контекст
                        </button>
                    </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                    effective: company <span className="font-mono">{scopeCompanyId || "all"}</span> · client <span className="font-mono">{scopeClientId || "all"}</span> · branch <span className="font-mono">{scopeBranchId || "all"}</span>
                </div>
            </section>

            {providerOpsQueue.length > 0 && (
                <div className="mb-4 rounded-lg border border-amber-300/60 bg-amber-50/60 p-4" data-testid="provider-ops-queue">
                    <div className="mb-2 text-sm font-semibold text-amber-900">
                        Provider Ops Queue ({providerOpsQueue.length})
                    </div>
                    <div className="space-y-2">
                        {providerOpsQueue.map((queueItem) => (
                            <div
                                key={`queue-${queueItem.branch_id}`}
                                className="flex flex-wrap items-center justify-between gap-3 rounded border border-amber-300/50 bg-background/80 p-2 text-xs"
                            >
                                <div>
                                    <div className="font-medium text-foreground">
                                        {queueItem.client_slug} / {queueItem.branch_name}
                                    </div>
                                    <div className="text-muted-foreground">
                                        priority {queueItem.priority.toUpperCase()} · action {providerOpsActionLabel(queueItem.recommended_action)}
                                    </div>
                                    <div className="text-muted-foreground">
                                        reasons: {queueItem.reasons.map((reason) => statusLabel(reason)).join(", ")}
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    className="rounded-full border border-border/60 px-3 py-1 font-medium hover:bg-muted"
                                    onClick={() => openWorkspaceForQueueItem(queueItem)}
                                    data-testid="integrations-queue-open-workspace"
                                >
                                    Manage in Workspace
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="bg-card border border-border/60 rounded-lg overflow-hidden" data-testid="integrations-table">
                <table className="w-full text-left">
                    <thead className="bg-muted">
                        <tr>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Клиент</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Филиал</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">WhatsApp</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Telegram</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Provider binding</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Оплата/срок</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Последний inbound</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Drift issues</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Итог</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Workspace</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item) => (
                            <tr
                                key={item.branch_id}
                                className="border-t border-border/60 hover:bg-muted/50"
                                data-testid="integrations-row"
                            >
                                <td className="p-4">
                                    <div className="font-medium">{item.client_slug}</div>
                                    <div className="text-xs text-muted-foreground">{item.client_id}</div>
                                </td>
                                <td className="p-4">
                                    <div className="font-medium">{item.branch_name}</div>
                                    <div className="text-xs text-muted-foreground">{item.branch_slug}</div>
                                    {!item.is_active && (
                                        <div className="text-xs text-muted-foreground">archived</div>
                                    )}
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{statusLabel(item.whatsapp_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        instance: {item.instance_id ?? "-"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{statusLabel(item.telegram_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        chat: {item.telegram_chat_id ?? "-"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{item.provider_binding_provider ?? "-"}</div>
                                    <div className="text-xs text-muted-foreground">
                                        binding instance: {item.provider_binding_instance_id ?? "-"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        webhook: {item.provider_binding_webhook_status ?? "-"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        owner: {item.provider_binding_owner ?? "-"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{paymentStatusLabel(item.provider_binding_payment_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        paid_until: {item.provider_binding_paid_until ?? "-"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        next_renewal: {item.provider_binding_next_renewal_at ?? "-"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        last_rebind: {item.provider_binding_last_rebind_at ?? "-"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        rebind_required: {item.provider_binding_rebind_required ? "yes" : "no"}
                                    </div>
                                    <div className="mt-1">
                                        <span
                                            className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingExpiryBadgeClass(item.provider_binding_expiry_status)}`}
                                        >
                                            {providerBindingExpiryLabel(item.provider_binding_expiry_status)}
                                        </span>
                                    </div>
                                    <div className="mt-1">
                                        <span
                                            className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingAlertBadgeClass(item.provider_binding_alert_state)}`}
                                        >
                                            {providerBindingAlertLabel(item.provider_binding_alert_state)}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        days left: {item.provider_binding_days_until_expiry ?? "-"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{formatTimestamp(item.last_inbound_at)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        instance: {item.last_inbound_instance_id ?? "-"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <DriftIssues item={item} />
                                </td>
                                <td className="p-4">
                                    <span className={`rounded px-2 py-1 text-xs font-medium ${statusBadgeClass(item.status)}`}>
                                        {statusLabel(item.status)}
                                    </span>
                                </td>
                                <td className="p-4 text-sm">
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                        onClick={() => openWorkspaceForRow(item)}
                                        data-testid="integrations-row-open-workspace"
                                    >
                                        Manage in Workspace
                                    </button>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        Execute actions only in Workspace
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {items.length === 0 && (
                            <tr>
                                <td colSpan={10} className="p-8 text-center text-muted-foreground" data-testid="integrations-empty">
                                    Филиалы в доступном fleet не найдены.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
