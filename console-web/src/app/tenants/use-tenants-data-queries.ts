"use client";

import { type InfiniteData, useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type { components } from "@/types/api.generated";
import { adminApi, auditApi, type TenantsWeeklySnapshotRecord } from "@/lib/api-client";

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetLifecycleFilter = "all" | "lead" | "contracting" | "onboarding" | "go_live_ready" | "active" | "paused" | "archived";
type FleetPaymentFilter = "all" | "pending" | "confirmed" | "rejected" | "unknown";
type FleetServiceFilter = "all" | "ok" | "degraded" | "attention";

type UseTenantsDataQueriesParams<TSnapshot> = {
    tenantsEnabled: boolean;
    companyQueryValue?: string;
    clientQueryValue?: string;
    branchQueryValue?: string;
    pageFilterCompanyId: string | null;
    pageFilterClientId: string | null;
    pageFilterBranchId: string | null;
    tenantLifecycle: TenantLifecycleMode;
    fleetLifecycleFilter: FleetLifecycleFilter;
    fleetPaymentFilter: FleetPaymentFilter;
    fleetServiceFilter: FleetServiceFilter;
    branchEditorId?: string;
    maxWeeklySnapshots: number;
    mapWeeklySnapshotRecordToViewModel: (record: TenantsWeeklySnapshotRecord) => TSnapshot | null;
};

export function useTenantsDataQueries<TSnapshot>({
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
    branchEditorId,
    maxWeeklySnapshots,
    mapWeeklySnapshotRecordToViewModel,
}: UseTenantsDataQueriesParams<TSnapshot>) {
    const companiesQuery = useInfiniteQuery<
        components["schemas"]["ConsoleCompanyListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleCompanyListResponse"], string | undefined>,
        ["tenants-companies", string | undefined],
        string | undefined
    >({
        queryKey: ["tenants-companies", companyQueryValue],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listCompanies({
                cursor,
                limit: 20,
                q: companyQueryValue,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const tenantsPortfolioQuery = useQuery({
        queryKey: [
            "tenants-portfolio",
            clientQueryValue,
            pageFilterCompanyId,
            tenantLifecycle,
            fleetLifecycleFilter,
            fleetPaymentFilter,
            fleetServiceFilter,
        ],
        queryFn: async () => {
            const response = await adminApi.getTenantsPortfolio({
                limit: 20,
                q: clientQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                lifecycle: tenantLifecycle,
                attention_limit: 12,
                stale_after_minutes: 60,
                include_low: "false",
            });
            return response.data;
        },
        enabled: tenantsEnabled,
        staleTime: 30000,
    });

    const tenantsCompanyCockpitQuery = useQuery({
        queryKey: [
            "tenants-company-cockpit",
            pageFilterCompanyId,
            pageFilterClientId,
            clientQueryValue,
            branchQueryValue,
            tenantLifecycle,
        ],
        queryFn: async () => {
            if (!pageFilterCompanyId) {
                return null;
            }
            const response = await adminApi.getTenantsCompanyCockpit({
                company_id: pageFilterCompanyId,
                client_id: pageFilterClientId ?? undefined,
                include_branches: "false",
                lifecycle: tenantLifecycle,
                client_limit: 20,
                client_q: clientQueryValue,
            });
            return response.data;
        },
        enabled: tenantsEnabled && !!pageFilterCompanyId,
        staleTime: 30000,
    });

    const clientsQuery = useInfiniteQuery<
        components["schemas"]["ConsoleClientListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleClientListResponse"], string | undefined>,
        [
            "tenants-clients",
            string | undefined,
            string | null,
            TenantLifecycleMode,
            FleetLifecycleFilter,
            FleetPaymentFilter,
            FleetServiceFilter,
        ],
        string | undefined
    >({
        queryKey: [
            "tenants-clients",
            clientQueryValue,
            pageFilterCompanyId,
            tenantLifecycle,
            fleetLifecycleFilter,
            fleetPaymentFilter,
            fleetServiceFilter,
        ],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listClients({
                cursor,
                limit: 20,
                q: clientQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                lifecycle: tenantLifecycle,
                include_fleet: "true",
                include_summary: cursor ? undefined : "true",
                fleet_lifecycle: fleetLifecycleFilter === "all" ? undefined : fleetLifecycleFilter,
                payment_status: fleetPaymentFilter === "all" ? undefined : fleetPaymentFilter,
                service_state: fleetServiceFilter === "all" ? undefined : fleetServiceFilter,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const branchesQuery = useInfiniteQuery<
        components["schemas"]["ConsoleBranchListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleBranchListResponse"], string | undefined>,
        ["tenants-branches", string | undefined, string | null, string | null, string | null, TenantLifecycleMode],
        string | undefined
    >({
        queryKey: ["tenants-branches", branchQueryValue, pageFilterCompanyId, pageFilterClientId, pageFilterBranchId, tenantLifecycle],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listBranches({
                cursor,
                limit: 20,
                q: branchQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                client_id: pageFilterClientId ?? undefined,
                branch_id: pageFilterBranchId ?? undefined,
                lifecycle: tenantLifecycle,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const fleetAttentionQuery = useQuery({
        queryKey: ["tenants-fleet-attention", tenantLifecycle],
        queryFn: async () => {
            const response = await adminApi.listFleetAttention({
                limit: 12,
                stale_after_minutes: 60,
                include_low: "false",
            });
            return response.data;
        },
        enabled: tenantsEnabled && tenantLifecycle === "active" && tenantsPortfolioQuery.isError,
    });

    const branchChangesQuery = useQuery({
        queryKey: ["tenants-branch-changes", branchEditorId],
        queryFn: async () => {
            if (!branchEditorId) {
                return null;
            }
            const response = await adminApi.listBranchChanges({
                branch_id: branchEditorId,
                limit: 10,
            });
            return response.data;
        },
        enabled: tenantsEnabled && !!branchEditorId,
    });

    const recentBranchChangesKpiQuery = useQuery({
        queryKey: ["tenants-branch-changes-recent-kpi", tenantLifecycle],
        queryFn: async () => {
            const response = await adminApi.listBranchChanges({
                limit: 100,
            });
            return response.data;
        },
        enabled: tenantsEnabled && tenantLifecycle === "active",
    });

    const selectedClientAuditQuery = useQuery<components["schemas"]["ConsoleAuditEvent"][]>({
        queryKey: ["tenants-client-lifecycle-audit-api", pageFilterClientId],
        queryFn: async () => {
            if (!pageFilterClientId) {
                return [];
            }
            const response = await auditApi.list({
                entity_type: "client",
                entity_id: pageFilterClientId,
                limit: 50,
            });
            return (response.data.items ?? []) as components["schemas"]["ConsoleAuditEvent"][];
        },
        enabled: tenantsEnabled && !!pageFilterClientId,
        staleTime: 30000,
    });

    const weeklySnapshotsServerQuery = useQuery({
        queryKey: ["tenants-weekly-snapshots", pageFilterClientId],
        queryFn: async () => {
            if (!pageFilterClientId) {
                return [] as TSnapshot[];
            }
            const response = await adminApi.listTenantsWeeklySnapshots({
                client_id: pageFilterClientId,
                limit: maxWeeklySnapshots,
            });
            return (response.data.items ?? [])
                .map((item) => mapWeeklySnapshotRecordToViewModel(item))
                .filter((item): item is TSnapshot => item !== null);
        },
        enabled: tenantsEnabled && !!pageFilterClientId,
        staleTime: 30000,
    });

    return {
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
    };
}
