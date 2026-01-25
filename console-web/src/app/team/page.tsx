"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

import api from "@/lib/api";
import { agentsApi, authApi, settingsApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import type { components } from "@/types/api.generated";

type SessionData = ReturnType<typeof useSession>["data"];

type AgentBase = components["schemas"]["Agent"];
type AgentWithIdentities = components["schemas"]["AgentWithIdentities"];
type AgentIdentity = components["schemas"]["AgentIdentity"];
type TelegramLinkResponse = components["schemas"]["TelegramLinkResponse"];

type Specialist = {
    id: string;
    name: string;
    branch_id?: string | null;
    branch_name?: string | null;
    services?: Array<{ name: string; duration_min?: number; price?: number }>;
    is_active?: boolean;
};

type SpecialistsResponse = {
    items: Specialist[];
};

type TeamTab = "users" | "specialists";

type Role = "owner" | "admin" | "manager" | "support";

type TeamBranch = { id?: string; name?: string };

type TeamClient = { id?: string; name?: string };

type TeamMe = {
    agent?: { role?: Role | null };
    client?: TeamClient | null;
    branches?: TeamBranch[];
    selected_branch_id?: string | null;
};

const TEAM_TABS: Array<{ id: TeamTab; label: string; hint: string }> = [
    { id: "users", label: "Пользователи", hint: "роль/доступ" },
    { id: "specialists", label: "Специалисты", hint: "услуги/слоты" },
];

function RoleBadge({ role }: { role?: string | null }) {
    const styles: Record<string, string> = {
        owner: "bg-purple-100 text-purple-800",
        admin: "bg-secondary text-secondary-foreground",
        manager: "bg-green-100 text-green-800",
        support: "bg-muted text-muted-foreground",
    };
    const label = role ?? "—";
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[label] || "bg-muted text-muted-foreground"}`}>
            {label}
        </span>
    );
}

function formatBranchLabel(branchId: string | null | undefined, branches: TeamBranch[]) {
    if (!branchId) {
        return "Все филиалы";
    }
    const match = branches.find((branch) => branch.id === branchId);
    return match?.name ?? branchId.slice(0, 8);
}

function resolveTelegramIdentity(agent: AgentBase | AgentWithIdentities): AgentIdentity | undefined {
    if (!("identities" in agent)) {
        return undefined;
    }
    return agent.identities?.find((identity) => identity.channel === "telegram");
}

async function fetchSpecialists(branchId?: string): Promise<SpecialistsResponse> {
    const params = branchId ? `?branch_id=${branchId}` : "";
    const response = await api.get(`/calendar/specialists${params}`);
    const data = response.data || {};
    return { items: (data.items || []) as Specialist[] };
}

function UsersPanel({
    session,
    role,
    branches,
}: {
    session: SessionData;
    role: Role;
    branches: TeamBranch[];
}) {
    const { handleError } = useErrorHandler();
    const queryClient = useQueryClient();
    const canManage = role === "owner" || role === "admin";
    const [linkTokens, setLinkTokens] = useState<Record<string, TelegramLinkResponse>>({});
    const [linkTarget, setLinkTarget] = useState<string | null>(null);

    const settingsQuery = useQuery({
        queryKey: ["settings"],
        queryFn: async () => (await settingsApi.get()).data,
        enabled: !!session,
    });

    const agentsQuery = useQuery({
        queryKey: ["agents"],
        queryFn: async () => (await agentsApi.list()).data,
        enabled: !!session && canManage,
    });

    const agents = useMemo(() => {
        if (canManage) {
            return (agentsQuery.data?.items ?? []) as Array<AgentBase | AgentWithIdentities>;
        }
        return (settingsQuery.data?.agents ?? []) as Array<AgentBase | AgentWithIdentities>;
    }, [canManage, agentsQuery.data, settingsQuery.data]);

    const activeCount = agents.filter((agent) => agent.is_active).length;
    const owners = agents.filter((agent) => agent.role === "owner").length;
    const managers = agents.filter((agent) => agent.role === "manager").length;

    const linkMutation = useMutation({
        mutationFn: async (agentId: string) => (await agentsApi.linkTelegram(agentId)).data,
        onMutate: (agentId) => {
            setLinkTarget(agentId);
        },
        onSuccess: (data, agentId) => {
            setLinkTokens((prev) => ({ ...prev, [agentId]: data }));
            toast.success("Ссылка для Telegram создана");
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setLinkTarget(null);
            queryClient.invalidateQueries({ queryKey: ["agents"] });
        },
    });

    return (
        <div className="space-y-6">
            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-semibold">Пользователи</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            Управление ролями и доступом. Telegram linking доступен только owner/admin.
                        </p>
                    </div>
                    {canManage ? (
                        <Link className="btn-ghost" href="/settings">
                            Открыть provisioning
                        </Link>
                    ) : (
                        <span className="text-xs text-muted-foreground">
                            Только owner/admin может управлять пользователями.
                        </span>
                    )}
                </div>
                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Всего</p>
                        <p className="text-2xl font-semibold mt-2">{agents.length}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Активных</p>
                        <p className="text-2xl font-semibold mt-2">{activeCount}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Owner/Manager</p>
                        <p className="text-2xl font-semibold mt-2">{owners} / {managers}</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {(settingsQuery.isLoading || agentsQuery.isLoading) && (
                    <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
                        Загрузка команды...
                    </div>
                )}
                {(!settingsQuery.isLoading && (settingsQuery.error || agentsQuery.error)) && (
                    <div className="card-surface p-6 text-sm text-destructive">
                        Не удалось загрузить команду.
                        <button
                            type="button"
                            className="btn-ghost mt-3"
                            onClick={() => {
                                settingsQuery.refetch();
                                agentsQuery.refetch();
                            }}
                        >
                            Повторить
                        </button>
                    </div>
                )}
                {!settingsQuery.isLoading && agents.length === 0 && (
                    <div className="card-surface p-6 text-sm text-muted-foreground">
                        Нет участников команды.
                    </div>
                )}
                {!settingsQuery.isLoading && agents.length > 0 && agents.map((agent, index) => {
                    const identity = resolveTelegramIdentity(agent);
                    const linkData = agent.id ? linkTokens[agent.id] : undefined;
                    const displayHandle = identity?.username ? `@${identity.username}` : identity?.external_id;
                    const agentBranchLabel = formatBranchLabel(agent.branch_id ?? null, branches);
                    const agentKey = agent.id ?? `agent-${index}`;

                    return (
                        <div key={agentKey} className="card-surface p-5">
                            <div className="flex items-start justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">{agentBranchLabel}</p>
                                    <p className="text-lg font-semibold mt-1">{agent.name || "Без имени"}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <RoleBadge role={agent.role} />
                                    <span
                                        className={`h-2 w-2 rounded-full ${agent.is_active ? "bg-green-500" : "bg-muted"}`}
                                    ></span>
                                </div>
                            </div>

                            <div className="mt-4 text-sm">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted-foreground">Telegram</span>
                                    {canManage ? (
                                        <span className={identity ? "font-medium" : "text-muted-foreground"}>
                                            {identity ? displayHandle : "не подключен"}
                                        </span>
                                    ) : (
                                        <span className="text-muted-foreground">только owner/admin</span>
                                    )}
                                </div>
                                {canManage && agent.id && (
                                    <div className="mt-3 flex items-center justify-between gap-2">
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                            onClick={() => linkMutation.mutate(agent.id as string)}
                                            disabled={linkTarget === agent.id}
                                        >
                                            {linkTarget === agent.id
                                                ? "Генерация..."
                                                : identity
                                                    ? "Переподключить"
                                                    : "Подключить Telegram"}
                                        </button>
                                        {identity?.linked_at && (
                                            <span className="text-xs text-muted-foreground">
                                                {new Date(identity.linked_at).toLocaleDateString("ru-RU")}
                                            </span>
                                        )}
                                    </div>
                                )}
                                {linkData && (
                                    <div className="mt-3 rounded-lg border border-border/60 bg-background p-3 text-xs">
                                        <div>
                                            Код: <span className="font-mono">{linkData.token}</span>
                                        </div>
                                        {linkData.deep_link && (
                                            <Link className="text-primary underline" href={linkData.deep_link} target="_blank">
                                                Открыть в Telegram
                                            </Link>
                                        )}
                                        <div className="text-muted-foreground">
                                            Отправьте боту <span className="font-mono">/start {linkData.token}</span>
                                        </div>
                                        <div className="text-muted-foreground">
                                            Истекает: {new Date(linkData.expires_at).toLocaleString("ru-RU")}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function SpecialistsPanel({
    session,
    branches,
    role,
    selectedBranchId,
    onSelectBranch,
}: {
    session: SessionData;
    branches: TeamBranch[];
    role: Role;
    selectedBranchId: string;
    onSelectBranch: (value: string) => void;
}) {
    const { handleError } = useErrorHandler();

    const specialistsQuery = useQuery({
        queryKey: ["calendar-specialists", selectedBranchId],
        queryFn: () => fetchSpecialists(selectedBranchId || undefined),
        enabled: !!session,
    });

    useEffect(() => {
        if (specialistsQuery.error) {
            handleError(specialistsQuery.error);
        }
    }, [specialistsQuery.error, handleError]);

    const specialists = specialistsQuery.data?.items ?? [];
    const totalServices = specialists.reduce((total, specialist) => total + (specialist.services?.length ?? 0), 0);

    return (
        <div className="space-y-6">
            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-semibold">Специалисты</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            Услуги подтягиваются из Knowledge. Обновление каталога — через Knowledge Studio.
                        </p>
                    </div>
                    {branches.length > 1 && (
                        <select
                            className="rounded-full border border-border/60 bg-background px-4 py-2 text-sm"
                            value={selectedBranchId}
                            onChange={(event) => onSelectBranch(event.target.value)}
                        >
                            <option value="">Все филиалы</option>
                            {branches.map((branch) => (
                                <option key={branch.id} value={branch.id}>
                                    {branch.name ?? branch.id}
                                </option>
                            ))}
                        </select>
                    )}
                </div>
                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Специалисты</p>
                        <p className="text-2xl font-semibold mt-2">{specialists.length}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Услуги</p>
                        <p className="text-2xl font-semibold mt-2">{totalServices}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Доступ</p>
                        <p className="text-sm text-muted-foreground mt-2">
                            {role === "manager" ? "Read-only" : "Owner/Admin"}
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {specialistsQuery.isLoading && (
                    <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
                        Загрузка специалистов...
                    </div>
                )}
                {!specialistsQuery.isLoading && specialists.length === 0 && (
                    <div className="card-surface p-6 text-sm text-muted-foreground">
                        Специалисты не найдены. Добавьте их через provisioning.
                    </div>
                )}
                {!specialistsQuery.isLoading && specialists.map((specialist) => (
                    <div key={specialist.id} className="card-surface p-5">
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">
                                    {specialist.branch_name ?? formatBranchLabel(specialist.branch_id ?? null, branches)}
                                </p>
                                <p className="text-lg font-semibold mt-1">{specialist.name}</p>
                            </div>
                            <span
                                className={`px-2 py-1 rounded text-xs font-medium ${specialist.is_active
                                    ? "bg-green-100 text-green-800"
                                    : "bg-muted text-muted-foreground"}`}
                            >
                                {specialist.is_active ? "Активен" : "Неактивен"}
                            </span>
                        </div>
                        <div className="mt-4 text-xs text-muted-foreground">Услуги</div>
                        <div className="mt-2 space-y-2">
                            {(specialist.services ?? []).length === 0 && (
                                <p className="text-sm text-muted-foreground">Нет услуг</p>
                            )}
                            {(specialist.services ?? []).map((service, index) => {
                                const price = service.price != null ? `${service.price} ₸` : "—";
                                const duration = service.duration_min != null ? `${service.duration_min} мин` : "—";
                                return (
                                    <div
                                        key={`${specialist.id}-service-${index}`}
                                        className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-sm"
                                    >
                                        <div className="font-medium">{service.name}</div>
                                        <div className="text-xs text-muted-foreground">{duration} • {price}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default function TeamPage() {
    const { data: session } = useSession();
    const [activeTab, setActiveTab] = useState<TeamTab>(TEAM_TABS[0].id);
    const [selectedBranchId, setSelectedBranchId] = useState("");

    const meQuery = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => (await authApi.getMe()).data as TeamMe,
        enabled: !!session,
    });

    const branches = (meQuery.data?.branches ?? []) as TeamBranch[];
    const role = (meQuery.data?.agent?.role ?? "manager") as Role;

    useEffect(() => {
        if (!selectedBranchId && role === "manager" && meQuery.data?.selected_branch_id) {
            setSelectedBranchId(meQuery.data.selected_branch_id);
        }
    }, [role, meQuery.data?.selected_branch_id, selectedBranchId]);

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра команды.
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="team-page">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="badge mb-3">Team</div>
                    <h1 className="text-2xl font-semibold">Команда и специалисты</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Управляйте пользователями и следите за специалистами в календаре.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Link className="btn-ghost" href="/knowledge">
                        Knowledge Studio
                    </Link>
                    <Link className="btn-primary" href="/settings">
                        Provisioning
                    </Link>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                {TEAM_TABS.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                            activeTab === tab.id
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground"
                        }`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        {tab.label}
                        <span className="ml-2 text-xs opacity-70">{tab.hint}</span>
                    </button>
                ))}
            </div>

            {activeTab === "users" ? (
                <UsersPanel session={session} role={role} branches={branches} />
            ) : (
                <SpecialistsPanel
                    session={session}
                    branches={branches}
                    role={role}
                    selectedBranchId={selectedBranchId}
                    onSelectBranch={setSelectedBranchId}
                />
            )}
        </div>
    );
}
