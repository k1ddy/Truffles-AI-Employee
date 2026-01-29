"use client";

import { useMemo, useState } from "react";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import { adminApi, authApi, canAccessConsole } from "@/lib/api-client";

const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";
const COMPANY_ID_STORAGE_KEY = "console:company_id";

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

export default function TenantsPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const [clientQuery, setClientQuery] = useState("");
    const [branchQuery, setBranchQuery] = useState("");
    const [companyQuery, setCompanyQuery] = useState("");

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

    const selectedClientId = meData?.client?.id ?? null;
    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? null;
    const selectedBranchId = meData?.selected_branch_id ?? null;

    const tenantsEnabled = Boolean(session && canReadTenants);
    const companyQueryValue = companyQuery.trim() || undefined;
    const clientQueryValue = clientQuery.trim() || undefined;
    const branchQueryValue = branchQuery.trim() || undefined;

    const companiesQuery = useInfiniteQuery({
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
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const clientsQuery = useInfiniteQuery({
        queryKey: ["tenants-clients", clientQueryValue],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listClients({
                cursor,
                limit: 20,
                q: clientQueryValue,
            });
            return response.data;
        },
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const branchesQuery = useInfiniteQuery({
        queryKey: ["tenants-branches", branchQueryValue],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listBranches({
                cursor,
                limit: 20,
                q: branchQueryValue,
            });
            return response.data;
        },
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const companies = useMemo(
        () => companiesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [companiesQuery.data],
    );
    const clients = useMemo(
        () => clientsQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [clientsQuery.data],
    );
    const branches = useMemo(
        () => branchesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [branchesQuery.data],
    );

    const refreshContext = () => {
        queryClient.invalidateQueries({ queryKey: ["console-me"] });
    };

    const setCompanyContext = (companyId?: string | null) => {
        setLocalStorageValue(COMPANY_ID_STORAGE_KEY, companyId);
        setLocalStorageValue(CLIENT_ID_STORAGE_KEY, null);
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, null);
        refreshContext();
    };

    const setClientContext = (clientId?: string | null, companyId?: string | null) => {
        setLocalStorageValue(COMPANY_ID_STORAGE_KEY, companyId ?? null);
        setLocalStorageValue(CLIENT_ID_STORAGE_KEY, clientId ?? null);
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, null);
        refreshContext();
    };

    const setBranchContext = (branchId?: string | null) => {
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, branchId ?? null);
        refreshContext();
    };

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра Tenants.
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
            <AccessDenied message="Эта роль не имеет доступа к Tenants." />
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="tenants-page">
            <div className="flex flex-col gap-2 mb-6">
                <h1 className="text-2xl font-bold" data-testid="tenants-title">Тенанты</h1>
                <div className="text-xs text-muted-foreground">
                    Контекст: {selectedCompanyId ?? "—"} / {meData?.client?.name ?? selectedClientId ?? "—"} / {selectedBranchId ?? "—"}
                </div>
            </div>

            <div className="grid gap-6">
                <section className="bg-card border border-border/60 rounded-lg p-5">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Компании</h2>
                            <p className="text-sm text-muted-foreground">
                                {companiesQuery.isLoading ? "—" : `${companies.length} всего`}
                            </p>
                        </div>
                        <input
                            className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Поиск по компаниям"
                            value={companyQuery}
                            onChange={(event) => setCompanyQuery(event.target.value)}
                        />
                    </div>
                    <div className="space-y-3">
                        {companiesQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка компаний...</div>
                        ) : companiesQuery.isError ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить компании.</div>
                        ) : companies.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Компании не найдены.</div>
                        ) : (
                            companies.map((company) => (
                                <div
                                    key={company.id}
                                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                >
                                    <div>
                                        <div className="font-medium">{company.name ?? "Без названия"}</div>
                                        <div className="text-xs text-muted-foreground">{company.id}</div>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{company.id === selectedCompanyId ? "Выбрана" : ""}</span>
                                        <button
                                            className="btn-ghost"
                                            onClick={() => setCompanyContext(company.id)}
                                            disabled={company.id === selectedCompanyId}
                                        >
                                            В контекст
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    {companiesQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => companiesQuery.fetchNextPage()}
                                disabled={companiesQuery.isFetchingNextPage}
                            >
                                {companiesQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>

                <section className="bg-card border border-border/60 rounded-lg p-5">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Клиенты</h2>
                            <p className="text-sm text-muted-foreground">
                                {clientsQuery.isLoading ? "—" : `${clients.length} всего`}
                            </p>
                        </div>
                        <input
                            className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Поиск по клиентам"
                            value={clientQuery}
                            onChange={(event) => setClientQuery(event.target.value)}
                        />
                    </div>
                    <div className="space-y-3">
                        {clientsQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка клиентов...</div>
                        ) : clientsQuery.isError ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить клиентов.</div>
                        ) : clients.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Клиенты не найдены.</div>
                        ) : (
                            clients.map((client) => (
                                <div
                                    key={client.id}
                                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                >
                                    <div>
                                        <div className="font-medium">{client.name ?? client.slug ?? "Без названия"}</div>
                                        <div className="text-xs text-muted-foreground">{client.id}</div>
                                        {client.company_name ? (
                                            <div className="text-xs text-muted-foreground">{client.company_name}</div>
                                        ) : null}
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{client.id === selectedClientId ? "Выбран" : ""}</span>
                                        <button
                                            className="btn-ghost"
                                            onClick={() => setClientContext(client.id, client.company_id)}
                                            disabled={client.id === selectedClientId}
                                        >
                                            В контекст
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    {clientsQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => clientsQuery.fetchNextPage()}
                                disabled={clientsQuery.isFetchingNextPage}
                            >
                                {clientsQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>

                <section className="bg-card border border-border/60 rounded-lg p-5">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Филиалы</h2>
                            <p className="text-sm text-muted-foreground">
                                {branchesQuery.isLoading ? "—" : `${branches.length} всего`}
                            </p>
                        </div>
                        <input
                            className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Поиск по филиалам"
                            value={branchQuery}
                            onChange={(event) => setBranchQuery(event.target.value)}
                        />
                    </div>
                    <div className="space-y-3">
                        {branchesQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка филиалов...</div>
                        ) : branchesQuery.isError ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить филиалы.</div>
                        ) : branches.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Филиалы не найдены.</div>
                        ) : (
                            branches.map((branch) => (
                                <div
                                    key={branch.id}
                                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                >
                                    <div>
                                        <div className="font-medium">{branch.name ?? branch.slug ?? "Без названия"}</div>
                                        <div className="text-xs text-muted-foreground">{branch.id}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {branch.instance_id ? `instance_id: ${branch.instance_id}` : "instance_id: —"}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {branch.onboarding_state ? `onboarding: ${branch.onboarding_state}` : "onboarding: —"}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{branch.id === selectedBranchId ? "Выбран" : ""}</span>
                                        <button
                                            className="btn-ghost"
                                            onClick={() => setBranchContext(branch.id)}
                                            disabled={branch.id === selectedBranchId}
                                        >
                                            В контекст
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    {branchesQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => branchesQuery.fetchNextPage()}
                                disabled={branchesQuery.isFetchingNextPage}
                            >
                                {branchesQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>
            </div>

            <div className="mt-10">
                <ProvisioningWizard session={session} accessSection="tenants" />
            </div>
        </div>
    );
}
