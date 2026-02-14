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
    type Branch,
    type BranchIntegrationStatus,
    type Client,
    type ProviderOpsQueueItem,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import type { components } from "@/types/api.generated";

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

const STALE_AFTER_OPTIONS = [15, 30, 60, 180] as const;

type ScopeTarget = {
    companyId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
};

type StatusFilter = "all" | "error" | "warn" | "ok";
type ExpiryFilter = "all" | "expired" | "expiring" | "ok" | "unknown";
type TeamFilter = "all" | "gap" | "no_manager" | "no_specialist" | "understaffed";

type AgentMembership = components["schemas"]["AgentMembership"];
type Company = components["schemas"]["Company"];

type MembershipStats = {
    total: number;
    managers: number;
    specialists: number;
    support: number;
};

type EnrichedRow = BranchIntegrationStatus & {
    company_id: string | null;
    company_name: string;
    client_name: string;
    onboarding_state: string | null;
    go_live_state: string | null;
    go_live_allowed: boolean;
    team_stats: MembershipStats;
    team_issue: string | null;
};

function createEmptyMembershipStats(): MembershipStats {
    return {
        total: 0,
        managers: 0,
        specialists: 0,
        support: 0,
    };
}

function accumulateMembershipStats(target: MembershipStats, role: AgentMembership["role"] | undefined) {
    target.total += 1;
    if (role === "manager") {
        target.managers += 1;
    }
    if (role === "specialist") {
        target.specialists += 1;
    }
    if (role === "support") {
        target.support += 1;
    }
}

function mergeMembershipStats(...items: Array<MembershipStats | undefined>): MembershipStats {
    const merged = createEmptyMembershipStats();
    for (const item of items) {
        if (!item) {
            continue;
        }
        merged.total += item.total;
        merged.managers += item.managers;
        merged.specialists += item.specialists;
        merged.support += item.support;
    }
    return merged;
}

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

function normalizeText(value?: string | null): string {
    return (value ?? "").trim().toLowerCase();
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

function providerOpsActionLabel(action: ProviderOpsQueueItem["recommended_action"]): string {
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

function goLiveStateLabel(value?: string | null): string {
    if (!value) {
        return "pending";
    }
    return value;
}

function goLiveBadgeClass(allowed: boolean, state?: string | null): string {
    if (allowed) {
        return "bg-green-100 text-green-800";
    }
    if (state === "rejected") {
        return "bg-red-100 text-red-800";
    }
    return "bg-amber-100 text-amber-800";
}

function teamIssueFromStats(stats: MembershipStats): string | null {
    if (stats.managers === 0) {
        return "No manager";
    }
    if (stats.specialists === 0) {
        return "No specialist";
    }
    if (stats.total < 2) {
        return "Understaffed";
    }
    return null;
}

function teamBadgeClass(issue: string | null): string {
    if (!issue) {
        return "bg-green-100 text-green-800";
    }
    if (issue === "No manager") {
        return "bg-red-100 text-red-800";
    }
    return "bg-amber-100 text-amber-800";
}

function onboardingStateLabel(value?: string | null): string {
    if (!value) {
        return "unknown";
    }
    return value;
}

function rowSeverityWeight(row: EnrichedRow): number {
    let score = 0;
    if (row.status === "error") {
        score += 100;
    }
    if (row.status === "warn") {
        score += 40;
    }
    if (row.provider_binding_expiry_status === "expired") {
        score += 80;
    }
    if (row.provider_binding_expiry_status === "expiring_soon") {
        score += 35;
    }
    if (row.provider_binding_rebind_required) {
        score += 60;
    }
    if (row.team_issue === "No manager") {
        score += 50;
    }
    if (row.team_issue === "No specialist") {
        score += 25;
    }
    if (row.team_issue === "Understaffed") {
        score += 20;
    }
    return score;
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

function KpiCard({
    title,
    value,
    description,
    tone,
}: {
    title: string;
    value: string;
    description: string;
    tone: "neutral" | "good" | "warn" | "critical";
}) {
    const cardClass =
        tone === "critical"
            ? "border-red-300/80 bg-red-50"
            : tone === "warn"
                ? "border-amber-300/80 bg-amber-50"
                : tone === "good"
                    ? "border-emerald-300/80 bg-emerald-50"
                    : "border-border/60 bg-card";

    return (
        <div className={`rounded-xl border p-4 ${cardClass}`}>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
            <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{description}</div>
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

    const [searchText, setSearchText] = useState("");
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
    const [expiryFilter, setExpiryFilter] = useState<ExpiryFilter>("all");
    const [teamFilter, setTeamFilter] = useState<TeamFilter>("all");

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

    const {
        data: companiesData,
        error: companiesError,
    } = useQuery({
        queryKey: ["integrations-companies"],
        queryFn: async () => {
            const response = await adminApi.listCompanies({ limit: 300 });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
    });

    const {
        data: clientsData,
        error: clientsError,
    } = useQuery({
        queryKey: ["integrations-clients", scopeCompanyId],
        queryFn: async () => {
            const response = await adminApi.listClients({
                limit: 500,
                lifecycle: "active",
                company_id: scopeCompanyId || undefined,
                include_fleet: "true",
                include_summary: "true",
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
    });

    const clientOptions = useMemo<Client[]>(() => clientsData?.items ?? [], [clientsData?.items]);

    const {
        data: branchesData,
        error: branchesError,
    } = useQuery({
        queryKey: ["integrations-branches", scopeClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                limit: 500,
                lifecycle: "active",
                client_id: scopeClientId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
    });

    const branchOptions = useMemo<Branch[]>(() => branchesData?.items ?? [], [branchesData?.items]);

    const {
        data: integrationsData,
        isLoading: integrationsLoading,
        error: integrationsError,
        refetch: refetchIntegrations,
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

    const {
        data: membershipsData,
        error: membershipsError,
    } = useQuery({
        queryKey: ["integrations-memberships", scopeCompanyId, scopeClientId, scopeBranchId],
        queryFn: async () => {
            const response = await adminApi.listMemberships({
                include_inactive: "false",
                company_id: scopeCompanyId || undefined,
                client_id: scopeClientId || undefined,
                branch_id: scopeBranchId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
    });

    const {
        data: fleetAttentionData,
        error: fleetAttentionError,
    } = useQuery({
        queryKey: ["integrations-fleet-attention", staleAfterMinutes],
        queryFn: async () => {
            const response = await adminApi.listFleetAttention({
                stale_after_minutes: staleAfterMinutes,
                include_low: "true",
                limit: 20,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
        refetchInterval: 120000,
    });

    useEffect(() => {
        if (integrationsError) {
            handleError(integrationsError);
        }
    }, [integrationsError, handleError]);

    useEffect(() => {
        if (companiesError) {
            handleError(companiesError);
        }
    }, [companiesError, handleError]);

    useEffect(() => {
        if (clientsError) {
            handleError(clientsError);
        }
    }, [clientsError, handleError]);

    useEffect(() => {
        if (branchesError) {
            handleError(branchesError);
        }
    }, [branchesError, handleError]);

    useEffect(() => {
        if (membershipsError) {
            handleError(membershipsError);
        }
    }, [membershipsError, handleError]);

    useEffect(() => {
        if (fleetAttentionError) {
            handleError(fleetAttentionError);
        }
    }, [fleetAttentionError, handleError]);

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

    const companyOptions = useMemo<Company[]>(() => {
        const fromMe = meData?.companies ?? [];
        const fromApi = companiesData?.items ?? [];
        const merged = new Map<string, Company>();
        for (const company of [...fromApi, ...fromMe]) {
            if (company?.id) {
                merged.set(String(company.id), company as Company);
            }
        }
        return [...merged.values()];
    }, [companiesData?.items, meData?.companies]);

    const companyById = useMemo(() => {
        const result = new Map<string, Company>();
        for (const company of companyOptions) {
            if (company.id) {
                result.set(String(company.id), company);
            }
        }
        return result;
    }, [companyOptions]);

    const clientById = useMemo(() => {
        const result = new Map<string, Client>();
        for (const client of clientOptions) {
            if (client.id) {
                result.set(String(client.id), client);
            }
        }
        return result;
    }, [clientOptions]);

    const branchById = useMemo(() => {
        const result = new Map<string, Branch>();
        for (const branch of branchOptions) {
            if (branch.id) {
                result.set(String(branch.id), branch);
            }
        }
        return result;
    }, [branchOptions]);

    const clientCompanyMap = useMemo(() => {
        const result = new Map<string, string>();
        for (const client of clientOptions) {
            if (client?.id && client?.company_id) {
                result.set(String(client.id), String(client.company_id));
            }
        }
        for (const client of meData?.clients ?? []) {
            if (client?.id && client?.company_id && !result.has(String(client.id))) {
                result.set(String(client.id), String(client.company_id));
            }
        }
        return result;
    }, [clientOptions, meData?.clients]);

    const membershipStatsByScope = useMemo(() => {
        const branchMap = new Map<string, MembershipStats>();
        const clientMap = new Map<string, MembershipStats>();
        const companyMap = new Map<string, MembershipStats>();

        const updateMap = (
            targetMap: Map<string, MembershipStats>,
            key: string | null | undefined,
            role: AgentMembership["role"] | undefined,
        ) => {
            if (!key) {
                return;
            }
            const current = targetMap.get(key) ?? createEmptyMembershipStats();
            accumulateMembershipStats(current, role);
            targetMap.set(key, current);
        };

        for (const membership of membershipsData?.items ?? []) {
            const record = membership as AgentMembership;
            if (!record.is_active) {
                continue;
            }

            if (record.scope === "branch") {
                updateMap(branchMap, record.branch_id ? String(record.branch_id) : null, record.role);
                continue;
            }

            if (record.scope === "client") {
                updateMap(clientMap, record.client_id ? String(record.client_id) : null, record.role);
                continue;
            }

            if (record.scope === "company") {
                updateMap(companyMap, record.company_id ? String(record.company_id) : null, record.role);
                continue;
            }
        }

        return {
            branchMap,
            clientMap,
            companyMap,
        };
    }, [membershipsData?.items]);

    const integrationsItems = useMemo(() => integrationsData?.items ?? [], [integrationsData?.items]);

    const rows = useMemo<EnrichedRow[]>(() => {
        return integrationsItems
            .map((item) => {
                const client = clientById.get(item.client_id);
                const branch = branchById.get(item.branch_id);
                const companyId = (client?.company_id ? String(client.company_id) : clientCompanyMap.get(item.client_id)) ?? null;
                const companyName = companyId
                    ? (companyById.get(companyId)?.name ?? companyId)
                    : (client?.company_name ?? "-");

                const teamStats = mergeMembershipStats(
                    companyId ? membershipStatsByScope.companyMap.get(companyId) : undefined,
                    membershipStatsByScope.clientMap.get(item.client_id),
                    membershipStatsByScope.branchMap.get(item.branch_id),
                );
                const teamIssue = teamIssueFromStats(teamStats);

                return {
                    ...item,
                    company_id: companyId,
                    company_name: companyName,
                    client_name: client?.name ?? client?.slug ?? item.client_slug,
                    onboarding_state: branch?.onboarding_state ?? null,
                    go_live_state: branch?.go_live_state ?? null,
                    go_live_allowed: Boolean(branch?.go_live_allowed),
                    team_stats: teamStats,
                    team_issue: teamIssue,
                };
            })
            .sort((a, b) => rowSeverityWeight(b) - rowSeverityWeight(a));
    }, [branchById, clientById, clientCompanyMap, companyById, integrationsItems, membershipStatsByScope]);

    const filteredRows = useMemo(() => {
        const q = normalizeText(searchText);
        return rows.filter((row) => {
            if (statusFilter !== "all" && row.status !== statusFilter) {
                return false;
            }
            if (expiryFilter !== "all") {
                const expiry = row.provider_binding_expiry_status ?? "unknown";
                if (expiryFilter === "expired" && expiry !== "expired") {
                    return false;
                }
                if (expiryFilter === "expiring" && expiry !== "expiring_soon") {
                    return false;
                }
                if (expiryFilter === "ok" && expiry !== "ok") {
                    return false;
                }
                if (expiryFilter === "unknown" && expiry !== "unknown") {
                    return false;
                }
            }

            if (teamFilter !== "all") {
                if (teamFilter === "gap" && !row.team_issue) {
                    return false;
                }
                if (teamFilter === "no_manager" && row.team_stats.managers > 0) {
                    return false;
                }
                if (teamFilter === "no_specialist" && row.team_stats.specialists > 0) {
                    return false;
                }
                if (teamFilter === "understaffed" && row.team_stats.total >= 2) {
                    return false;
                }
            }

            if (!q) {
                return true;
            }

            const haystack = [
                row.company_name,
                row.client_name,
                row.client_slug,
                row.branch_name,
                row.branch_slug,
                row.instance_id ?? "",
                row.provider_binding_owner ?? "",
                row.provider_binding_instance_id ?? "",
                row.onboarding_state ?? "",
                row.go_live_state ?? "",
            ]
                .join(" ")
                .toLowerCase();

            return haystack.includes(q);
        });
    }, [expiryFilter, rows, searchText, statusFilter, teamFilter]);

    const kpi = useMemo(() => {
        const allRows = rows;
        const companySet = new Set<string>();
        const clientSet = new Set<string>();
        for (const row of allRows) {
            if (row.company_id) {
                companySet.add(row.company_id);
            }
            clientSet.add(row.client_id);
        }

        const errorBranches = allRows.filter((row) => row.status === "error").length;
        const warnBranches = allRows.filter((row) => row.status === "warn").length;
        const expiredBindings = allRows.filter((row) => row.provider_binding_expiry_status === "expired").length;
        const expiringSoon = allRows.filter((row) => row.provider_binding_expiry_status === "expiring_soon").length;
        const rebindRequired = allRows.filter((row) => Boolean(row.provider_binding_rebind_required)).length;
        const teamGaps = allRows.filter((row) => Boolean(row.team_issue)).length;
        const goLiveAllowed = allRows.filter((row) => row.go_live_allowed).length;
        const staleInbound = allRows.filter((row) => row.whatsapp_status === "no_recent_inbound").length;

        return {
            totalCompanies: companySet.size,
            totalClients: clientSet.size,
            totalBranches: allRows.length,
            errorBranches,
            warnBranches,
            expiredBindings,
            expiringSoon,
            rebindRequired,
            teamGaps,
            goLiveAllowed,
            staleInbound,
            filteredBranches: filteredRows.length,
        };
    }, [filteredRows.length, rows]);

    const fleetAttentionSummary = fleetAttentionData?.summary;
    const providerOpsQueue = integrationsData?.provider_ops_queue ?? [];

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

    const openWorkspaceForRow = (row: EnrichedRow) => {
        persistScopeAndOpenWorkspace(
            {
                companyId: row.company_id,
                clientId: row.client_id,
                branchId: row.branch_id,
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
        return <div className="p-8 text-center text-muted-foreground">Войдите в систему для просмотра интеграций.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли...</div>;
    }

    if (!canReadIntegrations) {
        return <AccessDenied message="Эта роль не имеет доступа к интеграциям." />;
    }

    if (integrationsLoading && integrationsItems.length === 0) {
        return (
            <div className="mx-auto max-w-[1400px] p-6" data-testid="integrations-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="integrations-title">Fleet Control Center</h1>
                <div className="space-y-3 animate-pulse">
                    {[...Array(8)].map((_, index) => (
                        <div key={index} className="h-12 rounded bg-muted/70" />
                    ))}
                </div>
            </div>
        );
    }

    if (integrationsError && integrationsItems.length === 0) {
        return (
            <div className="mx-auto max-w-[1400px] p-6" data-testid="integrations-page">
                <h1 className="mb-6 text-2xl font-bold" data-testid="integrations-title">Fleet Control Center</h1>
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid="integrations-error">
                    <p className="mb-4 text-destructive">Не удалось загрузить интеграции</p>
                    <button
                        onClick={() => refetchIntegrations()}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="integrations-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-[1400px] p-6" data-testid="integrations-page">
            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="integrations-title">Fleet Control Center</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Единый обзор по всем компаниям: филиалы, подписки provider, team coverage, onboarding/go-live, ops-риски.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => refetchIntegrations()}
                    >
                        Обновить
                    </button>
                    <Link href="/company-workspace" className="btn-primary" data-testid="integrations-open-workspace">
                        Open Workspace
                    </Link>
                    <Link href="/tenants" className="btn-ghost">Tenants</Link>
                    <Link href="/ops" className="btn-ghost">Ops</Link>
                </div>
            </div>

            <section className="mb-4 rounded-xl border border-blue-300/50 bg-blue-50/60 p-4" data-testid="integrations-workspace-cta">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div className="text-sm font-semibold text-blue-900">Workspace-first execution</div>
                        <div className="mt-1 text-xs text-blue-800/80">
                            Execute-операции (rebind, renewal, webhook update, reconcile) выполняются только в `Company Workspace`.
                        </div>
                    </div>
                    <div className="text-xs text-blue-900/80">
                        stale_after_minutes: <span className="font-mono">{integrationsData?.stale_after_minutes ?? staleAfterMinutes}</span>
                    </div>
                </div>
            </section>

            <section className="rounded-xl border border-border/60 bg-card p-4" data-testid="integrations-scope-controls">
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Scope + filters</div>
                <div className="mt-3 grid gap-3 lg:grid-cols-6">
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

                    <label className="text-xs text-muted-foreground">
                        stale threshold
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={staleAfterMinutes}
                            onChange={(event) => setStaleAfterMinutes(Number(event.target.value))}
                            data-testid="integrations-stale-select"
                        >
                            {STALE_AFTER_OPTIONS.map((minutes) => (
                                <option key={minutes} value={minutes}>{minutes} min</option>
                            ))}
                        </select>
                    </label>

                    <label className="text-xs text-muted-foreground">
                        status
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={statusFilter}
                            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                        >
                            <option value="all">all</option>
                            <option value="error">error</option>
                            <option value="warn">warn</option>
                            <option value="ok">ok</option>
                        </select>
                    </label>

                    <label className="text-xs text-muted-foreground">
                        search
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="company / client / branch / instance"
                            value={searchText}
                            onChange={(event) => setSearchText(event.target.value)}
                        />
                    </label>
                </div>

                <div className="mt-3 grid gap-3 lg:grid-cols-4">
                    <label className="text-xs text-muted-foreground">
                        expiry
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={expiryFilter}
                            onChange={(event) => setExpiryFilter(event.target.value as ExpiryFilter)}
                        >
                            <option value="all">all</option>
                            <option value="expired">expired</option>
                            <option value="expiring">expiring soon</option>
                            <option value="ok">ok</option>
                            <option value="unknown">unknown</option>
                        </select>
                    </label>

                    <label className="text-xs text-muted-foreground">
                        team
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={teamFilter}
                            onChange={(event) => setTeamFilter(event.target.value as TeamFilter)}
                        >
                            <option value="all">all</option>
                            <option value="gap">any gap</option>
                            <option value="no_manager">no manager</option>
                            <option value="no_specialist">no specialist</option>
                            <option value="understaffed">understaffed</option>
                        </select>
                    </label>

                    <div className="flex flex-wrap items-end gap-2">
                        <button
                            className="btn-ghost"
                            onClick={() => {
                                setScopeCompanyId("");
                                setScopeClientId("");
                                setScopeBranchId("");
                                setSearchText("");
                                setStatusFilter("all");
                                setExpiryFilter("all");
                                setTeamFilter("all");
                            }}
                            data-testid="integrations-scope-reset"
                        >
                            Reset
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={syncScopeFromContext}
                            data-testid="integrations-scope-sync"
                        >
                            From context
                        </button>
                        <button
                            className="btn-primary"
                            onClick={persistScopeAsContext}
                            data-testid="integrations-scope-save"
                        >
                            Set context
                        </button>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                        showing <span className="font-semibold text-foreground">{kpi.filteredBranches}</span> of {kpi.totalBranches} branches
                        <div className="mt-1">
                            company <span className="font-mono">{scopeCompanyId || "all"}</span> · client <span className="font-mono">{scopeClientId || "all"}</span> · branch <span className="font-mono">{scopeBranchId || "all"}</span>
                        </div>
                    </div>
                </div>
            </section>

            <section className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5" data-testid="integrations-kpi-grid">
                <KpiCard
                    title="Coverage"
                    value={`${kpi.totalCompanies} / ${kpi.totalClients} / ${kpi.totalBranches}`}
                    description="companies / clients / branches in scope"
                    tone="neutral"
                />
                <KpiCard
                    title="Health"
                    value={`${kpi.errorBranches} err · ${kpi.warnBranches} warn`}
                    description="integration status by branch"
                    tone={kpi.errorBranches > 0 ? "critical" : kpi.warnBranches > 0 ? "warn" : "good"}
                />
                <KpiCard
                    title="Provider Expiry"
                    value={`${kpi.expiredBindings} expired · ${kpi.expiringSoon} soon`}
                    description="paid_until / renewal risks"
                    tone={kpi.expiredBindings > 0 ? "critical" : kpi.expiringSoon > 0 ? "warn" : "good"}
                />
                <KpiCard
                    title="Rebind"
                    value={`${kpi.rebindRequired}`}
                    description="branches with rebind_required=true"
                    tone={kpi.rebindRequired > 0 ? "warn" : "good"}
                />
                <KpiCard
                    title="Team"
                    value={`${kpi.teamGaps} gaps · ${kpi.goLiveAllowed} go-live`}
                    description="team coverage gaps and go-live allowed"
                    tone={kpi.teamGaps > 0 ? "warn" : "good"}
                />
            </section>

            {fleetAttentionSummary && (
                <section className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-xl border border-red-300/70 bg-red-50 p-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-red-800">Fleet Attention</div>
                        <div className="mt-2 text-2xl font-semibold text-red-900">{fleetAttentionSummary.high_risk_clients}</div>
                        <div className="text-xs text-red-900/80">high risk clients</div>
                    </div>
                    <div className="rounded-xl border border-amber-300/70 bg-amber-50 p-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">Stale / Errors</div>
                        <div className="mt-2 text-2xl font-semibold text-amber-900">{fleetAttentionSummary.stale_branches_total + fleetAttentionSummary.integration_error_branches_total}</div>
                        <div className="text-xs text-amber-900/80">stale + integration error branches</div>
                    </div>
                    <div className="rounded-xl border border-blue-300/70 bg-blue-50 p-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-800">Queues</div>
                        <div className="mt-2 text-2xl font-semibold text-blue-900">{fleetAttentionSummary.outbox_failed_24h_total + fleetAttentionSummary.pending_handovers_total}</div>
                        <div className="text-xs text-blue-900/80">outbox failed + pending handovers</div>
                    </div>
                </section>
            )}

            {fleetAttentionData?.items?.length ? (
                <section className="mt-4 rounded-xl border border-border/60 bg-card p-4" data-testid="integrations-fleet-attention-list">
                    <div className="text-sm font-semibold">Top risk clients</div>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                        {fleetAttentionData.items.slice(0, 8).map((item) => (
                            <div key={item.client_id} className="rounded-lg border border-border/60 p-3 text-xs">
                                <div className="flex items-center justify-between gap-2">
                                    <div className="font-medium text-foreground">{item.company_name ?? "-"} / {item.client_name ?? item.client_slug}</div>
                                    <span className={`rounded px-2 py-0.5 font-semibold ${item.attention_level === "high" ? "bg-red-100 text-red-800" : item.attention_level === "medium" ? "bg-amber-100 text-amber-800" : "bg-blue-100 text-blue-800"}`}>
                                        {item.attention_level}
                                    </span>
                                </div>
                                <div className="mt-1 text-muted-foreground">
                                    action: {item.next_action} · reasons: {item.reasons.join(", ") || "-"}
                                </div>
                                <div className="mt-1 text-muted-foreground">
                                    branches {item.active_branches}/{item.total_branches} · stale {item.stale_branches} · degraded {item.degraded_branches}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            ) : null}

            {providerOpsQueue.length > 0 && (
                <section className="mt-4 rounded-xl border border-amber-300/60 bg-amber-50/60 p-4" data-testid="provider-ops-queue">
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
                </section>
            )}

            <section className="mt-4 overflow-hidden rounded-xl border border-border/60 bg-card" data-testid="integrations-branch-matrix">
                <div className="space-y-3 p-3 md:hidden">
                    {filteredRows.map((row) => (
                        <article key={`mobile-${row.branch_id}`} className="rounded-lg border border-border/60 p-3 text-xs" data-testid="integrations-mobile-row">
                            <div className="font-medium">{row.company_name}</div>
                            <div className="text-muted-foreground">{row.client_name} ({row.client_slug})</div>
                            <div className="mt-1 font-semibold">{row.branch_name}</div>
                            <div className="text-muted-foreground">{row.branch_slug}</div>

                            <div className="mt-2 flex flex-wrap items-center gap-1">
                                <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${statusBadgeClass(row.status)}`}>{statusLabel(row.status)}</span>
                                <span className="rounded bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">WA: {statusLabel(row.whatsapp_status)}</span>
                                <span className="rounded bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">TG: {statusLabel(row.telegram_status)}</span>
                            </div>

                            <div className="mt-2 text-muted-foreground">owner: {row.provider_binding_owner ?? "-"} · paid_until: {row.provider_binding_paid_until ?? "-"}</div>
                            <div className="mt-1 flex flex-wrap items-center gap-1">
                                <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingExpiryBadgeClass(row.provider_binding_expiry_status)}`}>
                                    {providerBindingExpiryLabel(row.provider_binding_expiry_status)}
                                </span>
                                <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingAlertBadgeClass(row.provider_binding_alert_state)}`}>
                                    {providerBindingAlertLabel(row.provider_binding_alert_state)}
                                </span>
                            </div>

                            <div className="mt-2">
                                <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${teamBadgeClass(row.team_issue)}`}>{row.team_issue ?? "Team OK"}</span>
                                <span className="ml-2 text-muted-foreground">mgr {row.team_stats.managers} · spec {row.team_stats.specialists} · total {row.team_stats.total}</span>
                            </div>

                            <div className="mt-2 text-muted-foreground">
                                onboarding: {onboardingStateLabel(row.onboarding_state)} · go-live: {goLiveStateLabel(row.go_live_state)}{row.go_live_allowed ? " (allowed)" : ""}
                            </div>

                            <div className="mt-2 text-muted-foreground">last inbound: {formatTimestamp(row.last_inbound_at)}</div>
                            <div className="mt-1"><DriftIssues item={row} /></div>

                            <button
                                type="button"
                                className="mt-3 rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                onClick={() => openWorkspaceForRow(row)}
                            >
                                Manage in Workspace
                            </button>
                        </article>
                    ))}
                    {filteredRows.length === 0 && (
                        <div className="p-4 text-center text-muted-foreground" data-testid="integrations-empty">
                            Нет филиалов по текущему scope/filter.
                        </div>
                    )}
                </div>

                <div className="hidden overflow-x-auto md:block">
                    <table className="w-full text-left">
                        <thead className="bg-muted/70">
                            <tr>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Company / Client / Branch</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Channels</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Provider Subscription</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Team</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Onboarding / Go-live</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Last inbound / Drift</th>
                                <th className="p-4 text-sm font-medium text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredRows.map((row) => (
                                <tr
                                    key={row.branch_id}
                                    className="border-t border-border/60 align-top hover:bg-muted/30"
                                    data-testid="integrations-row"
                                >
                                    <td className="p-4">
                                        <div className="font-medium">{row.company_name}</div>
                                        <div className="text-xs text-muted-foreground">{row.client_name} ({row.client_slug})</div>
                                        <div className="mt-1 font-medium">{row.branch_name}</div>
                                        <div className="text-xs text-muted-foreground">{row.branch_slug}</div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusBadgeClass(row.status)}`}>
                                                {statusLabel(row.status)}
                                            </span>
                                            <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                                WA: {statusLabel(row.whatsapp_status)}
                                            </span>
                                            <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                                TG: {statusLabel(row.telegram_status)}
                                            </span>
                                        </div>
                                        <div className="mt-2 text-xs text-muted-foreground">instance: {row.instance_id ?? "-"}</div>
                                        <div className="text-xs text-muted-foreground">binding instance: {row.provider_binding_instance_id ?? "-"}</div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <div className="text-xs text-muted-foreground">owner: {row.provider_binding_owner ?? "-"}</div>
                                        <div className="text-xs text-muted-foreground">paid_until: {row.provider_binding_paid_until ?? "-"}</div>
                                        <div className="text-xs text-muted-foreground">next_renewal: {row.provider_binding_next_renewal_at ?? "-"}</div>
                                        <div className="mt-1 flex flex-wrap items-center gap-1">
                                            <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingExpiryBadgeClass(row.provider_binding_expiry_status)}`}>
                                                {providerBindingExpiryLabel(row.provider_binding_expiry_status)}
                                            </span>
                                            <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingAlertBadgeClass(row.provider_binding_alert_state)}`}>
                                                {providerBindingAlertLabel(row.provider_binding_alert_state)}
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            days left: {row.provider_binding_days_until_expiry ?? "-"} · rebind_required: {row.provider_binding_rebind_required ? "yes" : "no"}
                                        </div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <div className="text-xs text-muted-foreground">
                                            total: {row.team_stats.total} · mgr: {row.team_stats.managers} · spec: {row.team_stats.specialists} · support: {row.team_stats.support}
                                        </div>
                                        <div className="mt-1">
                                            <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${teamBadgeClass(row.team_issue)}`}>
                                                {row.team_issue ?? "Team OK"}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <div className="text-xs text-muted-foreground">onboarding: {onboardingStateLabel(row.onboarding_state)}</div>
                                        <div className="mt-1">
                                            <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${goLiveBadgeClass(row.go_live_allowed, row.go_live_state)}`}>
                                                go-live: {goLiveStateLabel(row.go_live_state)}{row.go_live_allowed ? " (allowed)" : ""}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <div>{formatTimestamp(row.last_inbound_at)}</div>
                                        <div className="mt-1 text-xs text-muted-foreground">last inbound instance: {row.last_inbound_instance_id ?? "-"}</div>
                                        <div className="mt-2"><DriftIssues item={row} /></div>
                                    </td>
                                    <td className="p-4 text-sm">
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                            onClick={() => openWorkspaceForRow(row)}
                                            data-testid="integrations-row-open-workspace"
                                        >
                                            Manage in Workspace
                                        </button>
                                        <div className="mt-1 text-xs text-muted-foreground">Open scoped workspace for this branch</div>
                                    </td>
                                </tr>
                            ))}
                            {filteredRows.length === 0 && (
                                <tr>
                                    <td colSpan={7} className="p-8 text-center text-muted-foreground" data-testid="integrations-empty">
                                        Нет филиалов по текущему scope/filter.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}
