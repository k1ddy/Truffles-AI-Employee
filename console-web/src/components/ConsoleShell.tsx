"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { usePathname } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";

import LoginButton from "@/components/LoginButton";
import { authApi } from "@/lib/api-client";

const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

type Role = "owner" | "admin" | "manager" | "support";

type ClientSummary = {
    id?: string;
    name?: string;
    company_id?: string | null;
};

type BranchSummary = {
    id?: string;
    name?: string;
};

type ConsoleMe = {
    agent?: { role?: Role | null };
    client?: ClientSummary | null;
    clients?: ClientSummary[];
    branches?: BranchSummary[];
    selection_required?: boolean;
    branch_selection_required?: boolean;
    selected_branch_id?: string | null;
};

type NavItem = {
    label: string;
    href: string;
    roles: Role[];
    testId: string;
};

const NAV_ITEMS: NavItem[] = [
    { label: "Заявки", href: "/", roles: ["owner", "admin", "manager", "support"], testId: "nav-cases" },
    { label: "Записи", href: "/calendar", roles: ["owner", "admin", "manager"], testId: "nav-calendar" },
    { label: "Знания", href: "/knowledge", roles: ["owner", "admin", "manager"], testId: "nav-knowledge" },
    { label: "Статус", href: "/ops", roles: ["owner", "admin", "support"], testId: "nav-ops" },
    { label: "Журнал", href: "/audit", roles: ["owner", "admin", "support"], testId: "nav-audit" },
    { label: "Настройки", href: "/settings", roles: ["owner", "admin"], testId: "nav-settings" },
];

const ROLE_LABELS: Record<Role, string> = {
    owner: "Owner",
    admin: "Admin",
    manager: "Manager",
    support: "Support",
};

function readLocalStorage(key: string): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    return window.localStorage.getItem(key);
}

function writeLocalStorage(key: string, value: string | null) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}

function formatCompanyLabel(client: ClientSummary | null | undefined): string {
    if (!client?.company_id) {
        return "—";
    }
    return client.company_id.slice(0, 8);
}

function findBranchName(branches: BranchSummary[] | undefined, branchId: string | null | undefined): string {
    if (!branchId || !branches?.length) {
        return "—";
    }
    const match = branches.find((branch) => branch.id === branchId);
    return match?.name ?? "—";
}

function SelectionGate({
    me,
    onConfirmClient,
    onConfirmBranch,
    isSubmitting,
}: {
    me: ConsoleMe;
    onConfirmClient: (clientId: string) => void;
    onConfirmBranch: (branchId: string) => void;
    isSubmitting: boolean;
}) {
    const [clientId, setClientId] = useState(() => me.client?.id ?? "");
    const [branchId, setBranchId] = useState(() => me.selected_branch_id ?? "");

    useEffect(() => {
        setClientId(me.client?.id ?? "");
    }, [me.client?.id]);

    useEffect(() => {
        setBranchId(me.selected_branch_id ?? "");
    }, [me.selected_branch_id]);

    if (me.selection_required) {
        return (
            <div className="card-surface p-8 max-w-xl">
                <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите клиента</h2>
                <p className="text-sm text-muted-foreground mb-6">
                    Доступно несколько клиентов. Выберите контекст, чтобы загрузить данные.
                </p>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={clientId}
                    onChange={(event) => setClientId(event.target.value)}
                    data-testid="client-select"
                >
                    <option value="">Выберите клиента</option>
                    {(me.clients ?? []).map((client) => (
                        <option key={client.id} value={client.id}>
                            {client.name ?? client.id}
                        </option>
                    ))}
                </select>
                <div className="mt-6 flex justify-end">
                    <button
                        className="btn-primary"
                        onClick={() => onConfirmClient(clientId)}
                        disabled={!clientId || isSubmitting}
                        data-testid="client-select-confirm"
                    >
                        Продолжить
                    </button>
                </div>
            </div>
        );
    }

    if (me.branch_selection_required) {
        return (
            <div className="card-surface p-8 max-w-xl">
                <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите филиал</h2>
                <p className="text-sm text-muted-foreground mb-6">
                    Для вашей роли нужен филиал. Выберите, чтобы продолжить работу.
                </p>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={branchId}
                    onChange={(event) => setBranchId(event.target.value)}
                    data-testid="branch-select"
                >
                    <option value="">Выберите филиал</option>
                    {(me.branches ?? []).map((branch) => (
                        <option key={branch.id} value={branch.id}>
                            {branch.name ?? branch.id}
                        </option>
                    ))}
                </select>
                <div className="mt-6 flex justify-end">
                    <button
                        className="btn-primary"
                        onClick={() => onConfirmBranch(branchId)}
                        disabled={!branchId || isSubmitting}
                        data-testid="branch-select-confirm"
                    >
                        Продолжить
                    </button>
                </div>
            </div>
        );
    }

    return null;
}

function ContextBar({
    me,
    onSelectClient,
    onSelectBranch,
}: {
    me: ConsoleMe;
    onSelectClient: (clientId: string) => void;
    onSelectBranch: (branchId: string | null) => void;
}) {
    const clients = me.clients ?? [];
    const branches = me.branches ?? [];
    const clientId = me.client?.id ?? "";
    const branchId = me.selected_branch_id ?? "";
    const allowAllBranches = !me.branch_selection_required;

    return (
        <div className="flex flex-wrap items-center gap-6 text-sm" data-testid="context-bar">
            <div className="flex flex-col gap-1 min-w-[140px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Company</span>
                <span className="text-sm font-semibold">{formatCompanyLabel(me.client ?? undefined)}</span>
            </div>
            <div className="flex flex-col gap-1 min-w-[180px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Client</span>
                {clients.length > 1 ? (
                    <select
                        className="rounded-lg border border-border bg-background px-2 py-1 text-sm"
                        value={clientId}
                        onChange={(event) => onSelectClient(event.target.value)}
                        data-testid="context-client-select"
                    >
                        {clients.map((client) => (
                            <option key={client.id} value={client.id}>
                                {client.name ?? client.id}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="text-sm font-semibold">{me.client?.name ?? "—"}</span>
                )}
            </div>
            <div className="flex flex-col gap-1 min-w-[180px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Branch</span>
                {branches.length > 1 ? (
                    <select
                        className="rounded-lg border border-border bg-background px-2 py-1 text-sm"
                        value={branchId}
                        onChange={(event) => onSelectBranch(event.target.value || null)}
                        data-testid="context-branch-select"
                    >
                        {allowAllBranches && <option value="">Все филиалы</option>}
                        {branches.map((branch) => (
                            <option key={branch.id} value={branch.id}>
                                {branch.name ?? branch.id}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="text-sm font-semibold">
                        {findBranchName(branches, branchId)}
                    </span>
                )}
            </div>
        </div>
    );
}

function PublicLanding() {
    return (
        <div className="min-h-screen bg-background">
            <header className="border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-3">
                        <Image
                            src="/brand/truffles-logo.png"
                            alt="Truffles"
                            width={140}
                            height={40}
                            className="h-7 w-auto"
                            priority
                        />
                        <span className="hidden text-xs uppercase tracking-[0.3em] text-muted-foreground sm:inline">
                            Truffles Console
                        </span>
                    </div>
                    <LoginButton />
                </div>
            </header>
            <main className="mx-auto flex max-w-3xl flex-col items-center px-6 py-20 text-center">
                <span className="badge mb-6">Control Plane</span>
                <h1 className="text-3xl font-semibold md:text-4xl">Панель управления AI‑ассистентом</h1>
                <p className="mt-4 text-base text-muted-foreground">
                    Войдите в систему, чтобы управлять заявками, расписанием и настройками.
                </p>
            </main>
        </div>
    );
}

export default function ConsoleShell({ children }: { children: React.ReactNode }) {
    const { status } = useSession();
    const pathname = usePathname();
    const hasSession = status === "authenticated";
    const queryClient = useQueryClient();

    const { data, isLoading, isFetching, error, refetch } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data as ConsoleMe;
        },
        enabled: hasSession,
    });

    const role = data?.agent?.role ?? "manager";
    const navItems = useMemo(
        () => NAV_ITEMS.filter((item) => item.roles.includes(role)),
        [role]
    );

    const [isSubmitting, setIsSubmitting] = useState(false);

    const selectionRequired = !!data?.selection_required;
    const branchSelectionRequired = !!data?.branch_selection_required;
    const showGate = selectionRequired || branchSelectionRequired;

    const handleSelectClient = async (clientId: string) => {
        if (!clientId) {
            return;
        }
        setIsSubmitting(true);
        writeLocalStorage(CLIENT_ID_STORAGE_KEY, clientId);
        writeLocalStorage(BRANCH_ID_STORAGE_KEY, null);
        await refetch();
        queryClient.invalidateQueries();
        setIsSubmitting(false);
    };

    const handleSelectBranch = async (branchId: string) => {
        if (!branchId) {
            return;
        }
        setIsSubmitting(true);
        writeLocalStorage(BRANCH_ID_STORAGE_KEY, branchId);
        await refetch();
        queryClient.invalidateQueries();
        setIsSubmitting(false);
    };

    const handleContextClientChange = async (clientId: string) => {
        if (!clientId || clientId === readLocalStorage(CLIENT_ID_STORAGE_KEY)) {
            return;
        }
        await handleSelectClient(clientId);
    };

    const handleContextBranchChange = async (branchId: string | null) => {
        const stored = readLocalStorage(BRANCH_ID_STORAGE_KEY);
        if (branchId === stored) {
            return;
        }
        setIsSubmitting(true);
        writeLocalStorage(BRANCH_ID_STORAGE_KEY, branchId);
        await refetch();
        queryClient.invalidateQueries();
        setIsSubmitting(false);
    };

    if (!hasSession && status !== "loading") {
        return <PublicLanding />;
    }

    return (
        <div className="min-h-screen bg-background">
            <div className="flex min-h-screen">
                <aside className="hidden w-64 flex-col border-r border-border/60 bg-card/40 px-4 py-6 md:flex">
                    <div className="flex items-center gap-3 px-2">
                        <Image
                            src="/brand/truffles-logo.png"
                            alt="Truffles"
                            width={120}
                            height={32}
                            className="h-6 w-auto"
                        />
                    </div>
                    <div className="mt-6 px-2 text-xs uppercase tracking-[0.3em] text-muted-foreground">
                        {ROLE_LABELS[role]}
                    </div>
                    <nav className="mt-6 flex flex-col gap-2 text-sm font-medium">
                        {navItems.map((item) => {
                            const isActive = item.href === "/"
                                ? pathname === "/"
                                : pathname.startsWith(item.href);
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`rounded-lg px-3 py-2 transition ${
                                        isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                                    }`}
                                    data-testid={item.testId}
                                >
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>
                </aside>
                <div className="flex flex-1 flex-col">
                    <header
                        className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur"
                        data-testid="console-header"
                    >
                        <div className="flex flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                            <div className="flex items-center gap-3 md:hidden">
                                <Image
                                    src="/brand/truffles-logo.png"
                                    alt="Truffles"
                                    width={120}
                                    height={32}
                                    className="h-6 w-auto"
                                />
                                <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                                    Truffles Console
                                </span>
                            </div>
                            {data && (
                                <ContextBar
                                    me={data}
                                    onSelectClient={handleContextClientChange}
                                    onSelectBranch={handleContextBranchChange}
                                />
                            )}
                            <div className="flex items-center justify-between gap-4">
                                <LoginButton />
                            </div>
                        </div>
                        <nav className="flex gap-2 overflow-x-auto px-6 pb-3 text-sm font-medium md:hidden">
                            {navItems.map((item) => {
                                const isActive = item.href === "/"
                                    ? pathname === "/"
                                    : pathname.startsWith(item.href);
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={`rounded-full px-4 py-2 transition ${
                                            isActive ? "bg-primary text-primary-foreground" : "bg-muted"
                                        }`}
                                        data-testid={`mobile-${item.testId}`}
                                    >
                                        {item.label}
                                    </Link>
                                );
                            })}
                        </nav>
                    </header>

                    <main className="flex-1 px-6 py-8">
                        <div className="mx-auto w-full max-w-6xl">
                            {status === "loading" && (
                                <div className="card-surface p-8">
                                    <p className="text-sm text-muted-foreground">Загрузка профиля...</p>
                                </div>
                            )}
                            {error && (
                                <div className="card-surface p-8">
                                    <p className="text-sm text-destructive">
                                        Не удалось загрузить данные профиля.
                                    </p>
                                    <button
                                        onClick={() => refetch()}
                                        className="btn-ghost mt-4"
                                        data-testid="me-retry"
                                    >
                                        Повторить
                                    </button>
                                </div>
                            )}
                            {!isLoading && !error && data && showGate && (
                                <div className="flex min-h-[320px] items-center justify-center">
                                    <SelectionGate
                                        me={data}
                                        onConfirmClient={handleSelectClient}
                                        onConfirmBranch={handleSelectBranch}
                                        isSubmitting={isSubmitting || isFetching}
                                    />
                                </div>
                            )}
                            {!isLoading && !error && data && !showGate && children}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}
