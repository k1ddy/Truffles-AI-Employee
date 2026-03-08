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

type AgentBase = components["schemas"]["ConsoleAgent"];
type AgentWithIdentities = components["schemas"]["ConsoleAgentWithIdentities"];
type AgentIdentity = components["schemas"]["ConsoleAgentIdentity"];
type TelegramLinkResponse = components["schemas"]["ConsoleTelegramLinkResponse"];

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

type TeamClient = {
    id?: string;
    name?: string;
    company_id?: string | null;
    company_name?: string | null;
};
type TeamCompany = { id?: string; name?: string };

type TeamMe = {
    agent?: { id?: string | null; role?: ConsoleRole | null };
    client?: TeamClient | null;
    branches?: TeamBranch[];
    clients?: TeamClient[];
    companies?: TeamCompany[];
    selected_company_id?: string | null;
    selected_branch_id?: string | null;
};

type AgentRole = components["schemas"]["ConsoleAgentCreateRequest"]["role"];
type MembershipScope = components["schemas"]["ConsoleMembershipCreateRequest"]["scope"];
type AgentMembership = components["schemas"]["ConsoleAgentMembership"];
type RoutingProfile = components["schemas"]["ConsoleRoutingProfile"];
type RoutingProfileScope = RoutingProfile["scope"];
type RoutingProfileStatus = RoutingProfile["routing_status"];

const TEAM_AGENT_ROLES: AgentRole[] = [
    "platform_admin",
    "owner",
    "admin",
    "manager",
    "support",
    "specialist",
    "viewer",
];
const TEAM_ASSIGNABLE_AGENT_ROLES: AgentRole[] = ["owner", "admin", "manager", "viewer"];

const TEAM_MEMBERSHIP_SCOPES: MembershipScope[] = ["company", "client", "branch"];
const TEAM_ROUTING_PROFILE_SCOPES: RoutingProfileScope[] = ["client", "branch"];
const TEAM_ROUTING_PROFILE_STATUSES: RoutingProfileStatus[] = ["available", "paused", "follow_up_only"];

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

function membershipTargetLabel(
    membership: AgentMembership,
    branches: TeamBranch[],
    clientsById: Map<string, TeamClient>,
    companiesById: Map<string, TeamCompany>,
) {
    if (membership.scope === "branch") {
        return formatBranchLabel(membership.branch_id, branches);
    }
    if (membership.scope === "client") {
        if (!membership.client_id) {
            return "client: —";
        }
        return clientsById.get(membership.client_id)?.name ?? membership.client_id.slice(0, 8);
    }
    if (!membership.company_id) {
        return "company: —";
    }
    return companiesById.get(membership.company_id)?.name ?? membership.company_id.slice(0, 8);
}

function buildRoutingProfileKey(agentId: string, branchId?: string | null) {
    return `${agentId}:${branchId || "client"}`;
}

function formatRoutingProfileScopeLabel(profile: RoutingProfile, branches: TeamBranch[]) {
    if (profile.scope === "branch") {
        return `Филиал: ${formatBranchLabel(profile.branch_id, branches)}`;
    }
    return "Клиент по умолчанию";
}

function formatRoutingProfileStatusLabel(status: RoutingProfileStatus) {
    if (status === "paused") {
        return "Пауза";
    }
    if (status === "follow_up_only") {
        return "Только follow-up";
    }
    return "Доступен";
}

async function fetchSpecialists(branchId?: string): Promise<SpecialistsResponse> {
    const params = new URLSearchParams();
    if (branchId) {
        params.set("branch_id", branchId);
    }
    const query = params.toString();
    const response = await api.get(`/calendar/specialists${query ? `?${query}` : ""}`);
    const data = response.data || {};
    return { items: (data.items || []) as Specialist[] };
}

async function fetchSpecialistsAdmin(branchId?: string): Promise<SpecialistsResponse> {
    const params = new URLSearchParams();
    if (branchId) {
        params.set("branch_id", branchId);
    }
    params.set("include_inactive", "true");
    const response = await api.get(`/calendar/specialists?${params.toString()}`);
    const data = response.data || {};
    return { items: (data.items || []) as Specialist[] };
}

type SpecialistMutationPayload = {
    name: string;
    branch_id?: string;
    services?: Array<{ name: string; duration_min?: number; price?: number }>;
};

type SpecialistServiceDraft = {
    name: string;
    duration_min: string;
    price: string;
};

function makeEmptyServiceDraft(): SpecialistServiceDraft {
    return { name: "", duration_min: "", price: "" };
}

function mapSpecialistServicesToDraft(services?: Specialist["services"]): SpecialistServiceDraft[] {
    if (!services || services.length === 0) {
        return [makeEmptyServiceDraft()];
    }
    return services.map((service) => ({
        name: service.name ?? "",
        duration_min: service.duration_min != null ? String(service.duration_min) : "",
        price: service.price != null ? String(service.price) : "",
    }));
}

function parseServicesFromDraft(
    drafts: SpecialistServiceDraft[],
): Array<{ name: string; duration_min?: number; price?: number }> {
    return drafts
        .map((draft) => {
            const name = draft.name.trim();
            if (!name) {
                return null;
            }
            const parsedDuration = draft.duration_min.trim()
                ? Number.parseInt(draft.duration_min.trim(), 10)
                : undefined;
            const parsedPrice = draft.price.trim()
                ? Number.parseInt(draft.price.trim(), 10)
                : undefined;
            const payload: { name: string; duration_min?: number; price?: number } = { name };
            if (Number.isFinite(parsedDuration) && parsedDuration && parsedDuration > 0) {
                payload.duration_min = parsedDuration;
            }
            if (Number.isFinite(parsedPrice) && parsedPrice != null && parsedPrice >= 0) {
                payload.price = parsedPrice;
            }
            return payload;
        })
        .filter((service): service is { name: string; duration_min?: number; price?: number } => Boolean(service));
}

async function createSpecialist(data: SpecialistMutationPayload): Promise<Specialist> {
    const response = await api.post("/calendar/specialists", data);
    return (response.data || {}) as Specialist;
}

async function updateSpecialist(
    specialistId: string,
    data: Partial<SpecialistMutationPayload>,
): Promise<Specialist> {
    const response = await api.patch(`/calendar/specialists/${specialistId}`, data);
    return (response.data || {}) as Specialist;
}

async function setSpecialistActive(specialistId: string, isActive: boolean): Promise<Specialist> {
    const endpoint = isActive ? "enable" : "disable";
    const response = await api.post(`/calendar/specialists/${specialistId}/${endpoint}`);
    return (response.data || {}) as Specialist;
}

function UsersPanel({
    session,
    role,
    branches,
    clients,
    companies,
    companyId,
    clientId,
    currentAgentId,
}: {
    session: SessionData;
    role: ConsoleRole;
    branches: TeamBranch[];
    clients: TeamClient[];
    companies: TeamCompany[];
    companyId?: string | null;
    clientId?: string | null;
    currentAgentId?: string | null;
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
    const [createAgentSsoUsername, setCreateAgentSsoUsername] = useState("");
    const [createAgentSsoPassword, setCreateAgentSsoPassword] = useState("");
    const [createAgentSsoTempPassword, setCreateAgentSsoTempPassword] = useState(true);
    const [createAgentIsActive, setCreateAgentIsActive] = useState(true);
    const [agentSearch, setAgentSearch] = useState("");
    const [agentRoleFilter, setAgentRoleFilter] = useState<"all" | AgentRole>("all");
    const [agentStatusFilter, setAgentStatusFilter] = useState<"all" | "active" | "inactive">("all");
    const [membershipAgentId, setMembershipAgentId] = useState("");
    const [membershipScope, setMembershipScope] = useState<MembershipScope>("client");
    const [membershipRole, setMembershipRole] = useState<AgentRole>("manager");
    const [membershipCompanyId, setMembershipCompanyId] = useState(companyId ?? "");
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
    const [routingProfileAgentId, setRoutingProfileAgentId] = useState("");
    const [routingProfileScope, setRoutingProfileScope] = useState<RoutingProfileScope>("client");
    const [routingProfileBranchId, setRoutingProfileBranchId] = useState("");
    const [routingProfileStatus, setRoutingProfileStatus] = useState<RoutingProfileStatus>("available");
    const [routingProfileCapacity, setRoutingProfileCapacity] = useState("");
    const [routingProfileReason, setRoutingProfileReason] = useState("");
    const [editingRoutingProfileKey, setEditingRoutingProfileKey] = useState<string | null>(null);
    const [routingProfileTarget, setRoutingProfileTarget] = useState<string | null>(null);

    const agentsQuery = useQuery({
        queryKey: ["agents"],
        queryFn: async () => (await agentsApi.list()).data,
        enabled: !!session && canReadTeam,
    });

    const agents = useMemo(() => {
        return (agentsQuery.data?.items ?? []) as Array<AgentBase | AgentWithIdentities>;
    }, [agentsQuery.data]);
    const agentsById = useMemo(() => {
        const mapped = new Map<string, AgentBase | AgentWithIdentities>();
        agents.forEach((agent) => {
            if (agent.id) {
                mapped.set(agent.id, agent);
            }
        });
        return mapped;
    }, [agents]);
    const clientsById = useMemo(() => {
        const mapped = new Map<string, TeamClient>();
        clients.forEach((client) => {
            if (client.id) {
                mapped.set(client.id, client);
            }
        });
        return mapped;
    }, [clients]);
    const companiesById = useMemo(() => {
        const mapped = new Map<string, TeamCompany>();
        companies.forEach((company) => {
            if (company.id) {
                mapped.set(company.id, company);
            }
        });
        return mapped;
    }, [companies]);
    const filteredAgents = useMemo(() => {
        const normalizedSearch = agentSearch.trim().toLowerCase();
        return agents.filter((agent) => {
            if (agentRoleFilter !== "all" && agent.role !== agentRoleFilter) {
                return false;
            }
            if (agentStatusFilter === "active" && !agent.is_active) {
                return false;
            }
            if (agentStatusFilter === "inactive" && agent.is_active) {
                return false;
            }
            if (!normalizedSearch) {
                return true;
            }
            const branchLabel = formatBranchLabel(agent.branch_id ?? null, branches).toLowerCase();
            const haystack = `${agent.name || ""} ${agent.role || ""} ${branchLabel}`.toLowerCase();
            return haystack.includes(normalizedSearch);
        });
    }, [agentRoleFilter, agentSearch, agentStatusFilter, agents, branches]);

    useEffect(() => {
        setMembershipClientId(clientId ?? "");
        setEditingClientId(clientId ?? "");
        setMembershipCompanyId(companyId ?? "");
        setEditingCompanyId(companyId ?? "");
        setRoutingProfileBranchId("");
        setEditingRoutingProfileKey(null);
    }, [clientId, companyId]);

    const membershipsQuery = useQuery({
        queryKey: ["team-memberships", clientId ?? "", membershipIncludeInactive, membershipFilterAgentId],
        queryFn: async () =>
            (
                await adminApi.listMemberships({
                    client_id: clientId || undefined,
                    include_inactive: membershipIncludeInactive ? "true" : undefined,
                    agent_id: membershipFilterAgentId || undefined,
                })
            ).data,
        enabled: !!session && canManage,
    });
    const branchLookupClientId = useMemo(() => {
        if (editingMembershipId && editingScope === "branch") {
            return editingClientId.trim();
        }
        if (membershipScope === "branch") {
            return membershipClientId.trim();
        }
        return "";
    }, [editingClientId, editingMembershipId, editingScope, membershipClientId, membershipScope]);
    const membershipBranchesQuery = useQuery({
        queryKey: ["membership-branches", branchLookupClientId],
        queryFn: async () =>
            (
                await adminApi.listBranches({
                    client_id: branchLookupClientId || undefined,
                })
            ).data,
        enabled: !!session && canReadTeam && !!branchLookupClientId,
    });
    const routingProfilesQuery = useQuery({
        queryKey: ["routing-profiles", clientId ?? ""],
        queryFn: async () => {
            if (!clientId) {
                return { items: [] as RoutingProfile[] };
            }
            return (await adminApi.listRoutingProfiles({ client_id: clientId })).data;
        },
        enabled: !!session && canReadTeam && !!clientId,
    });
    const routingBranchesQuery = useQuery({
        queryKey: ["routing-branches", clientId ?? ""],
        queryFn: async () => {
            if (!clientId) {
                return { items: [] as TeamBranch[] };
            }
            return (await adminApi.listBranches({ client_id: clientId })).data;
        },
        enabled: !!session && canReadTeam && !!clientId,
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
    useEffect(() => {
        if (membershipBranchesQuery.error) {
            handleError(membershipBranchesQuery.error);
        }
    }, [membershipBranchesQuery.error, handleError]);
    useEffect(() => {
        if (routingProfilesQuery.error) {
            handleError(routingProfilesQuery.error);
        }
    }, [routingProfilesQuery.error, handleError]);
    useEffect(() => {
        if (routingBranchesQuery.error) {
            handleError(routingBranchesQuery.error);
        }
    }, [routingBranchesQuery.error, handleError]);

    const memberships = useMemo(() => {
        return (membershipsQuery.data?.items ?? []) as AgentMembership[];
    }, [membershipsQuery.data]);
    const routingProfiles = useMemo(() => {
        return (routingProfilesQuery.data?.items ?? []) as RoutingProfile[];
    }, [routingProfilesQuery.data]);
    const membershipBranchOptions = useMemo(() => {
        const apiItems = ((membershipBranchesQuery.data?.items ?? []) as TeamBranch[]).filter((branch) => Boolean(branch.id));
        if (apiItems.length > 0) {
            return apiItems;
        }
        if (branchLookupClientId && clientId && branchLookupClientId === clientId) {
            return branches.filter((branch) => Boolean(branch.id));
        }
        return [];
    }, [branchLookupClientId, branches, clientId, membershipBranchesQuery.data]);
    const routingBranchOptions = useMemo(() => {
        const apiItems = ((routingBranchesQuery.data?.items ?? []) as TeamBranch[]).filter((branch) => Boolean(branch.id));
        if (apiItems.length > 0) {
            return apiItems;
        }
        return branches.filter((branch) => Boolean(branch.id));
    }, [branches, routingBranchesQuery.data]);
    const routingProfileAgents = useMemo(() => {
        return agents.filter((agent) => {
            if (!agent.id) {
                return false;
            }
            if (agent.client_id !== clientId) {
                return false;
            }
            return agent.role === "owner" || agent.role === "admin" || agent.role === "manager";
        });
    }, [agents, clientId]);
    const selectedMembershipAgent = membershipAgentId ? agentsById.get(membershipAgentId) : undefined;
    const selectedMembershipAgentIsProtected = selectedMembershipAgent?.role === "platform_admin";

    const isProtectedMembership = (membership: AgentMembership) => {
        const membershipAgent = agentsById.get(membership.agent_id);
        return membership.role === "platform_admin" || membershipAgent?.role === "platform_admin";
    };

    useEffect(() => {
        if (companyId && membershipScope === "company" && membershipCompanyId !== companyId) {
            setMembershipCompanyId(companyId);
        }
    }, [companyId, membershipCompanyId, membershipScope]);

    const activeCount = agents.filter((agent) => agent.is_active).length;
    const owners = agents.filter((agent) => agent.role === "owner").length;
    const managers = agents.filter((agent) => agent.role === "manager").length;
    const membershipsActiveCount = memberships.filter((membership) => membership.is_active).length;
    const routingProfilesCount = routingProfiles.length;
    const filteredAgentsCount = filteredAgents.length;
    const selectedClientLabel = clientId
        ? (clientsById.get(clientId)?.name ?? clientId.slice(0, 8))
        : "не выбран";
    const selectedCompanyLabel = companyId
        ? (companiesById.get(companyId)?.name ?? companyId.slice(0, 8))
        : null;

    const isBranchRequiredRole = createAgentRole === "manager";
    const canSelectBranchScope = createAgentRole !== "platform_admin";
    const canCreateAgent = canManage && Boolean(clientId);
    const agentBranchRequiredHint = isBranchRequiredRole
        ? "Для роли manager нужно выбрать филиал."
        : canSelectBranchScope
            ? "Выберите филиал для branch-only доступа или оставьте пустым для доступа ко всем филиалам клиента."
            : "platform_admin создается только как platform scope.";

    useEffect(() => {
        if (!canSelectBranchScope) {
            setCreateAgentBranchId("");
        }
    }, [canSelectBranchScope]);

    useEffect(() => {
        if (membershipScope === "client" && clientId && !membershipClientId) {
            setMembershipClientId(clientId);
        }
        if (membershipScope === "company" && companyId && !membershipCompanyId) {
            setMembershipCompanyId(companyId);
        }
        if (membershipScope === "branch" && clientId && !membershipClientId) {
            setMembershipClientId(clientId);
        }
        if (membershipScope !== "branch") {
            setMembershipBranchId("");
        }
    }, [membershipScope, clientId, companyId, membershipClientId, membershipCompanyId]);
    useEffect(() => {
        if (routingProfileScope !== "branch") {
            setRoutingProfileBranchId("");
        }
    }, [routingProfileScope]);

    const createAgentMutation = useMutation({
        mutationFn: async () => {
            if (!clientId) {
                throw new Error("Выберите клиентский контекст в Tenants перед созданием учеток.");
            }
            const payload: components["schemas"]["ConsoleAgentCreateRequest"] = {
                client_id: clientId,
                role: createAgentRole,
                name: createAgentName.trim() || undefined,
                branch_id: createAgentBranchId || undefined,
                oidc_subject: createAgentOidcSubject.trim() || undefined,
                sso_username: createAgentSsoUsername.trim() || undefined,
                sso_password: createAgentSsoPassword || undefined,
                sso_temp_password: createAgentSsoUsername.trim() ? createAgentSsoTempPassword : null,
                is_active: createAgentIsActive,
            };
            return (await adminApi.createAgent(payload)).data;
        },
        onSuccess: () => {
            toast.success("Учетная запись создана");
            setCreateAgentName("");
            setCreateAgentOidcSubject("");
            setCreateAgentSsoUsername("");
            setCreateAgentSsoPassword("");
            setCreateAgentSsoTempPassword(true);
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
            const payload: components["schemas"]["ConsoleMembershipCreateRequest"] = {
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
        mutationFn: async (payload: { membershipId: string; data: components["schemas"]["ConsoleMembershipUpdateRequest"] }) =>
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
    const resetRoutingProfileForm = () => {
        setRoutingProfileAgentId("");
        setRoutingProfileScope("client");
        setRoutingProfileBranchId("");
        setRoutingProfileStatus("available");
        setRoutingProfileCapacity("");
        setRoutingProfileReason("");
        setEditingRoutingProfileKey(null);
    };
    const upsertRoutingProfileMutation = useMutation({
        mutationFn: async () => {
            if (!clientId) {
                throw new Error("Выберите клиентский контекст");
            }
            if (!routingProfileAgentId) {
                throw new Error("Выберите пользователя");
            }
            if (routingProfileScope === "branch" && !routingProfileBranchId) {
                throw new Error("Выберите филиал для branch override");
            }
            const rawCapacity = routingProfileCapacity.trim();
            const parsedCapacity = rawCapacity ? Number(rawCapacity) : null;
            if (rawCapacity && (parsedCapacity === null || !Number.isFinite(parsedCapacity) || parsedCapacity < 1)) {
                throw new Error("Лимит должен быть числом >= 1");
            }
            const maxOpenCaseCount = parsedCapacity;
            return (
                await adminApi.upsertRoutingProfile({
                    agent_id: routingProfileAgentId,
                    client_id: clientId,
                    branch_id: routingProfileScope === "branch" ? routingProfileBranchId : null,
                    routing_status: routingProfileStatus,
                    max_open_case_count: maxOpenCaseCount,
                    reason: routingProfileReason.trim() || undefined,
                })
            ).data;
        },
        onMutate: () => {
            setRoutingProfileTarget(editingRoutingProfileKey || buildRoutingProfileKey(routingProfileAgentId, routingProfileBranchId || null));
        },
        onSuccess: () => {
            toast.success(editingRoutingProfileKey ? "Routing profile обновлен" : "Routing profile сохранен");
            resetRoutingProfileForm();
            queryClient.invalidateQueries({ queryKey: ["routing-profiles"] });
            queryClient.invalidateQueries({ queryKey: ["case-assignees"] });
        },
        onError: (error) => {
            if (error instanceof Error && !(error as { response?: unknown }).response) {
                toast.error(error.message);
                return;
            }
            handleError(error);
        },
        onSettled: () => {
            setRoutingProfileTarget(null);
        },
    });
    const deleteRoutingProfileMutation = useMutation({
        mutationFn: async (payload: { agentId: string; branchId?: string | null; reason?: string; key: string }) => {
            if (!clientId) {
                throw new Error("Выберите клиентский контекст");
            }
            return (
                await adminApi.deleteRoutingProfile(payload.agentId, {
                    client_id: clientId,
                    branch_id: payload.branchId || undefined,
                    reason: payload.reason,
                })
            ).data;
        },
        onMutate: ({ key }) => {
            setRoutingProfileTarget(key);
        },
        onSuccess: () => {
            toast.success("Routing override удален");
            queryClient.invalidateQueries({ queryKey: ["routing-profiles"] });
            queryClient.invalidateQueries({ queryKey: ["case-assignees"] });
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setRoutingProfileTarget(null);
        },
    });

    const startMembershipEdit = (membership: AgentMembership) => {
        if (isProtectedMembership(membership)) {
            toast.error("platform_admin membership защищен и не редактируется");
            return;
        }
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
        if (isProtectedMembership(membership)) {
            toast.error("platform_admin membership защищен и не редактируется");
            return;
        }
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
        const payload: components["schemas"]["ConsoleMembershipUpdateRequest"] = {
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
        if (isProtectedMembership(membership)) {
            toast.error("platform_admin membership защищен и не отключается");
            return;
        }
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
    const startRoutingProfileEdit = (profile: RoutingProfile) => {
        setEditingRoutingProfileKey(buildRoutingProfileKey(profile.agent_id, profile.branch_id));
        setRoutingProfileAgentId(profile.agent_id);
        setRoutingProfileScope(profile.scope);
        setRoutingProfileBranchId(profile.branch_id ?? "");
        setRoutingProfileStatus(profile.routing_status);
        setRoutingProfileCapacity(profile.max_open_case_count ? String(profile.max_open_case_count) : "");
        setRoutingProfileReason("");
    };
    const handleDeleteRoutingProfile = (profile: RoutingProfile) => {
        const reason = window.prompt("Причина удаления override (optional)")?.trim() || undefined;
        const key = buildRoutingProfileKey(profile.agent_id, profile.branch_id);
        deleteRoutingProfileMutation.mutate({
            agentId: profile.agent_id,
            branchId: profile.branch_id,
            reason,
            key,
        });
        if (editingRoutingProfileKey === key) {
            resetRoutingProfileForm();
        }
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

    const handleToggleAccess = (agent: AgentBase | AgentWithIdentities) => {
        if (!agent.id) {
            return;
        }
        if (agent.role === "platform_admin") {
            toast.error("platform_admin аккаунт защищен");
            return;
        }
        if (currentAgentId && agent.id === currentAgentId && agent.is_active) {
            toast.error("Нельзя отключить собственную учетную запись");
            return;
        }
        const isActive = Boolean(agent.is_active);
        const reason = window.prompt(isActive ? "Причина отключения доступа" : "Причина включения доступа");
        if (!reason || !reason.trim()) {
            return;
        }
        accessMutation.mutate({
            agentId: agent.id,
            enable: !isActive,
            reason: reason.trim(),
        });
    };

    const handleRebindOidc = (agentId: string) => {
        const targetAgent = agentsById.get(agentId);
        if (targetAgent?.role === "platform_admin" && role !== "platform_admin") {
            toast.error("Только platform_admin может менять OIDC у platform_admin");
            return;
        }
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
        if (isBranchRequiredRole && !createAgentBranchId) {
            toast.error("Для manager выберите филиал");
            return;
        }
        const hasOidc = Boolean(createAgentOidcSubject.trim());
        const hasSsoUsername = Boolean(createAgentSsoUsername.trim());
        const hasSsoPassword = Boolean(createAgentSsoPassword);
        if (hasOidc && (hasSsoUsername || hasSsoPassword)) {
            toast.error("Используйте либо oidc_subject, либо SSO login/password");
            return;
        }
        if (hasSsoUsername !== hasSsoPassword) {
            toast.error("Для SSO укажите и login, и password");
            return;
        }
        if (hasSsoPassword && createAgentSsoPassword.length < 8) {
            toast.error("SSO password должен быть не короче 8 символов");
            return;
        }
        createAgentMutation.mutate();
    };

    const handleCreateMembership = () => {
        if (!membershipAgentId) {
            toast.error("Выберите пользователя");
            return;
        }
        if (selectedMembershipAgentIsProtected) {
            toast.error("platform_admin membership не создается через Team");
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
                        <p className="mt-1 text-xs text-muted-foreground">Показано: {filteredAgentsCount}</p>
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
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                    <input
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Поиск: имя, роль, филиал"
                        value={agentSearch}
                        onChange={(event) => setAgentSearch(event.target.value)}
                    />
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={agentRoleFilter}
                        onChange={(event) => setAgentRoleFilter(event.target.value as "all" | AgentRole)}
                    >
                        <option value="all">Все роли</option>
                        {TEAM_AGENT_ROLES.map((roleValue) => (
                            <option key={`filter-role-${roleValue}`} value={roleValue}>
                                {roleValue}
                            </option>
                        ))}
                    </select>
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={agentStatusFilter}
                        onChange={(event) => setAgentStatusFilter(event.target.value as "all" | "active" | "inactive")}
                    >
                        <option value="all">Все статусы</option>
                        <option value="active">Только активные</option>
                        <option value="inactive">Только отключенные</option>
                    </select>
                </div>
            </div>

            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold">Создать учетную запись</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Быстрый выпуск owner/admin/manager/viewer для текущего клиента.
                        </p>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        {selectedCompanyLabel ? `company: ${selectedCompanyLabel} · ` : ""}
                        client: {selectedClientLabel}
                    </div>
                </div>
                {!clientId ? (
                    <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        Нет клиентского контекста. Выберите клиент в Tenants (`В контекст`), затем обновите Team.
                    </div>
                ) : null}
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={createAgentRole}
                        onChange={(event) => setCreateAgentRole(event.target.value as AgentRole)}
                        disabled={!canCreateAgent}
                    >
                        {TEAM_ASSIGNABLE_AGENT_ROLES.map((roleValue) => (
                            <option key={roleValue} value={roleValue}>
                                {roleValue}
                            </option>
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
                    <input
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="SSO login (optional)"
                        value={createAgentSsoUsername}
                        onChange={(event) => setCreateAgentSsoUsername(event.target.value)}
                        disabled={!canCreateAgent}
                    />
                    <input
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="SSO password (optional)"
                        type="password"
                        value={createAgentSsoPassword}
                        onChange={(event) => setCreateAgentSsoPassword(event.target.value)}
                        disabled={!canCreateAgent}
                    />
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={createAgentBranchId}
                        onChange={(event) => setCreateAgentBranchId(event.target.value)}
                        disabled={!canCreateAgent || !canSelectBranchScope}
                    >
                        <option value="">
                            {canSelectBranchScope ? "Client scope (все филиалы)" : "Platform scope"}
                        </option>
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
                    <label className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm">
                        <input
                            type="checkbox"
                            checked={createAgentSsoTempPassword}
                            onChange={(event) => setCreateAgentSsoTempPassword(event.target.checked)}
                            disabled={!canCreateAgent || !createAgentSsoUsername.trim()}
                        />
                        temp password
                    </label>
                    <button
                        type="button"
                        className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed xl:col-span-2"
                        onClick={handleCreateAgent}
                        disabled={!canCreateAgent || createAgentMutation.isPending}
                    >
                        {createAgentMutation.isPending ? "Создание..." : "Создать"}
                    </button>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">{agentBranchRequiredHint}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                    Для SSO укажите пару `login/password`. `oidc_subject` и SSO credentials вместе использовать нельзя.
                </p>
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
                <p className="mt-2 text-xs text-muted-foreground">
                    Список memberships ограничен текущим client context: <span className="font-medium">{selectedClientLabel}</span>.
                </p>

                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-8">
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
                                <option
                                    key={agent.id ?? `agent-create-${index}`}
                                    value={agent.id}
                                    disabled={agent.role === "platform_admin"}
                                >
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
                        {TEAM_ASSIGNABLE_AGENT_ROLES.map((roleValue) => (
                            <option key={roleValue} value={roleValue}>{roleValue}</option>
                        ))}
                    </select>
                    {membershipScope === "company" && (
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={membershipCompanyId}
                            onChange={(event) => setMembershipCompanyId(event.target.value)}
                            disabled={!canManage}
                        >
                            <option value="">Выберите компанию</option>
                            {companies.map((company) => (
                                <option key={company.id} value={company.id}>
                                    {company.name ?? company.id}
                                </option>
                            ))}
                        </select>
                    )}
                    {membershipScope === "client" && (
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={membershipClientId}
                            onChange={(event) => setMembershipClientId(event.target.value)}
                            disabled={!canManage}
                        >
                            <option value="">Выберите клиента</option>
                            {clients.map((client) => (
                                <option key={client.id} value={client.id}>
                                    {client.name ?? client.id}
                                </option>
                            ))}
                        </select>
                    )}
                    {membershipScope === "branch" && (
                        <>
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={membershipClientId}
                                onChange={(event) => setMembershipClientId(event.target.value)}
                                disabled={!canManage}
                            >
                                <option value="">Выберите клиента</option>
                                {clients.map((client) => (
                                    <option key={`branch-client-${client.id}`} value={client.id}>
                                        {client.name ?? client.id}
                                    </option>
                                ))}
                            </select>
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={membershipBranchId}
                                onChange={(event) => setMembershipBranchId(event.target.value)}
                                disabled={!canManage || !membershipClientId}
                            >
                                <option value="">
                                    {membershipBranchesQuery.isLoading ? "Загрузка филиалов..." : "Выберите филиал"}
                                </option>
                                {membershipBranchOptions.map((branch) => (
                                    <option key={branch.id} value={branch.id}>
                                        {branch.name ?? branch.id}
                                    </option>
                                ))}
                            </select>
                        </>
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
                        disabled={!canManage || createMembershipMutation.isPending || selectedMembershipAgentIsProtected}
                    >
                        {createMembershipMutation.isPending ? "Сохранение..." : "Добавить membership"}
                    </button>
                </div>
                {selectedMembershipAgentIsProtected ? (
                    <p className="mt-2 text-xs text-amber-700">
                        Для `platform_admin` memberships управляются автоматически и не редактируются вручную.
                    </p>
                ) : null}

                <div className="mt-4 space-y-2">
                    {membershipsQuery.isLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка memberships...</div>
                    ) : memberships.length === 0 ? (
                        <div className="text-sm text-muted-foreground">Memberships не найдены.</div>
                    ) : (
                        memberships.map((membership) => {
                            const isEditing = editingMembershipId === membership.id;
                            const rowLoading = membershipTarget === membership.id;
                            const protectedMembership = isProtectedMembership(membership);
                            return (
                                <div key={membership.id} className="rounded-lg border border-border/60 px-3 py-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-sm">
                                            <span className="font-medium">{membership.agent_name ?? membership.agent_id.slice(0, 8)}</span>
                                            <span className="text-muted-foreground">
                                                {" · "}
                                                {membershipTargetLabel(membership, branches, clientsById, companiesById)}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <RoleBadge role={membership.role} />
                                            <span className={`text-xs ${membership.is_active ? "text-green-700" : "text-muted-foreground"}`}>
                                                {membership.is_active ? "active" : "inactive"}
                                            </span>
                                            {protectedMembership ? (
                                                <span className="text-xs text-amber-700">protected</span>
                                            ) : null}
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => toggleMembershipActive(membership)}
                                                    disabled={rowLoading || protectedMembership}
                                                >
                                                    {rowLoading ? "..." : membership.is_active ? "Disable" : "Enable"}
                                                </button>
                                            ) : null}
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => startMembershipEdit(membership)}
                                                    disabled={rowLoading || protectedMembership}
                                                >
                                                    Edit
                                                </button>
                                            ) : null}
                                        </div>
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        scope={membership.scope} · company={membership.company_id ?? "—"} · client={membership.client_id ?? "—"} · branch={membership.branch_id ?? "—"}
                                    </div>
                                    {isEditing && canManage && !protectedMembership ? (
                                        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-6">
                                            <select
                                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={editingRole}
                                                onChange={(event) => setEditingRole(event.target.value as AgentRole)}
                                            >
                                                {TEAM_ASSIGNABLE_AGENT_ROLES.map((roleValue) => (
                                                    <option key={roleValue} value={roleValue}>
                                                        {roleValue}
                                                    </option>
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
                                                <select
                                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={editingCompanyId}
                                                    onChange={(event) => setEditingCompanyId(event.target.value)}
                                                >
                                                    <option value="">Выберите компанию</option>
                                                    {companies.map((company) => (
                                                        <option key={`edit-company-${company.id}`} value={company.id}>
                                                            {company.name ?? company.id}
                                                        </option>
                                                    ))}
                                                </select>
                                            )}
                                            {editingScope === "client" && (
                                                <select
                                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={editingClientId}
                                                    onChange={(event) => setEditingClientId(event.target.value)}
                                                >
                                                    <option value="">Выберите клиента</option>
                                                    {clients.map((client) => (
                                                        <option key={`edit-client-${client.id}`} value={client.id}>
                                                            {client.name ?? client.id}
                                                        </option>
                                                    ))}
                                                </select>
                                            )}
                                            {editingScope === "branch" && (
                                                <>
                                                    <select
                                                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={editingClientId}
                                                        onChange={(event) => setEditingClientId(event.target.value)}
                                                    >
                                                        <option value="">Выберите клиента</option>
                                                        {clients.map((client) => (
                                                            <option key={`edit-branch-client-${client.id}`} value={client.id}>
                                                                {client.name ?? client.id}
                                                            </option>
                                                        ))}
                                                    </select>
                                                    <select
                                                        className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={editingBranchId}
                                                        onChange={(event) => setEditingBranchId(event.target.value)}
                                                        disabled={!editingClientId}
                                                    >
                                                        <option value="">
                                                            {membershipBranchesQuery.isLoading ? "Загрузка филиалов..." : "Выберите филиал"}
                                                        </option>
                                                        {membershipBranchOptions.map((branch) => (
                                                            <option key={`edit-branch-${branch.id}`} value={branch.id}>
                                                                {branch.name ?? branch.id}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </>
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

            <div className="card-surface p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold">Routing Profiles</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Server-owned availability и capacity для case routing policies. Branch override перекрывает client default.
                        </p>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        profiles: {routingProfilesCount}
                    </div>
                </div>
                {!clientId ? (
                    <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        Нет клиентского контекста. Выберите клиента в Tenants, затем обновите Team.
                    </div>
                ) : null}
                {clientId && canManage ? (
                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={routingProfileAgentId}
                            onChange={(event) => setRoutingProfileAgentId(event.target.value)}
                            disabled={!canManage}
                        >
                            <option value="">Выберите owner/admin/manager</option>
                            {routingProfileAgents.map((agent) => (
                                <option key={`routing-agent-${agent.id}`} value={agent.id}>
                                    {(agent.name || "Без имени")} · {agent.role}
                                </option>
                            ))}
                        </select>
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={routingProfileScope}
                            onChange={(event) => setRoutingProfileScope(event.target.value as RoutingProfileScope)}
                            disabled={!canManage}
                        >
                            {TEAM_ROUTING_PROFILE_SCOPES.map((scopeValue) => (
                                <option key={`routing-scope-${scopeValue}`} value={scopeValue}>
                                    {scopeValue === "client" ? "client default" : "branch override"}
                                </option>
                            ))}
                        </select>
                        {routingProfileScope === "branch" ? (
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={routingProfileBranchId}
                                onChange={(event) => setRoutingProfileBranchId(event.target.value)}
                                disabled={!canManage}
                            >
                                <option value="">
                                    {routingBranchesQuery.isLoading ? "Загрузка филиалов..." : "Выберите филиал"}
                                </option>
                                {routingBranchOptions.map((branch) => (
                                    <option key={`routing-branch-${branch.id}`} value={branch.id}>
                                        {branch.name ?? branch.id}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                                Применится ко всему клиенту
                            </div>
                        )}
                        <select
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={routingProfileStatus}
                            onChange={(event) => setRoutingProfileStatus(event.target.value as RoutingProfileStatus)}
                            disabled={!canManage}
                        >
                            {TEAM_ROUTING_PROFILE_STATUSES.map((statusValue) => (
                                <option key={`routing-status-${statusValue}`} value={statusValue}>
                                    {formatRoutingProfileStatusLabel(statusValue)}
                                </option>
                            ))}
                        </select>
                        <input
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="max open cases (optional)"
                            inputMode="numeric"
                            value={routingProfileCapacity}
                            onChange={(event) => setRoutingProfileCapacity(event.target.value.replace(/[^\d]/g, ""))}
                            disabled={!canManage}
                        />
                        <input
                            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="reason (optional)"
                            value={routingProfileReason}
                            onChange={(event) => setRoutingProfileReason(event.target.value)}
                            disabled={!canManage}
                        />
                        <div className="xl:col-span-6 flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs text-muted-foreground">
                                `paused` блокирует новые назначения. `follow_up_only` оставляет только явную continuity по follow-up. Пустой лимит = без capacity cap.
                            </p>
                            <div className="flex items-center gap-2">
                                {editingRoutingProfileKey ? (
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={resetRoutingProfileForm}
                                        disabled={upsertRoutingProfileMutation.isPending}
                                    >
                                        Отмена
                                    </button>
                                ) : null}
                                <button
                                    type="button"
                                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                                    onClick={() => upsertRoutingProfileMutation.mutate()}
                                    disabled={!canManage || upsertRoutingProfileMutation.isPending}
                                >
                                    {upsertRoutingProfileMutation.isPending ? "Сохранение..." : editingRoutingProfileKey ? "Обновить profile" : "Сохранить profile"}
                                </button>
                            </div>
                        </div>
                    </div>
                ) : null}
                {clientId && !canManage ? (
                    <p className="mt-4 text-xs text-muted-foreground">
                        У вас read-only доступ. Изменять routing profiles могут только owner/admin/platform admin.
                    </p>
                ) : null}
                <div className="mt-4 space-y-2">
                    {routingProfilesQuery.isLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка routing profiles...</div>
                    ) : routingProfiles.length === 0 ? (
                        <div className="text-sm text-muted-foreground">Routing profiles не заданы. Работает fallback `available` без capacity cap.</div>
                    ) : (
                        routingProfiles.map((profile) => {
                            const key = buildRoutingProfileKey(profile.agent_id, profile.branch_id);
                            const rowLoading = routingProfileTarget === key;
                            return (
                                <div key={key} className="rounded-lg border border-border/60 px-3 py-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-sm">
                                            <span className="font-medium">{profile.agent_name ?? profile.agent_id.slice(0, 8)}</span>
                                            <span className="text-muted-foreground">
                                                {" · "}
                                                {formatRoutingProfileScopeLabel(profile, routingBranchOptions)}
                                            </span>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="rounded-full border border-border/60 px-2 py-1 text-xs font-medium">
                                                {formatRoutingProfileStatusLabel(profile.routing_status)}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {profile.max_open_case_count ? `cap ${profile.max_open_case_count}` : "без cap"}
                                            </span>
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => startRoutingProfileEdit(profile)}
                                                    disabled={rowLoading}
                                                >
                                                    Edit
                                                </button>
                                            ) : null}
                                            {canManage ? (
                                                <button
                                                    type="button"
                                                    className="btn-ghost"
                                                    onClick={() => handleDeleteRoutingProfile(profile)}
                                                    disabled={rowLoading || deleteRoutingProfileMutation.isPending}
                                                >
                                                    {rowLoading ? "..." : "Удалить override"}
                                                </button>
                                            ) : null}
                                        </div>
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        updated: {profile.updated_at ? new Date(profile.updated_at).toLocaleString("ru-RU") : "—"}
                                        {" · "}
                                        id: {profile.id.slice(0, 8)}
                                    </div>
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
                {!agentsQuery.isLoading && filteredAgents.length === 0 && (
                    <div className="card-surface p-6 text-sm text-muted-foreground">
                        Участники не найдены по текущему фильтру.
                    </div>
                )}
                {!agentsQuery.isLoading && filteredAgents.length > 0 && filteredAgents.map((agent, index) => {
                    const identity = resolveTelegramIdentity(agent);
                    const linkData = agent.id ? linkTokens[agent.id] : undefined;
                    const displayHandle = identity?.username ? `@${identity.username}` : identity?.external_id;
                    const agentBranchLabel = formatBranchLabel(agent.branch_id ?? null, branches);
                    const agentKey = agent.id ?? `agent-${index}`;
                    const isProtectedAgent = agent.role === "platform_admin";
                    const isSelfDisableBlocked = Boolean(currentAgentId && agent.id && agent.id === currentAgentId && agent.is_active);

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
                                            onClick={() => handleToggleAccess(agent)}
                                            disabled={accessTarget === agent.id || isProtectedAgent || isSelfDisableBlocked}
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
                                            disabled={oidcTarget === agent.id || (isProtectedAgent && role !== "platform_admin")}
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
    const queryClient = useQueryClient();
    const canWriteTeam = canAccessConsole(role, "team", "write");
    const branchOptions = useMemo(
        () => branches.filter((branch): branch is TeamBranch & { id: string } => Boolean(branch.id)),
        [branches],
    );
    const [createName, setCreateName] = useState("");
    const [createBranchId, setCreateBranchId] = useState("");
    const [createServices, setCreateServices] = useState<SpecialistServiceDraft[]>([makeEmptyServiceDraft()]);
    const [editingSpecialistId, setEditingSpecialistId] = useState<string | null>(null);
    const [editName, setEditName] = useState("");
    const [editBranchId, setEditBranchId] = useState("");
    const [editServices, setEditServices] = useState<SpecialistServiceDraft[]>([makeEmptyServiceDraft()]);
    const [statusTarget, setStatusTarget] = useState<string | null>(null);

    const specialistsQuery = useQuery({
        queryKey: ["calendar-specialists", selectedBranchId, canWriteTeam ? "all" : "active"],
        queryFn: () => (
            canWriteTeam
                ? fetchSpecialistsAdmin(selectedBranchId || undefined)
                : fetchSpecialists(selectedBranchId || undefined)
        ),
        enabled: !!session,
    });

    useEffect(() => {
        if (!createBranchId && selectedBranchId) {
            setCreateBranchId(selectedBranchId);
        }
    }, [createBranchId, selectedBranchId]);

    useEffect(() => {
        if (specialistsQuery.error) {
            handleError(specialistsQuery.error);
        }
    }, [specialistsQuery.error, handleError]);

    const createMutation = useMutation({
        mutationFn: (payload: SpecialistMutationPayload) => createSpecialist(payload),
        onSuccess: () => {
            toast.success("Специалист добавлен");
            setCreateName("");
            setCreateServices([makeEmptyServiceDraft()]);
            queryClient.invalidateQueries({ queryKey: ["calendar-specialists"] });
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const updateMutation = useMutation({
        mutationFn: (payload: { specialistId: string; data: Partial<SpecialistMutationPayload> }) =>
            updateSpecialist(payload.specialistId, payload.data),
        onSuccess: () => {
            toast.success("Специалист обновлен");
            setEditingSpecialistId(null);
            setEditName("");
            setEditBranchId("");
            setEditServices([makeEmptyServiceDraft()]);
            queryClient.invalidateQueries({ queryKey: ["calendar-specialists"] });
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const statusMutation = useMutation({
        mutationFn: (payload: { specialistId: string; isActive: boolean }) =>
            setSpecialistActive(payload.specialistId, payload.isActive),
        onMutate: ({ specialistId }) => {
            setStatusTarget(specialistId);
        },
        onSuccess: (_data, payload) => {
            toast.success(payload.isActive ? "Специалист включен" : "Специалист отключен");
            queryClient.invalidateQueries({ queryKey: ["calendar-specialists"] });
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setStatusTarget(null);
        },
    });

    const resolveTargetBranchId = (preferredBranchId: string) => {
        if (preferredBranchId) {
            return preferredBranchId;
        }
        if (selectedBranchId) {
            return selectedBranchId;
        }
        if (branchOptions.length === 1) {
            return branchOptions[0].id as string;
        }
        return "";
    };

    const handleCreateSpecialist = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!canWriteTeam) {
            return;
        }
        const name = createName.trim();
        if (!name) {
            toast.error("Введите имя специалиста");
            return;
        }
        const branchId = resolveTargetBranchId(createBranchId);
        if (!branchId) {
            toast.error("Выберите филиал");
            return;
        }
        createMutation.mutate({
            name,
            branch_id: branchId,
            services: parseServicesFromDraft(createServices),
        });
    };

    const startEditSpecialist = (specialist: Specialist) => {
        setEditingSpecialistId(specialist.id);
        setEditName(specialist.name ?? "");
        setEditBranchId(specialist.branch_id ?? "");
        setEditServices(mapSpecialistServicesToDraft(specialist.services));
    };

    const handleSaveSpecialist = (specialistId: string) => {
        if (!canWriteTeam) {
            return;
        }
        const name = editName.trim();
        if (!name) {
            toast.error("Введите имя специалиста");
            return;
        }
        const branchId = resolveTargetBranchId(editBranchId);
        if (!branchId) {
            toast.error("Выберите филиал");
            return;
        }
        updateMutation.mutate({
            specialistId,
            data: {
                name,
                branch_id: branchId,
                services: parseServicesFromDraft(editServices),
            },
        });
    };

    const addCreateService = () => {
        setCreateServices((current) => [...current, makeEmptyServiceDraft()]);
    };

    const removeCreateService = (index: number) => {
        setCreateServices((current) => {
            if (current.length <= 1) {
                return [makeEmptyServiceDraft()];
            }
            return current.filter((_, itemIndex) => itemIndex !== index);
        });
    };

    const patchCreateService = (
        index: number,
        field: keyof SpecialistServiceDraft,
        value: string,
    ) => {
        setCreateServices((current) =>
            current.map((service, itemIndex) => (
                itemIndex === index
                    ? { ...service, [field]: value }
                    : service
            ))
        );
    };

    const addEditService = () => {
        setEditServices((current) => [...current, makeEmptyServiceDraft()]);
    };

    const removeEditService = (index: number) => {
        setEditServices((current) => {
            if (current.length <= 1) {
                return [makeEmptyServiceDraft()];
            }
            return current.filter((_, itemIndex) => itemIndex !== index);
        });
    };

    const patchEditService = (
        index: number,
        field: keyof SpecialistServiceDraft,
        value: string,
    ) => {
        setEditServices((current) =>
            current.map((service, itemIndex) => (
                itemIndex === index
                    ? { ...service, [field]: value }
                    : service
            ))
        );
    };

    const specialists = specialistsQuery.data?.items ?? [];
    const totalServices = specialists.reduce((total, specialist) => total + (specialist.services?.length ?? 0), 0);
    const activeCount = specialists.filter((specialist) => specialist.is_active).length;

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
                            data-testid="team-specialists-branch-filter"
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
                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Специалисты</p>
                        <p className="text-2xl font-semibold mt-2">{specialists.length}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-muted/40 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Активные</p>
                        <p className="text-2xl font-semibold mt-2">{activeCount}</p>
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

            {canWriteTeam && (
                <form
                    onSubmit={handleCreateSpecialist}
                    className="card-surface p-6 space-y-4"
                    data-testid="team-specialist-create-form"
                >
                    <div>
                        <h3 className="text-base font-semibold">Добавить специалиста</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Создание привязано к onboarding booking шагу и текущему клиенту.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                        <input
                            data-testid="team-specialist-create-name"
                            className="rounded-xl border border-border/60 bg-background px-3 py-2 text-sm"
                            placeholder="Имя специалиста"
                            value={createName}
                            onChange={(event) => setCreateName(event.target.value)}
                        />
                        <select
                            data-testid="team-specialist-create-branch"
                            className="rounded-xl border border-border/60 bg-background px-3 py-2 text-sm"
                            value={createBranchId}
                            onChange={(event) => setCreateBranchId(event.target.value)}
                        >
                            <option value="">Выберите филиал</option>
                            {branchOptions.map((branch) => (
                                <option key={branch.id} value={branch.id}>
                                    {branch.name ?? branch.id}
                                </option>
                            ))}
                        </select>
                        <button
                            data-testid="team-specialist-create-submit"
                            type="submit"
                            className="btn-primary"
                            disabled={createMutation.isPending}
                        >
                            {createMutation.isPending ? "Добавление..." : "Добавить"}
                        </button>
                    </div>
                    <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-medium">Услуги специалиста</p>
                            <button
                                data-testid="team-specialist-create-service-add"
                                type="button"
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                onClick={addCreateService}
                            >
                                + Услуга
                            </button>
                        </div>
                        {createServices.map((service, index) => (
                            <div
                                key={`create-service-${index}`}
                                className="grid grid-cols-1 gap-2 md:grid-cols-4"
                                data-testid="team-specialist-create-service-row"
                            >
                                <input
                                    data-testid="team-specialist-create-service-name"
                                    className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="Название услуги"
                                    value={service.name}
                                    onChange={(event) => patchCreateService(index, "name", event.target.value)}
                                />
                                <input
                                    data-testid="team-specialist-create-service-duration"
                                    className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="Длительность, мин"
                                    inputMode="numeric"
                                    value={service.duration_min}
                                    onChange={(event) => patchCreateService(index, "duration_min", event.target.value)}
                                />
                                <input
                                    data-testid="team-specialist-create-service-price"
                                    className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="Цена, ₸"
                                    inputMode="numeric"
                                    value={service.price}
                                    onChange={(event) => patchCreateService(index, "price", event.target.value)}
                                />
                                <button
                                    data-testid="team-specialist-create-service-remove"
                                    type="button"
                                    className="rounded-lg border border-border/60 px-3 py-2 text-sm hover:bg-muted"
                                    onClick={() => removeCreateService(index)}
                                >
                                    Удалить
                                </button>
                            </div>
                        ))}
                    </div>
                </form>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {specialistsQuery.isLoading && (
                    <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
                        Загрузка специалистов...
                    </div>
                )}
                {!specialistsQuery.isLoading && specialists.length === 0 && (
                    <div className="card-surface p-6 text-sm text-muted-foreground">
                        Специалисты не найдены.
                    </div>
                )}
                {!specialistsQuery.isLoading && specialists.map((specialist) => (
                    <div
                        key={specialist.id}
                        className="card-surface p-5"
                        data-testid="team-specialist-card"
                        data-specialist-id={specialist.id}
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">
                                    {specialist.branch_name ?? formatBranchLabel(specialist.branch_id ?? null, branches)}
                                </p>
                                <p className="text-lg font-semibold mt-1" data-testid="team-specialist-name">{specialist.name}</p>
                            </div>
                            <span
                                data-testid="team-specialist-status"
                                className={`px-2 py-1 rounded text-xs font-medium ${specialist.is_active
                                    ? "bg-green-100 text-green-800"
                                    : "bg-muted text-muted-foreground"}`}
                            >
                                {specialist.is_active ? "Активен" : "Неактивен"}
                            </span>
                        </div>
                        {canWriteTeam && (
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                                <button
                                    data-testid="team-specialist-edit-toggle"
                                    type="button"
                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
                                    onClick={() => (
                                        editingSpecialistId === specialist.id
                                            ? setEditingSpecialistId(null)
                                            : startEditSpecialist(specialist)
                                    )}
                                >
                                    {editingSpecialistId === specialist.id ? "Скрыть редактирование" : "Редактировать"}
                                </button>
                                <button
                                    data-testid="team-specialist-status-toggle"
                                    type="button"
                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
                                    onClick={() => statusMutation.mutate({
                                        specialistId: specialist.id,
                                        isActive: !(specialist.is_active ?? true),
                                    })}
                                    disabled={statusTarget === specialist.id}
                                >
                                    {statusTarget === specialist.id
                                        ? "Сохранение..."
                                        : specialist.is_active
                                            ? "Отключить"
                                            : "Включить"}
                                </button>
                            </div>
                        )}
                        {canWriteTeam && editingSpecialistId === specialist.id && (
                            <div
                                className="mt-4 rounded-xl border border-border/60 bg-muted/20 p-3 space-y-3"
                                data-testid="team-specialist-edit-form"
                            >
                                <input
                                    data-testid="team-specialist-edit-name"
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    value={editName}
                                    onChange={(event) => setEditName(event.target.value)}
                                    placeholder="Имя специалиста"
                                />
                                <select
                                    data-testid="team-specialist-edit-branch"
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    value={editBranchId}
                                    onChange={(event) => setEditBranchId(event.target.value)}
                                >
                                    <option value="">Выберите филиал</option>
                                    {branchOptions.map((branch) => (
                                        <option key={branch.id} value={branch.id}>
                                            {branch.name ?? branch.id}
                                        </option>
                                    ))}
                                </select>
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground">Услуги</p>
                                        <button
                                            data-testid="team-specialist-edit-service-add"
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                            onClick={addEditService}
                                        >
                                            + Услуга
                                        </button>
                                    </div>
                                    {editServices.map((service, index) => (
                                        <div
                                            key={`edit-service-${index}`}
                                            className="grid grid-cols-1 gap-2 md:grid-cols-4"
                                            data-testid="team-specialist-edit-service-row"
                                        >
                                            <input
                                                data-testid="team-specialist-edit-service-name"
                                                className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                                placeholder="Название услуги"
                                                value={service.name}
                                                onChange={(event) => patchEditService(index, "name", event.target.value)}
                                            />
                                            <input
                                                data-testid="team-specialist-edit-service-duration"
                                                className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                                placeholder="Длительность, мин"
                                                inputMode="numeric"
                                                value={service.duration_min}
                                                onChange={(event) => patchEditService(index, "duration_min", event.target.value)}
                                            />
                                            <input
                                                data-testid="team-specialist-edit-service-price"
                                                className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                                placeholder="Цена, ₸"
                                                inputMode="numeric"
                                                value={service.price}
                                                onChange={(event) => patchEditService(index, "price", event.target.value)}
                                            />
                                            <button
                                                data-testid="team-specialist-edit-service-remove"
                                                type="button"
                                                className="rounded-lg border border-border/60 px-3 py-2 text-sm hover:bg-muted"
                                                onClick={() => removeEditService(index)}
                                            >
                                                Удалить
                                            </button>
                                        </div>
                                    ))}
                                </div>
                                <button
                                    data-testid="team-specialist-edit-save"
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => handleSaveSpecialist(specialist.id)}
                                    disabled={updateMutation.isPending}
                                >
                                    {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
                                </button>
                            </div>
                        )}
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
    const clients = (meQuery.data?.clients ?? []) as TeamClient[];
    const companies = (meQuery.data?.companies ?? []) as TeamCompany[];
    const selectedCompanyId = meQuery.data?.selected_company_id ?? meQuery.data?.client?.company_id ?? null;
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
                        data-testid={`team-tab-${tab.id}`}
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
                    clients={clients}
                    companies={companies}
                    companyId={selectedCompanyId}
                    clientId={meQuery.data?.client?.id ?? null}
                    currentAgentId={meQuery.data?.agent?.id ?? null}
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
