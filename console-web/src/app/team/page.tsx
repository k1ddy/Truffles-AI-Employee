"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

import api from "@/lib/api";
import { adminApi, agentsApi, authApi, canAccessConsole, type ConsoleRole } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";

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

type TeamBranch = { id?: string; name?: string };

type TeamClient = { id?: string; name?: string };

type TeamMe = {
    agent?: { role?: ConsoleRole | null };
    client?: TeamClient | null;
    branches?: TeamBranch[];
    selected_branch_id?: string | null;
};

type AgentRole = components["schemas"]["AgentCreateRequest"]["role"];
type MembershipScope = components["schemas"]["MembershipCreateRequest"]["scope"];
type AgentMembership = components["schemas"]["AgentMembership"];

const TEAM_AGENT_ROLES: AgentRole[] = [
    "platform_admin",
    "owner",
    "admin",
    "manager",
    "support",
    "specialist",
    "viewer",
];

const TEAM_MEMBERSHIP_SCOPES: MembershipScope[] = ["company", "client", "branch"];

const TEAM_TABS: Array<{ id: TeamTab; label: string; hint: string }> = [
    { id: "users", label: "Пользователи", hint: "роль/доступ" },
    { id: "specialists", label: "Специалисты", hint: "услуги/слоты" },
];

function RoleBadge({ role }: { role?: string | null }) {
    const styles: Record<string, string> = {
        platform_admin: "bg-amber-100 text-amber-800",
        owner: "bg-purple-100 text-purple-800",
        admin: "bg-secondary text-secondary-foreground",
        manager: "bg-green-100 text-green-800",
        support: "bg-muted text-muted-foreground",
        specialist: "bg-blue-100 text-blue-800",
        viewer: "bg-slate-100 text-slate-700",
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

function membershipTargetLabel(membership: AgentMembership, branches: TeamBranch[]) {
    if (membership.scope === "branch") {
        return formatBranchLabel(membership.branch_id, branches);
    }
    if (membership.scope === "client") {
        return membership.client_id ? membership.client_id.slice(0, 8) : "client: —";
    }
    return membership.company_id ? membership.company_id.slice(0, 8) : "company: —";
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
    clientId,
}: {
    session: SessionData;
    role: ConsoleRole;
    branches: TeamBranch[];
    clientId?: string | null;
}) {
    const { handleError } = useErrorHandler();
    const queryClient = useQueryClient();
    const canManage = canAccessConsole(role, "team", "write");
    const canReadTeam = canAccessConsole(role, "team", "read");
    const canViewProvisioning =
        canAccessConsole(role, "settings", "read") || canAccessConsole(role, "provisioning", "read");
    const [linkTokens, setLinkTokens] = useState<Record<string, TelegramLinkResponse>>({});
    const [linkTarget, setLinkTarget] = useState<string | null>(null);
    const [accessTarget, setAccessTarget] = useState<string | null>(null);
    const [oidcTarget, setOidcTarget] = useState<string | null>(null);
    const [membershipTarget, setMembershipTarget] = useState<string | null>(null);
    const [createAgentRole, setCreateAgentRole] = useState<AgentRole>("manager");
    const [createAgentBranchId, setCreateAgentBranchId] = useState("");
    const [createAgentName, setCreateAgentName] = useState("");
    const [createAgentOidcSubject, setCreateAgentOidcSubject] = useState("");
    const [createAgentIsActive, setCreateAgentIsActive] = useState(true);
    const [membershipAgentId, setMembershipAgentId] = useState("");
    const [membershipScope, setMembershipScope] = useState<MembershipScope>("client");
    const [membershipRole, setMembershipRole] = useState<AgentRole>("manager");
    const [membershipCompanyId, setMembershipCompanyId] = useState("");
    const [membershipClientId, setMembershipClientId] = useState(clientId ?? "");
    const [membershipBranchId, setMembershipBranchId] = useState("");
    const [membershipIsActive, setMembershipIsActive] = useState(true);
    const [membershipIncludeInactive, setMembershipIncludeInactive] = useState(false);
    const [membershipFilterAgentId, setMembershipFilterAgentId] = useState("");
    const [editingMembershipId, setEditingMembershipId] = useState<string | null>(null);
    const [editingRole, setEditingRole] = useState<AgentRole>("manager");
    const [editingScope, setEditingScope] = useState<MembershipScope>("client");
    const [editingCompanyId, setEditingCompanyId] = useState("");
    const [editingClientId, setEditingClientId] = useState(clientId ?? "");
    const [editingBranchId, setEditingBranchId] = useState("");
    const [editingIsActive, setEditingIsActive] = useState(true);
    const [editingReason, setEditingReason] = useState("");

    const agentsQuery = useQuery({
        queryKey: ["agents"],
        queryFn: async () => (await agentsApi.list()).data,
        enabled: !!session && canReadTeam,
    });

    const agents = useMemo(() => {
        return (agentsQuery.data?.items ?? []) as Array<AgentBase | AgentWithIdentities>;
    }, [agentsQuery.data]);

    useEffect(() => {
        setMembershipClientId(clientId ?? "");
        setEditingClientId(clientId ?? "");
    }, [clientId]);

    const membershipsQuery = useQuery({
        queryKey: ["team-memberships", membershipIncludeInactive, membershipFilterAgentId],
        queryFn: async () =>
            (
                await adminApi.listMemberships({
                    include_inactive: membershipIncludeInactive ? "true" : undefined,
                    agent_id: membershipFilterAgentId || undefined,
                })
            ).data,
        enabled: !!session && canReadTeam,
    });

    useEffect(() => {
        if (agentsQuery.error) {
            handleError(agentsQuery.error);
        }
    }, [agentsQuery.error, handleError]);

    useEffect(() => {
        if (membershipsQuery.error) {
            handleError(membershipsQuery.error);
        }
    }, [membershipsQuery.error, handleError]);

    const memberships = useMemo(() => {
        return (membershipsQuery.data?.items ?? []) as AgentMembership[];
    }, [membershipsQuery.data]);

    useEffect(() => {
        if (membershipCompanyId) {
            return;
        }
        const fallbackCompany = memberships.find((membership) => membership.company_id)?.company_id ?? "";
        if (fallbackCompany) {
            setMembershipCompanyId(fallbackCompany);
        }
    }, [memberships, membershipCompanyId]);

    const activeCount = agents.filter((agent) => agent.is_active).length;
    const owners = agents.filter((agent) => agent.role === "owner").length;
    const managers = agents.filter((agent) => agent.role === "manager").length;
    const membershipsActiveCount = memberships.filter((membership) => membership.is_active).length;

    const isBranchScopedRole = createAgentRole === "manager" || createAgentRole === "specialist";
    const canCreateAgent = canManage && Boolean(clientId);
    const agentBranchRequiredHint = isBranchScopedRole
        ? "Для роли manager/specialist нужно выбрать филиал."
        : "Филиал можно оставить пустым для client-level роли.";

    useEffect(() => {
        if (!isBranchScopedRole) {
            setCreateAgentBranchId("");
        }
    }, [isBranchScopedRole]);

    useEffect(() => {
        if (membershipScope === "client" && clientId && !membershipClientId) {
            setMembershipClientId(clientId);
        }
        if (membershipScope !== "branch") {
            setMembershipBranchId("");
        }
    }, [membershipScope, clientId, membershipClientId]);

    const createAgentMutation = useMutation({
        mutationFn: async () => {
            if (!clientId) {
                throw new Error("Выберите клиентский контекст в Tenants перед созданием учеток.");
            }
            const payload: components["schemas"]["AgentCreateRequest"] = {
                client_id: clientId,
                role: createAgentRole,
                name: createAgentName.trim() || undefined,
                branch_id: createAgentBranchId || undefined,
                oidc_subject: createAgentOidcSubject.trim() || undefined,
                is_active: createAgentIsActive,
            };
            return (await adminApi.createAgent(payload)).data;
        },
        onSuccess: () => {
            toast.success("Учетная запись создана");
            setCreateAgentName("");
            setCreateAgentOidcSubject("");
            setCreateAgentBranchId("");
            queryClient.invalidateQueries({ queryKey: ["agents"] });
            queryClient.invalidateQueries({ queryKey: ["team-memberships"] });
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const createMembershipMutation = useMutation({
        mutationFn: async () => {
            if (!membershipAgentId) {
                throw new Error("Выберите пользователя");
            }
            const payload: components["schemas"]["MembershipCreateRequest"] = {
                agent_id: membershipAgentId,
                scope: membershipScope,
                role: membershipRole,
                is_active: membershipIsActive,
            };
            if (membershipScope === "company") {
                if (!membershipCompanyId.trim()) {
                    throw new Error("Укажите company_id");
                }
                payload.company_id = membershipCompanyId.trim();
            }
            if (membershipScope === "client") {
                if (!membershipClientId.trim()) {
                    throw new Error("Укажите client_id");
                }
                payload.client_id = membershipClientId.trim();
            }
            if (membershipScope === "branch") {
                if (!membershipBranchId) {
                    throw new Error("Выберите филиал");
                }
                payload.branch_id = membershipBranchId;
            }
            return (await adminApi.createMembership(payload)).data;
        },
        onSuccess: () => {
            toast.success("Membership создан");
            queryClient.invalidateQueries({ queryKey: ["team-memberships"] });
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const patchMembershipMutation = useMutation({
        mutationFn: async (payload: { membershipId: string; data: components["schemas"]["MembershipUpdateRequest"] }) =>
            (await adminApi.patchMembership(payload.membershipId, payload.data)).data,
        onMutate: ({ membershipId }) => {
            setMembershipTarget(membershipId);
        },
        onSuccess: () => {
            toast.success("Membership обновлен");
            setEditingMembershipId(null);
            setEditingReason("");
            queryClient.invalidateQueries({ queryKey: ["team-memberships"] });
            queryClient.invalidateQueries({ queryKey: ["agents"] });
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setMembershipTarget(null);
        },
    });

    const startMembershipEdit = (membership: AgentMembership) => {
        setEditingMembershipId(membership.id);
        setEditingRole(membership.role);
        setEditingScope(membership.scope);
        setEditingCompanyId(membership.company_id ?? "");
        setEditingClientId(membership.client_id ?? clientId ?? "");
        setEditingBranchId(membership.branch_id ?? "");
        setEditingIsActive(Boolean(membership.is_active));
        setEditingReason("");
    };

    const saveMembershipEdit = (membership: AgentMembership) => {
        if (editingRole === "platform_admin" && role !== "platform_admin") {
            toast.error("Только platform_admin может назначать role=platform_admin");
            return;
        }
        const scopeChanged = editingScope !== membership.scope;
        const targetChanged = (
            editingCompanyId !== (membership.company_id ?? "") ||
            editingClientId !== (membership.client_id ?? "") ||
            editingBranchId !== (membership.branch_id ?? "")
        );
        const deactivating = membership.is_active && !editingIsActive;
        if ((scopeChanged || targetChanged || deactivating) && !editingReason.trim()) {
            toast.error("Укажите reason для rescope/disable");
            return;
        }
        const payload: components["schemas"]["MembershipUpdateRequest"] = {
            role: editingRole,
            scope: editingScope,
            is_active: editingIsActive,
            reason: editingReason.trim() || undefined,
            company_id: editingScope === "company" ? (editingCompanyId.trim() || null) : null,
            client_id: editingScope === "client" ? (editingClientId.trim() || null) : null,
            branch_id: editingScope === "branch" ? (editingBranchId || null) : null,
        };
        if (editingScope === "company" && !editingCompanyId.trim()) {
            toast.error("Укажите company_id");
            return;
        }
        if (editingScope === "client" && !editingClientId.trim()) {
            toast.error("Укажите client_id");
            return;
        }
        if (editingScope === "branch" && !editingBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        patchMembershipMutation.mutate({ membershipId: membership.id, data: payload });
    };

    const toggleMembershipActive = (membership: AgentMembership) => {
        const nextActive = !membership.is_active;
        const reason = window.prompt(nextActive ? "Причина включения membership" : "Причина отключения membership");
        if (!reason || !reason.trim()) {
            return;
        }
        patchMembershipMutation.mutate({
            membershipId: membership.id,
            data: {
                is_active: nextActive,
                reason: reason.trim(),
            },
        });
    };

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

    const accessMutation = useMutation({
        mutationFn: async (payload: { agentId: string; enable: boolean; reason: string }) => {
            if (payload.enable) {
                return (await adminApi.enableAgent(payload.agentId, { reason: payload.reason })).data;
            }
            return (await adminApi.disableAgent(payload.agentId, { reason: payload.reason })).data;
        },
        onMutate: ({ agentId }) => {
            setAccessTarget(agentId);
        },
        onSuccess: (_data, payload) => {
            toast.success(payload.enable ? "Доступ восстановлен" : "Доступ отключен");
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setAccessTarget(null);
            queryClient.invalidateQueries({ queryKey: ["agents"] });
        },
    });

    const oidcMutation = useMutation({
        mutationFn: async (payload: { agentId: string; oidcSubject: string; reason: string }) =>
            (await adminApi.rebindAgentOidc(payload.agentId, {
                oidc_subject: payload.oidcSubject,
                reason: payload.reason,
            })).data,
        onMutate: ({ agentId }) => {
            setOidcTarget(agentId);
        },
        onSuccess: () => {
            toast.success("OIDC привязка обновлена");
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setOidcTarget(null);
            queryClient.invalidateQueries({ queryKey: ["agents"] });
        },
    });

    const handleToggleAccess = (agentId: string, isActive: boolean) => {
        const reason = window.prompt(isActive ? "Причина отключения доступа" : "Причина включения доступа");
        if (!reason || !reason.trim()) {
            return;
        }
        accessMutation.mutate({
            agentId,
            enable: !isActive,
            reason: reason.trim(),
        });
    };

    const handleRebindOidc = (agentId: string) => {
        const oidcSubject = window.prompt("Новый oidc_subject");
        if (!oidcSubject || !oidcSubject.trim()) {
            return;
        }
        const reason = window.prompt("Причина изменения OIDC привязки");
        if (!reason || !reason.trim()) {
            return;
        }
        oidcMutation.mutate({
            agentId,
            oidcSubject: oidcSubject.trim(),
            reason: reason.trim(),
        });
    };

    const handleCreateAgent = () => {
        if (!clientId) {
            toast.error("Выберите клиент в Tenants, затем вернитесь в Team");
            return;
        }
        if (createAgentRole === "platform_admin" && role !== "platform_admin") {
            toast.error("Только platform_admin может создавать platform_admin учетку");
            return;
        }
        if (isBranchScopedRole && !createAgentBranchId) {
            toast.error("Для manager/specialist выберите филиал");
            return;
        }
        createAgentMutation.mutate();
    };

    const handleCreateMembership = () => {
        if (!membershipAgentId) {
            toast.error("Выберите пользователя");
            return;
        }
        if (membershipRole === "platform_admin" && role !== "platform_admin") {
            toast.error("Только platform_admin может назначать role=platform_admin");
            return;
        }
        createMembershipMutation.mutate();
    };

    return (
        <div className="space-y-6">
            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-semibold">Пользователи</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            Управление ролями и доступом. Telegram linking доступен только owner/admin/platform admin.
                        </p>
                    </div>
                    {canViewProvisioning ? (
                        <Link className="btn-ghost" href="/settings">
                            Открыть provisioning
                        </Link>
                    ) : (
                        <span className="text-xs text-muted-foreground">
                            Только owner/admin/platform admin может управлять пользователями.
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

            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold">Создать учетную запись</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Быстрый выпуск owner/admin/manager/support/specialist/viewer для текущего клиента.
                        </p>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        client: {clientId ? <span className="font-mono">{clientId.slice(0, 8)}</span> : "не выбран"}
                    </div>
                </div>
                {!clientId ? (
                    <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        Нет клиентского контекста. Выберите клиент в Tenants (`В контекст`), затем обновите Team.
                    </div>
                ) : null}
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={createAgentRole}
                        onChange={(event) => setCreateAgentRole(event.target.value as AgentRole)}
                        disabled={!canCreateAgent}
                    >
                        {TEAM_AGENT_ROLES.map((roleValue) => (
                            <option key={roleValue} value={roleValue}>{roleValue}</option>
                        ))}
                    </select>
                    <input
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Имя"
                        value={createAgentName}
                        onChange={(event) => setCreateAgentName(event.target.value)}
                        disabled={!canCreateAgent}
                    />
                    <input
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="oidc_subject (optional)"
                        value={createAgentOidcSubject}
                        onChange={(event) => setCreateAgentOidcSubject(event.target.value)}
                        disabled={!canCreateAgent}
                    />
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={createAgentBranchId}
                        onChange={(event) => setCreateAgentBranchId(event.target.value)}
                        disabled={!canCreateAgent || !isBranchScopedRole}
                    >
                        <option value="">{isBranchScopedRole ? "Выберите филиал" : "Client scope"}</option>
                        {branches.map((branch) => (
                            <option key={branch.id} value={branch.id}>
                                {branch.name ?? branch.id}
                            </option>
                        ))}
                    </select>
                    <label className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm">
                        <input
                            type="checkbox"
                            checked={createAgentIsActive}
                            onChange={(event) => setCreateAgentIsActive(event.target.checked)}
                            disabled={!canCreateAgent}
                        />
                        active
                    </label>
                    <button
                        type="button"
                        className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={handleCreateAgent}
                        disabled={!canCreateAgent || createAgentMutation.isPending}
                    >
                        {createAgentMutation.isPending ? "Создание..." : "Создать"}
                    </button>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{agentBranchRequiredHint}</p>
            </div>

            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold">Memberships</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Управление scope/role/active для доступов компании, клиента и филиалов.
                        </p>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        total: {memberships.length} · active: {membershipsActiveCount}
                    </div>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={membershipFilterAgentId}
                        onChange={(event) => setMembershipFilterAgentId(event.target.value)}
                    >
                        <option value="">Все пользователи</option>
                        {agents
                            .filter((agent) => Boolean(agent.id))
                            .map((agent, index) => (
                                <option key={agent.id ?? `agent-filter-${index}`} value={agent.id}>
                                    {(agent.name || "Без имени")} · {agent.role}
                                </option>
                            ))}
                    </select>
                    <label className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm">
                        <input
                            type="checkbox"
                            checked={membershipIncludeInactive}
                            onChange={(event) => setMembershipIncludeInactive(event.target.checked)}
                        />
                        include inactive
                    </label>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-7">
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={membershipAgentId}
                        onChange={(event) => setMembershipAgentId(event.target.value)}
                        disabled={!canManage}
                    >
                        <option value="">Выберите пользователя</option>
                        {agents
                            .filter((agent) => Boolean(agent.id))
                            .map((agent, index) => (
                                <option key={agent.id ?? `agent-create-${index}`} value={agent.id}>
                                    {(agent.name || "Без имени")} · {agent.role}
                                </option>
                            ))}
                    </select>
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={membershipScope}
                        onChange={(event) => setMembershipScope(event.target.value as MembershipScope)}
                        disabled={!canManage}
                    >
                        {TEAM_MEMBERSHIP_SCOPES.map((scopeValue) => (
                            <option key={scopeValue} value={scopeValue}>{scopeValue}</option>
                        ))}
                    </select>
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={membershipRole}
                        onChange={(event) => setMembershipRole(event.target.value as AgentRole)}
                        disabled={!canManage}
                    >
                        {TEAM_AGENT_ROLES.map((roleValue) => (
                            <option key={roleValue} value={roleValue}>{roleValue}</option>
                        ))}
                    </select>
                    {membershipScope === "company" && (
                        <input
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="company_id"
                            value={membershipCompanyId}
                            onChange={(event) => setMembershipCompanyId(event.target.value)}
                            disabled={!canManage}
                        />
                    )}
                    {membershipScope === "client" && (
                        <input
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="client_id"
                            value={membershipClientId}
                            onChange={(event) => setMembershipClientId(event.target.value)}
                            disabled={!canManage}
                        />
                    )}
                    {membershipScope === "branch" && (
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={membershipBranchId}
                            onChange={(event) => setMembershipBranchId(event.target.value)}
                            disabled={!canManage}
                        >
                            <option value="">Выберите филиал</option>
                            {branches.map((branch) => (
                                <option key={branch.id} value={branch.id}>
                                    {branch.name ?? branch.id}
                                </option>
                            ))}
                        </select>
                    )}
                    <label className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm">
                        <input
                            type="checkbox"
                            checked={membershipIsActive}
                            onChange={(event) => setMembershipIsActive(event.target.checked)}
                            disabled={!canManage}
                        />
                        active
                    </label>
                    <button
                        type="button"
                        className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={handleCreateMembership}
                        disabled={!canManage || createMembershipMutation.isPending}
                    >
                        {createMembershipMutation.isPending ? "Сохранение..." : "Добавить membership"}
                    </button>
                </div>

                <div className="mt-4 space-y-2">
                    {membershipsQuery.isLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка memberships...</div>
                    ) : memberships.length === 0 ? (
                        <div className="text-sm text-muted-foreground">Memberships не найдены.</div>
                    ) : (
                        memberships.map((membership) => {
                            const isEditing = editingMembershipId === membership.id;
                            const rowLoading = membershipTarget === membership.id;
                            return (
                                <div key={membership.id} className="rounded-lg border border-border/60 px-3 py-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-sm">
                                            <span className="font-medium">{membership.agent_name ?? membership.agent_id.slice(0, 8)}</span>
                                            <span className="text-muted-foreground"> · {membershipTargetLabel(membership, branches)}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <RoleBadge role={membership.role} />
                                            <span className={`text-xs ${membership.is_active ? "text-green-700" : "text-muted-foreground"}`}>
                                                {membership.is_active ? "active" : "inactive"}
                                            </span>
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => toggleMembershipActive(membership)}
                                                    disabled={rowLoading}
                                                >
                                                    {rowLoading ? "..." : membership.is_active ? "Disable" : "Enable"}
                                                </button>
                                            ) : null}
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => startMembershipEdit(membership)}
                                                    disabled={rowLoading}
                                                >
                                                    Edit
                                                </button>
                                            ) : null}
                                        </div>
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        scope={membership.scope} · company={membership.company_id ?? "—"} · client={membership.client_id ?? "—"} · branch={membership.branch_id ?? "—"}
                                    </div>
                                    {isEditing && canManage ? (
                                        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-6">
                                            <select
                                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={editingRole}
                                                onChange={(event) => setEditingRole(event.target.value as AgentRole)}
                                            >
                                                {TEAM_AGENT_ROLES.map((roleValue) => (
                                                    <option key={roleValue} value={roleValue}>{roleValue}</option>
                                                ))}
                                            </select>
                                            <select
                                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={editingScope}
                                                onChange={(event) => setEditingScope(event.target.value as MembershipScope)}
                                            >
                                                {TEAM_MEMBERSHIP_SCOPES.map((scopeValue) => (
                                                    <option key={scopeValue} value={scopeValue}>{scopeValue}</option>
                                                ))}
                                            </select>
                                            {editingScope === "company" && (
                                                <input
                                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    placeholder="company_id"
                                                    value={editingCompanyId}
                                                    onChange={(event) => setEditingCompanyId(event.target.value)}
                                                />
                                            )}
                                            {editingScope === "client" && (
                                                <input
                                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    placeholder="client_id"
                                                    value={editingClientId}
                                                    onChange={(event) => setEditingClientId(event.target.value)}
                                                />
                                            )}
                                            {editingScope === "branch" && (
                                                <select
                                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={editingBranchId}
                                                    onChange={(event) => setEditingBranchId(event.target.value)}
                                                >
                                                    <option value="">Выберите филиал</option>
                                                    {branches.map((branch) => (
                                                        <option key={branch.id} value={branch.id}>
                                                            {branch.name ?? branch.id}
                                                        </option>
                                                    ))}
                                                </select>
                                            )}
                                            <label className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm">
                                                <input
                                                    type="checkbox"
                                                    checked={editingIsActive}
                                                    onChange={(event) => setEditingIsActive(event.target.checked)}
                                                />
                                                active
                                            </label>
                                            <input
                                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                placeholder="reason (обязательно для rescope/disable)"
                                                value={editingReason}
                                                onChange={(event) => setEditingReason(event.target.value)}
                                            />
                                            <div className="flex items-center gap-2">
                                                <button
                                                    type="button"
                                                    className="btn-primary"
                                                    onClick={() => saveMembershipEdit(membership)}
                                                    disabled={rowLoading}
                                                >
                                                    Сохранить
                                                </button>
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => setEditingMembershipId(null)}
                                                    disabled={rowLoading}
                                                >
                                                    Отмена
                                                </button>
                                            </div>
                                        </div>
                                    ) : null}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {agentsQuery.isLoading && (
                    <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
                        Загрузка команды...
                    </div>
                )}
                {!agentsQuery.isLoading && agentsQuery.error && (
                    <div className="card-surface p-6 text-sm text-destructive">
                        Не удалось загрузить команду.
                        <button
                            type="button"
                            className="btn-ghost mt-3"
                            onClick={() => {
                                agentsQuery.refetch();
                            }}
                        >
                            Повторить
                        </button>
                    </div>
                )}
                {!agentsQuery.isLoading && agents.length === 0 && (
                    <div className="card-surface p-6 text-sm text-muted-foreground">
                        Нет участников команды.
                    </div>
                )}
                {!agentsQuery.isLoading && agents.length > 0 && agents.map((agent, index) => {
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
                                        <span className="text-muted-foreground">только owner/admin/platform admin</span>
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
                                {canManage && agent.id && (
                                    <div className="mt-2 flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                            onClick={() => handleToggleAccess(agent.id as string, Boolean(agent.is_active))}
                                            disabled={accessTarget === agent.id}
                                        >
                                            {accessTarget === agent.id
                                                ? "Сохранение..."
                                                : agent.is_active
                                                    ? "Отключить доступ"
                                                    : "Включить доступ"}
                                        </button>
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                            onClick={() => handleRebindOidc(agent.id as string)}
                                            disabled={oidcTarget === agent.id}
                                        >
                                            {oidcTarget === agent.id ? "Сохранение..." : "OIDC rebind"}
                                        </button>
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
                                            Истекает:{" "}
                                            {linkData.expires_at
                                                ? new Date(linkData.expires_at).toLocaleString("ru-RU")
                                                : "—"}
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
    role: ConsoleRole;
    selectedBranchId: string;
    onSelectBranch: (value: string) => void;
}) {
    const { handleError } = useErrorHandler();
    const canWriteTeam = canAccessConsole(role, "team", "write");

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
                            {canWriteTeam ? "Owner/Admin/Platform" : "Read-only"}
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
    const role = (meQuery.data?.agent?.role ?? "manager") as ConsoleRole;
    const canReadTeam = canAccessConsole(role, "team", "read");

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

    if (meQuery.isLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canReadTeam) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к команде." />
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
                    {canAccessConsole(role, "knowledge", "read") && (
                        <Link className="btn-ghost" href="/knowledge">
                            Knowledge Studio
                        </Link>
                    )}
                    {(canAccessConsole(role, "settings", "read") || canAccessConsole(role, "provisioning", "read")) && (
                        <Link className="btn-primary" href="/settings">
                            Provisioning
                        </Link>
                    )}
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
                <UsersPanel
                    session={session}
                    role={role}
                    branches={branches}
                    clientId={meQuery.data?.client?.id ?? null}
                />
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
