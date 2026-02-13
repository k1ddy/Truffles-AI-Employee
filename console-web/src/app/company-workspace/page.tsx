"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import {
    adminApi,
    authApi,
    canAccessConsole,
} from "@/lib/api-client";

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

function setContextValue(key: string, value?: string | null) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}

function statusPill(status: "p0" | "p1" | "p2"): string {
    if (status === "p0") {
        return "bg-red-100 text-red-700";
    }
    if (status === "p1") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-blue-100 text-blue-700";
}

function formatDateLabel(value?: string | null): string {
    if (!value) {
        return "—";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("ru-RU");
}

export default function CompanyWorkspacePage() {
    const router = useRouter();
    const { data: session } = useSession();

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
    const canReadIntegrations = canAccessConsole(role, "integrations", "read");

    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? null;
    const selectedClientId = meData?.client?.id ?? null;
    const selectedBranchId = meData?.selected_branch_id ?? null;

    const { data: clientsData } = useQuery({
        queryKey: ["company-workspace-clients", selectedCompanyId],
        queryFn: async () => {
            const response = await adminApi.listClients({
                limit: 100,
                lifecycle: "active",
                company_id: selectedCompanyId ?? undefined,
                include_fleet: "true",
            });
            return response.data;
        },
        enabled: !!session && canReadTenants,
    });

    const { data: branchesData } = useQuery({
        queryKey: ["company-workspace-branches", selectedClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                limit: 100,
                lifecycle: "active",
                client_id: selectedClientId ?? undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadTenants && !!selectedClientId,
    });

    const { data: integrationsData, isLoading: integrationsLoading, refetch: refetchIntegrations } = useQuery({
        queryKey: ["company-workspace-integrations"],
        queryFn: async () => {
            const response = await adminApi.listIntegrations({ stale_after_minutes: 60 });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
        refetchInterval: 60000,
    });

    const filteredQueue = useMemo(() => {
        const providerOpsQueue = integrationsData?.provider_ops_queue ?? [];
        if (!selectedClientId) {
            return providerOpsQueue;
        }
        return providerOpsQueue.filter((item) => item.client_id === selectedClientId);
    }, [integrationsData?.provider_ops_queue, selectedClientId]);

    const filteredIntegrations = useMemo(() => {
        const integrationItems = integrationsData?.items ?? [];
        if (!selectedClientId) {
            return integrationItems;
        }
        return integrationItems.filter((item) => item.client_id === selectedClientId);
    }, [integrationsData?.items, selectedClientId]);

    const integrationsSummary = useMemo(() => {
        const total = filteredIntegrations.length;
        const error = filteredIntegrations.filter((item) => item.status === "error").length;
        const warn = filteredIntegrations.filter((item) => item.status === "warn").length;
        return { total, error, warn };
    }, [filteredIntegrations]);

    const applyContextAndOpenIntegrations = (item: { client_id: string; branch_id: string }) => {
        const companyId = clientsData?.items?.find((client) => client.id === item.client_id)?.company_id ?? selectedCompanyId ?? null;
        setContextValue(COMPANY_ID_STORAGE_KEY, companyId);
        setContextValue(CLIENT_ID_STORAGE_KEY, item.client_id);
        setContextValue(BRANCH_ID_STORAGE_KEY, item.branch_id);
        router.push("/integrations");
    };

    if (!session) {
        return <div className="p-8 text-center text-muted-foreground">Войдите в систему для работы с Company Workspace.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли...</div>;
    }

    if (!canReadTenants && !canReadIntegrations) {
        return <AccessDenied message="Нет доступа к Company Workspace." />;
    }

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="company-workspace-page">
            <div className="rounded-lg border border-border/60 bg-card p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold">Company Workspace</h1>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Единый операционный экран для platform-admin: контекст компании, provider ops и онбординг.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Link href="/tenants" className="btn-ghost">Тенанты</Link>
                        <Link href="/integrations" className="btn-ghost">Интеграции</Link>
                        <Link href="/ops" className="btn-ghost">Ops</Link>
                    </div>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">
                    Контекст: company <span className="font-mono">{selectedCompanyId ?? "—"}</span> · client <span className="font-mono">{selectedClientId ?? "—"}</span> · branch <span className="font-mono">{selectedBranchId ?? "—"}</span>
                </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-3">
                <div className="rounded-lg border border-border/60 bg-card p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Integrations Summary</div>
                    <div className="mt-2 text-sm text-muted-foreground">Филиалы в текущем контексте клиента.</div>
                    <div className="mt-3 space-y-1 text-sm">
                        <div>total: <span className="font-mono">{integrationsSummary.total}</span></div>
                        <div>warn: <span className="font-mono">{integrationsSummary.warn}</span></div>
                        <div>error: <span className="font-mono">{integrationsSummary.error}</span></div>
                    </div>
                </div>

                <div className="rounded-lg border border-border/60 bg-card p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Active Fleet</div>
                    <div className="mt-2 text-sm text-muted-foreground">Клиенты: {clientsData?.items?.length ?? 0}</div>
                    <div className="mt-1 text-sm text-muted-foreground">Филиалы: {branchesData?.items?.length ?? 0}</div>
                    <div className="mt-3 text-xs text-muted-foreground">
                        Для операций по provider lifecycle используйте queue ниже и переход в Integrations.
                    </div>
                </div>

                <div className="rounded-lg border border-border/60 bg-card p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Queue Control</div>
                    <div className="mt-2 text-sm text-muted-foreground">Provider ops queue: {filteredQueue.length}</div>
                    <button className="btn-ghost mt-3" onClick={() => refetchIntegrations()} disabled={integrationsLoading}>
                        {integrationsLoading ? "Обновление..." : "Обновить queue"}
                    </button>
                </div>
            </div>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-provider-queue">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="text-lg font-semibold">Provider Ops Queue</h2>
                    <span className="text-xs text-muted-foreground">{formatDateLabel(filteredQueue[0]?.generated_at)}</span>
                </div>
                <div className="mt-3 space-y-2">
                    {filteredQueue.length === 0 ? (
                        <div className="text-sm text-muted-foreground">Очередь пуста для текущего контекста.</div>
                    ) : (
                        filteredQueue.slice(0, 12).map((item) => (
                            <div key={`${item.branch_id}-${item.recommended_action}`} className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <div className="font-medium">{item.client_slug} / {item.branch_name}</div>
                                        <div className="text-xs text-muted-foreground">reasons: {item.reasons.join(", ")}</div>
                                    </div>
                                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusPill(item.priority)}`}>
                                        {item.priority.toUpperCase()}
                                    </span>
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <button
                                        className="btn-ghost"
                                        onClick={() => applyContextAndOpenIntegrations(item)}
                                    >
                                        Открыть в Integrations
                                    </button>
                                    <span className="text-xs text-muted-foreground">recommended: {item.recommended_action}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </section>

            {canReadTenants ? (
                <div className="mt-4" data-testid="company-workspace-onboarding">
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
