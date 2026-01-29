"use client";

import { useMemo, useState } from "react";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import { adminApi, authApi, canAccessConsole, confirmationsApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

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
    status: string;
    originalSlug: string;
    originalCompanyId: string;
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
    confirmReason: string;
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

function parseOptionalJson(value: string, label: string): { value?: Record<string, unknown>; error?: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return {};
    }
    try {
        return { value: JSON.parse(trimmed) as Record<string, unknown> };
    } catch {
        return { error: `${label}: некорректный JSON` };
    }
}

export default function TenantsPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();
    const [clientQuery, setClientQuery] = useState("");
    const [branchQuery, setBranchQuery] = useState("");
    const [companyQuery, setCompanyQuery] = useState("");
    const [companyEditor, setCompanyEditor] = useState<CompanyEditorState | null>(null);
    const [clientEditor, setClientEditor] = useState<ClientEditorState | null>(null);
    const [branchEditor, setBranchEditor] = useState<BranchEditorState | null>(null);
    const [savingCompany, setSavingCompany] = useState(false);
    const [savingClient, setSavingClient] = useState(false);
    const [savingBranch, setSavingBranch] = useState(false);

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

    const refreshTenants = () => {
        queryClient.invalidateQueries({ queryKey: ["tenants-companies"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-clients"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branches"] });
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

    const startCompanyEdit = (company: components["schemas"]["Company"]) => {
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
    };

    const startClientEdit = (client: components["schemas"]["Client"]) => {
        setCompanyEditor(null);
        setBranchEditor(null);
        setClientEditor({
            id: client.id,
            slug: client.slug ?? client.name ?? "",
            companyId: client.company_id ?? "",
            status: client.status ?? "",
            originalSlug: client.slug ?? client.name ?? "",
            originalCompanyId: client.company_id ?? "",
        });
    };

    const startBranchEdit = (branch: components["schemas"]["Branch"]) => {
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
            confirmReason: "",
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
    };

    const handleSaveCompany = async () => {
        if (!companyEditor) {
            return;
        }
        const name = companyEditor.name.trim();
        if (!name) {
            toast.error("Укажите название компании");
            return;
        }
        const billing = parseOptionalJson(companyEditor.billingInfo, "billing_info");
        if (billing.error) {
            toast.error(billing.error);
            return;
        }
        const payload: components["schemas"]["CompanyUpdateRequest"] = {};
        if (name !== companyEditor.originalName) {
            payload.name = name;
        }
        if (companyEditor.billingInfo.trim() !== companyEditor.originalBillingInfo.trim()) {
            payload.billing_info = billing.value ?? {};
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
            handleError(error);
        } finally {
            setSavingCompany(false);
        }
    };

    const handleSaveClient = async () => {
        if (!clientEditor) {
            return;
        }
        const slug = clientEditor.slug.trim();
        if (!slug) {
            toast.error("Укажите slug клиента");
            return;
        }
        const payload: components["schemas"]["ClientUpdateRequest"] = {};
        if (slug !== clientEditor.originalSlug) {
            payload.slug = slug;
        }
        const companyId = clientEditor.companyId.trim();
        if (companyId !== clientEditor.originalCompanyId) {
            payload.company_id = companyId || null;
        }
        const statusValue = clientEditor.status.trim();
        if (statusValue) {
            payload.status = statusValue;
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
            handleError(error);
        } finally {
            setSavingClient(false);
        }
    };

    const requiresBranchConfirmation = (editor: BranchEditorState) => {
        const removedInstance = editor.original.instanceId && !editor.instanceId.trim();
        const deactivated = editor.original.isActive && !editor.isActive;
        return removedInstance || deactivated;
    };

    const handleSaveBranch = async () => {
        if (!branchEditor) {
            return;
        }
        const name = branchEditor.name.trim();
        const slug = branchEditor.slug.trim();
        if (!name || !slug) {
            toast.error("Заполните название и slug филиала");
            return;
        }
        if (branchEditor.isActive && !branchEditor.instanceId.trim()) {
            toast.error("instance_id обязателен для активного филиала");
            return;
        }
        const payload: components["schemas"]["BranchUpdateRequest"] = {};
        if (name !== branchEditor.original.name) {
            payload.name = name;
        }
        if (slug !== branchEditor.original.slug) {
            payload.slug = slug;
        }
        const timezone = branchEditor.timezone.trim();
        if (timezone !== branchEditor.original.timezone) {
            payload.timezone = timezone || null;
        }
        const phone = branchEditor.phone.trim();
        if (phone !== branchEditor.original.phone) {
            payload.phone = phone || null;
        }
        const instanceId = branchEditor.instanceId.trim();
        if (instanceId !== branchEditor.original.instanceId) {
            payload.instance_id = instanceId || null;
        }
        const telegramChatId = branchEditor.telegramChatId.trim();
        if (telegramChatId !== branchEditor.original.telegramChatId) {
            payload.telegram_chat_id = telegramChatId || null;
        }
        const knowledgeTag = branchEditor.knowledgeTag.trim();
        if (knowledgeTag !== branchEditor.original.knowledgeTag) {
            payload.knowledge_tag = knowledgeTag || null;
        }
        if (branchEditor.isActive !== branchEditor.original.isActive) {
            payload.is_active = branchEditor.isActive;
        }
        if (Object.keys(payload).length === 0) {
            toast("Нет изменений");
            return;
        }
        const confirmationNeeded = requiresBranchConfirmation(branchEditor);
        if (confirmationNeeded && !branchEditor.confirmReason.trim()) {
            toast.error("Укажите причину для подтверждения");
            return;
        }
        setSavingBranch(true);
        try {
            if (confirmationNeeded) {
                const confirmation = await confirmationsApi.create({
                    action: "branch_deactivate",
                    target_type: "branch",
                    target_id: branchEditor.id,
                    reason: branchEditor.confirmReason.trim(),
                });
                payload.confirmation_id = confirmation.data.confirmation_id;
            }
            await adminApi.patchBranch(branchEditor.id, payload);
            toast.success("Филиал обновлён");
            setBranchEditor(null);
            refreshTenants();
            refreshContext();
        } catch (error) {
            handleError(error);
        } finally {
            setSavingBranch(false);
        }
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
                            companies.map((company) => {
                                const isEditing = companyEditor?.id === company.id;
                                return (
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
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startCompanyEdit(company)}
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setCompanyContext(company.id)}
                                                disabled={company.id === selectedCompanyId}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && companyEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <label className="text-xs text-muted-foreground">
                                                        Название
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={companyEditor.name}
                                                            onChange={(event) =>
                                                                setCompanyEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, name: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingCompany}
                                                        />
                                                    </label>
                                                    <label className="text-xs text-muted-foreground">
                                                        billing_info (JSON, optional)
                                                        <textarea
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                                            rows={3}
                                                            value={companyEditor.billingInfo}
                                                            onChange={(event) =>
                                                                setCompanyEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, billingInfo: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingCompany}
                                                        />
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handleSaveCompany}
                                                            disabled={!canWriteTenants || savingCompany}
                                                        >
                                                            {savingCompany ? "Сохранение..." : "Сохранить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => setCompanyEditor(null)}
                                                            disabled={savingCompany}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
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
                            clients.map((client) => {
                                const isEditing = clientEditor?.id === client.id;
                                return (
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
                                            {client.status ? (
                                                <div className="text-xs text-muted-foreground">status: {client.status}</div>
                                            ) : null}
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <span>{client.id === selectedClientId ? "Выбран" : ""}</span>
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startClientEdit(client)}
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setClientContext(client.id, client.company_id)}
                                                disabled={client.id === selectedClientId}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && clientEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <label className="text-xs text-muted-foreground">
                                                        Slug
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={clientEditor.slug}
                                                            onChange={(event) =>
                                                                setClientEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, slug: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingClient}
                                                        />
                                                    </label>
                                                    <label className="text-xs text-muted-foreground">
                                                        Company ID (optional)
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={clientEditor.companyId}
                                                            onChange={(event) =>
                                                                setClientEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, companyId: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingClient}
                                                        />
                                                    </label>
                                                    <label className="text-xs text-muted-foreground">
                                                        Status (optional)
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={clientEditor.status}
                                                            onChange={(event) =>
                                                                setClientEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, status: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingClient}
                                                        />
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handleSaveClient}
                                                            disabled={!canWriteTenants || savingClient}
                                                        >
                                                            {savingClient ? "Сохранение..." : "Сохранить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => setClientEditor(null)}
                                                            disabled={savingClient}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
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
                            branches.map((branch) => {
                                const isEditing = branchEditor?.id === branch.id;
                                const confirmationNeeded = isEditing && branchEditor
                                    ? requiresBranchConfirmation(branchEditor)
                                    : false;
                                return (
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
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startBranchEdit(branch)}
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setBranchContext(branch.id)}
                                                disabled={branch.id === selectedBranchId}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && branchEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <div className="grid gap-3 sm:grid-cols-2">
                                                        <label className="text-xs text-muted-foreground">
                                                            Название
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.name}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, name: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Slug
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.slug}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, slug: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Timezone (optional)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.timezone}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, timezone: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Phone (optional)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.phone}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, phone: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            instance_id (optional)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.instanceId}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, instanceId: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            telegram_chat_id (optional)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.telegramChatId}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, telegramChatId: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            knowledge_tag (optional)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.knowledgeTag}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, knowledgeTag: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                    </div>
                                                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <input
                                                            type="checkbox"
                                                            className="h-4 w-4"
                                                            checked={branchEditor.isActive}
                                                            onChange={(event) =>
                                                                setBranchEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, isActive: event.target.checked }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingBranch}
                                                        />
                                                        Активен
                                                    </label>
                                                    {confirmationNeeded ? (
                                                        <label className="text-xs text-muted-foreground">
                                                            Причина подтверждения
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.confirmReason}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, confirmReason: event.target.value }
                                                                            : prev
                                                                )
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                    ) : null}
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handleSaveBranch}
                                                            disabled={!canWriteTenants || savingBranch}
                                                        >
                                                            {savingBranch ? "Сохранение..." : "Сохранить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => setBranchEditor(null)}
                                                            disabled={savingBranch}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
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
