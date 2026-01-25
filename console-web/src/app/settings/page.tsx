"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { adminApi, agentsApi, authApi, telegramApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";

interface Branch {
    id: string;
    slug: string;
    name: string;
    is_active: boolean;
    instance_id?: string | null;
    telegram_chat_id?: string | null;
}

interface Agent {
    id: string;
    name: string | null;
    role: string;
    is_active: boolean;
    identities?: AgentIdentity[];
}

interface AgentIdentity {
    channel: "telegram";
    external_id: string;
    username?: string | null;
    linked_at?: string | null;
}

interface AgentLinkData {
    token: string;
    deep_link?: string | null;
    bot_username?: string | null;
    expires_at: string;
}

interface BotConfig {
    reminder_timeout_1: number | null;
    reminder_timeout_2: number | null;
    auto_close_timeout: number | null;
    quiet_hours_enabled: boolean;
    quiet_hours_start: string | null;
    quiet_hours_end: string | null;
    tone: string | null;
    autolearn_enabled: boolean;
    booking_enabled: boolean;
    enable_reminders: boolean;
    enable_owner_escalation: boolean;
}

interface SettingsData {
    branches: Branch[];
    bot_config: BotConfig | null;
}

async function fetchSettings(): Promise<SettingsData> {
    const response = await api.get("/settings");
    return response.data;
}

async function fetchAgents(): Promise<{ items: Agent[] }> {
    const response = await agentsApi.list();
    const data = response.data || {};
    return { items: (data.items || []) as unknown as Agent[] };
}

function RoleBadge({ role }: { role: string }) {
    const styles: Record<string, string> = {
        owner: "bg-purple-100 text-purple-800",
        admin: "bg-secondary text-secondary-foreground",
        manager: "bg-green-100 text-green-800",
        support: "bg-muted text-muted-foreground",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[role] || "bg-muted text-muted-foreground"}`}>
            {role}
        </span>
    );
}

function ConfigCard({ label, value, type = "text" }: { label: string; value: string | number | boolean | null; type?: string }) {
    let displayValue: React.ReactNode = value;

    if (type === "boolean") {
        displayValue = value ? (
            <span className="text-green-600 font-medium">✓ Включено</span>
        ) : (
            <span className="text-muted-foreground">Выключено</span>
        );
    } else if (type === "minutes" && typeof value === "number") {
        displayValue = `${value} мин`;
    } else if (value === null || value === undefined) {
        displayValue = <span className="text-muted-foreground">—</span>;
    }

    return (
        <div className="flex justify-between items-center py-2 border-b border-border/60 last:border-0">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{displayValue}</span>
        </div>
    );
}

type SessionData = ReturnType<typeof useSession>["data"];
type ProvisioningBranch = components["schemas"]["Branch"];
type ProvisioningAgent = components["schemas"]["Agent"];
type CapabilitiesPayload = components["schemas"]["CapabilitiesPayload"];
type CapabilitiesResponse = components["schemas"]["CapabilitiesResponse"];

type AgentRole = "owner" | "admin" | "manager" | "support";

const DEFAULT_TIMEZONE = "Asia/Almaty";

const WIZARD_STEPS = [
    { id: "branch", label: "Филиал", hint: "Draft" },
    { id: "integrations", label: "Интеграции", hint: "instance_id" },
    { id: "team", label: "Команда", hint: "Owner/Admin" },
    { id: "telegram", label: "Telegram", hint: "chat_id" },
    { id: "knowledge", label: "Knowledge", hint: "pack" },
    { id: "booking", label: "Booking", hint: "calendar" },
    { id: "go", label: "Go/No-Go", hint: "capabilities" },
] as const;

type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

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

function normalizeCapabilities(payload?: CapabilitiesPayload | null): CapabilitiesPayload {
    return {
        domain_slug: payload?.domain_slug ?? null,
        channels: {
            whatsapp: payload?.channels?.whatsapp ?? null,
            telegram: payload?.channels?.telegram ?? null,
            instagram: payload?.channels?.instagram ?? null,
        },
        providers: {
            availability_provider: payload?.providers?.availability_provider ?? null,
            crm_provider: payload?.providers?.crm_provider ?? null,
            calendar_provider: payload?.providers?.calendar_provider ?? null,
        },
        features: {
            booking_mode: payload?.features?.booking_mode ?? null,
            knowledge_upload: payload?.features?.knowledge_upload ?? null,
            analytics: payload?.features?.analytics ?? null,
            auto_learn: payload?.features?.auto_learn ?? null,
        },
    };
}

function mergeCapabilities(base?: CapabilitiesPayload | null, override?: CapabilitiesPayload | null): CapabilitiesPayload {
    const merged = normalizeCapabilities(base);
    const overridePayload = normalizeCapabilities(override);

    if (overridePayload.domain_slug) {
        merged.domain_slug = overridePayload.domain_slug;
    }

    (["whatsapp", "telegram", "instagram"] as const).forEach((key) => {
        const value = overridePayload.channels?.[key];
        if (value !== null && value !== undefined) {
            merged.channels[key] = value;
        }
    });

    const availabilityProvider = overridePayload.providers?.availability_provider;
    if (availabilityProvider !== null && availabilityProvider !== undefined) {
        merged.providers.availability_provider = availabilityProvider;
    }

    const crmProvider = overridePayload.providers?.crm_provider;
    if (crmProvider !== null && crmProvider !== undefined) {
        merged.providers.crm_provider = crmProvider;
    }

    const calendarProvider = overridePayload.providers?.calendar_provider;
    if (calendarProvider !== null && calendarProvider !== undefined) {
        merged.providers.calendar_provider = calendarProvider;
    }

    const bookingMode = overridePayload.features?.booking_mode;
    if (bookingMode !== null && bookingMode !== undefined) {
        merged.features.booking_mode = bookingMode;
    }

    const knowledgeUpload = overridePayload.features?.knowledge_upload;
    if (knowledgeUpload !== null && knowledgeUpload !== undefined) {
        merged.features.knowledge_upload = knowledgeUpload;
    }

    const analytics = overridePayload.features?.analytics;
    if (analytics !== null && analytics !== undefined) {
        merged.features.analytics = analytics;
    }

    const autoLearn = overridePayload.features?.auto_learn;
    if (autoLearn !== null && autoLearn !== undefined) {
        merged.features.auto_learn = autoLearn;
    }

    return merged;
}

function toTriState(value: boolean | null | undefined): string {
    if (value === true) {
        return "true";
    }
    if (value === false) {
        return "false";
    }
    return "inherit";
}

function fromTriState(value: string): boolean | null {
    if (value === "true") {
        return true;
    }
    if (value === "false") {
        return false;
    }
    return null;
}

function isNonEmptyRecord(value: unknown): value is Record<string, unknown> {
    if (!value || typeof value !== "object") {
        return false;
    }
    return Object.keys(value as Record<string, unknown>).length > 0;
}

function ProvisioningWizard({ session }: { session: SessionData }) {
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canEdit = role === "owner" || role === "admin";

    const [stepIndex, setStepIndex] = useState(0);
    const [companyName, setCompanyName] = useState("");
    const [companyId, setCompanyId] = useState("");
    const [billingInfo, setBillingInfo] = useState("");
    const [clientSlug, setClientSlug] = useState("");
    const [clientId, setClientId] = useState("");
    const [branchData, setBranchData] = useState<ProvisioningBranch | null>(null);
    const [branchForm, setBranchForm] = useState({
        name: "",
        slug: "",
        timezone: DEFAULT_TIMEZONE,
        phone: "",
        instanceId: "",
        telegramChatId: "",
        knowledgeTag: "",
        workingHours: "",
        bookingSettings: "",
    });
    const [activateOnSave, setActivateOnSave] = useState(true);
    const [agentForm, setAgentForm] = useState({
        name: "",
        role: "owner" as AgentRole,
        oidcSubject: "",
        branchId: "",
    });
    const [createdAgents, setCreatedAgents] = useState<ProvisioningAgent[]>([]);
    const [capabilitiesDraft, setCapabilitiesDraft] = useState<CapabilitiesPayload>(() => normalizeCapabilities());
    const [capabilitiesTouched, setCapabilitiesTouched] = useState(false);
    const [capabilitiesSavedAt, setCapabilitiesSavedAt] = useState<string | null>(null);
    const [specialistsConfirmed, setSpecialistsConfirmed] = useState(false);

    useEffect(() => {
        if (!clientId && meData?.client?.id) {
            setClientId(meData.client.id);
        }
        if (!companyId && meData?.client?.company_id) {
            setCompanyId(meData.client.company_id);
        }
    }, [clientId, companyId, meData]);

    useEffect(() => {
        if (!branchData) {
            return;
        }
        setBranchForm({
            name: branchData.name ?? "",
            slug: branchData.slug ?? "",
            timezone: branchData.timezone ?? DEFAULT_TIMEZONE,
            phone: branchData.phone ?? "",
            instanceId: branchData.instance_id ?? "",
            telegramChatId: branchData.telegram_chat_id ?? "",
            knowledgeTag: branchData.knowledge_tag ?? "",
            workingHours: stringifyOptionalJson(branchData.working_hours),
            bookingSettings: stringifyOptionalJson(branchData.booking_settings),
        });
        setAgentForm((prev) => ({
            ...prev,
            branchId: prev.branchId || branchData.id || "",
        }));
    }, [branchData]);

    const { data: capabilitiesData, isLoading: capabilitiesLoading, error: capabilitiesError, refetch: refetchCapabilities } = useQuery({
        queryKey: ["admin-capabilities", clientId, branchData?.id],
        queryFn: async () => {
            const response = await adminApi.getCapabilities({
                branch_id: branchData?.id,
                clientId: clientId || undefined,
            });
            return response.data as CapabilitiesResponse;
        },
        enabled: !!session && !!clientId && !!branchData?.id,
    });

    useEffect(() => {
        if (capabilitiesTouched || !capabilitiesData) {
            return;
        }
        const base = capabilitiesData.branch_capabilities?.payload ?? capabilitiesData.effective ?? null;
        setCapabilitiesDraft(normalizeCapabilities(base));
    }, [capabilitiesData, capabilitiesTouched]);

    useEffect(() => {
        if (capabilitiesTouched || capabilitiesData || !branchData) {
            return;
        }
        setCapabilitiesDraft((prev) => {
            const next = normalizeCapabilities(prev);
            if (branchData.instance_id && next.channels.whatsapp == null) {
                next.channels.whatsapp = true;
            }
            if (branchData.telegram_chat_id && next.channels.telegram == null) {
                next.channels.telegram = true;
            }
            if (branchData.knowledge_tag && next.features.knowledge_upload == null) {
                next.features.knowledge_upload = true;
            }
            if ((branchData.working_hours && Object.keys(branchData.working_hours).length > 0)
                && next.features.booking_mode == null) {
                next.features.booking_mode = "collect_preferences";
            }
            return next;
        });
    }, [branchData, capabilitiesData, capabilitiesTouched]);

    const createCompanyMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["CompanyCreateRequest"]) => {
            const response = await adminApi.createCompany(payload);
            return response.data;
        },
        onSuccess: (data) => {
            if (data.company?.id) {
                setCompanyId(data.company.id);
            }
            toast.success("Компания создана");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const createClientMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["ClientCreateRequest"]) => {
            const response = await adminApi.createClient(payload);
            return response.data;
        },
        onSuccess: (data) => {
            if (data.client?.id) {
                setClientId(data.client.id);
            }
            toast.success("Клиент создан");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const createBranchMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["BranchCreateRequest"]) => {
            const response = await adminApi.createBranch(payload);
            return response.data;
        },
        onSuccess: (data) => {
            setBranchData(data.branch as ProvisioningBranch);
            toast.success("Филиал создан");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const patchBranchMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["BranchUpdateRequest"]) => {
            if (!branchData?.id) {
                throw new Error("BRANCH_REQUIRED");
            }
            const response = await adminApi.patchBranch(branchData.id, payload);
            return response.data;
        },
        onSuccess: (data) => {
            setBranchData(data as ProvisioningBranch);
            toast.success("Филиал обновлён");
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                toast.error("Сначала создайте филиал");
                return;
            }
            handleError(error);
        },
    });

    const createAgentMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["AgentCreateRequest"]) => {
            const response = await adminApi.createAgent(payload);
            return response.data;
        },
        onSuccess: (data) => {
            setCreatedAgents((prev) => [data.agent as ProvisioningAgent, ...prev]);
            queryClient.invalidateQueries({ queryKey: ["agents"] });
            toast.success("Пользователь добавлен");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const patchCapabilitiesMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["CapabilitiesPatchRequest"]) => {
            const response = await adminApi.patchCapabilities(payload, clientId || undefined);
            return response.data;
        },
        onSuccess: (data) => {
            setCapabilitiesSavedAt(data.updated_at ?? new Date().toISOString());
            refetchCapabilities();
            toast.success("Capabilities сохранены");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const stepStatus = useMemo(() => {
        const hasWorkingHours = isNonEmptyRecord(branchData?.working_hours);
        const hasBookingSettings = isNonEmptyRecord(branchData?.booking_settings);
        const status: Record<WizardStepId, boolean> = {
            branch: !!branchData?.id,
            integrations: !!branchData?.instance_id,
            team: createdAgents.length > 0,
            telegram: !!branchData?.telegram_chat_id,
            knowledge: !!branchData?.knowledge_tag,
            booking: hasWorkingHours && hasBookingSettings,
            go: !!capabilitiesSavedAt,
        };
        return status;
    }, [branchData, createdAgents.length, capabilitiesSavedAt]);

    const capabilitiesPreview = useMemo(() => {
        const clientPayload = capabilitiesData?.client_capabilities?.payload ?? null;
        return mergeCapabilities(clientPayload, capabilitiesDraft);
    }, [capabilitiesData, capabilitiesDraft]);

    const hasWorkingHours = isNonEmptyRecord(branchData?.working_hours);
    const hasBookingSettings = isNonEmptyRecord(branchData?.booking_settings);
    const bookingEnabled = capabilitiesPreview.features?.booking_mode != null;

    const readinessItems = useMemo(() => {
        return [
            {
                id: "wa_instance",
                label: "WhatsApp instance_id",
                required: capabilitiesPreview.channels?.whatsapp === true,
                ok: !!branchData?.instance_id,
            },
            {
                id: "wa_active",
                label: "Филиал активен",
                required: capabilitiesPreview.channels?.whatsapp === true,
                ok: !!branchData?.is_active,
            },
            {
                id: "tg_chat",
                label: "Telegram chat_id",
                required: capabilitiesPreview.channels?.telegram === true,
                ok: !!branchData?.telegram_chat_id,
            },
            {
                id: "knowledge_tag",
                label: "Knowledge tag",
                required: capabilitiesPreview.features?.knowledge_upload === true,
                ok: !!branchData?.knowledge_tag,
            },
            {
                id: "booking_hours",
                label: "Working hours",
                required: bookingEnabled,
                ok: hasWorkingHours,
            },
            {
                id: "booking_settings",
                label: "Booking settings",
                required: bookingEnabled,
                ok: hasBookingSettings,
            },
            {
                id: "booking_specialists",
                label: "Specialists подтверждены",
                required: bookingEnabled,
                ok: specialistsConfirmed,
            },
        ];
    }, [
        branchData,
        capabilitiesPreview,
        bookingEnabled,
        hasBookingSettings,
        hasWorkingHours,
        specialistsConfirmed,
    ]);

    const missingRequirements = readinessItems.filter((item) => item.required && !item.ok);
    const goNoGoReady = missingRequirements.length === 0;

    const handleCreateCompany = () => {
        const name = companyName.trim();
        if (!name) {
            toast.error("Укажите название компании");
            return;
        }
        const billing = parseOptionalJson(billingInfo, "billing_info");
        if (billing.error) {
            toast.error(billing.error);
            return;
        }
        createCompanyMutation.mutate({
            name,
            billing_info: billing.value,
        });
    };

    const handleCreateClient = () => {
        const slug = clientSlug.trim();
        if (!slug) {
            toast.error("Укажите slug клиента");
            return;
        }
        createClientMutation.mutate({
            slug,
            company_id: companyId || undefined,
        });
    };

    const handleCreateBranch = () => {
        if (!clientId) {
            toast.error("Укажите client_id");
            return;
        }
        const name = branchForm.name.trim();
        const slug = branchForm.slug.trim();
        if (!name || !slug) {
            toast.error("Заполните название и slug");
            return;
        }
        createBranchMutation.mutate({
            client_id: clientId,
            name,
            slug,
            timezone: branchForm.timezone.trim() || undefined,
            phone: branchForm.phone.trim() || undefined,
            is_active: false,
        });
    };

    const handleUpdateBranchDraft = () => {
        if (!branchData?.id) {
            toast.error("Сначала создайте филиал");
            return;
        }
        const name = branchForm.name.trim();
        const slug = branchForm.slug.trim();
        if (!name || !slug) {
            toast.error("Заполните название и slug");
            return;
        }
        patchBranchMutation.mutate({
            name,
            slug,
            timezone: branchForm.timezone.trim() || undefined,
            phone: branchForm.phone.trim() || undefined,
        });
    };

    const handleSaveInstance = () => {
        if (!branchData?.id) {
            toast.error("Сначала создайте филиал");
            return;
        }
        const instanceId = branchForm.instanceId.trim();
        if (!instanceId) {
            toast.error("Укажите instance_id");
            return;
        }
        patchBranchMutation.mutate({
            instance_id: instanceId,
            is_active: activateOnSave,
        });
    };

    const handleSaveTelegram = () => {
        if (!branchData?.id) {
            toast.error("Сначала создайте филиал");
            return;
        }
        const chatId = branchForm.telegramChatId.trim();
        if (!chatId) {
            toast.error("Укажите telegram_chat_id");
            return;
        }
        patchBranchMutation.mutate({
            telegram_chat_id: chatId,
        });
    };

    const handleSaveKnowledge = () => {
        if (!branchData?.id) {
            toast.error("Сначала создайте филиал");
            return;
        }
        const tag = branchForm.knowledgeTag.trim();
        if (!tag) {
            toast.error("Укажите knowledge_tag");
            return;
        }
        patchBranchMutation.mutate({
            knowledge_tag: tag,
        });
    };

    const handleSaveBooking = () => {
        if (!branchData?.id) {
            toast.error("Сначала создайте филиал");
            return;
        }
        const workingHours = parseOptionalJson(branchForm.workingHours, "working_hours");
        if (workingHours.error) {
            toast.error(workingHours.error);
            return;
        }
        const bookingSettings = parseOptionalJson(branchForm.bookingSettings, "booking_settings");
        if (bookingSettings.error) {
            toast.error(bookingSettings.error);
            return;
        }
        if (!workingHours.value && !bookingSettings.value) {
            toast.error("Заполните working_hours или booking_settings");
            return;
        }
        patchBranchMutation.mutate({
            working_hours: workingHours.value,
            booking_settings: bookingSettings.value,
        });
    };

    const handleCreateAgent = () => {
        if (!clientId) {
            toast.error("Укажите client_id");
            return;
        }
        const roleValue = agentForm.role;
        const payload: components["schemas"]["AgentCreateRequest"] = {
            client_id: clientId,
            role: roleValue,
            name: agentForm.name.trim() || undefined,
            oidc_subject: agentForm.oidcSubject.trim() || undefined,
        };
        if (roleValue === "manager") {
            const branchId = agentForm.branchId || branchData?.id;
            if (!branchId) {
                toast.error("branch_id обязателен для manager");
                return;
            }
            payload.branch_id = branchId;
        }
        createAgentMutation.mutate(payload);
    };

    const handleSaveCapabilities = () => {
        if (!branchData?.id || !clientId) {
            toast.error("Нужны client_id и branch_id");
            return;
        }
        if (!goNoGoReady) {
            toast.error("Go/No-Go: заполните обязательные поля");
            return;
        }
        const sanitized = normalizeCapabilities(capabilitiesDraft);
        sanitized.domain_slug = sanitized.domain_slug?.trim() || null;
        patchCapabilitiesMutation.mutate({
            scope: "branch",
            branch_id: branchData.id,
            payload: sanitized,
        });
    };

    const handleReset = () => {
        setStepIndex(0);
        setBranchData(null);
        setBranchForm({
            name: "",
            slug: "",
            timezone: DEFAULT_TIMEZONE,
            phone: "",
            instanceId: "",
            telegramChatId: "",
            knowledgeTag: "",
            workingHours: "",
            bookingSettings: "",
        });
        setCreatedAgents([]);
        setCapabilitiesDraft(normalizeCapabilities());
        setCapabilitiesTouched(false);
        setCapabilitiesSavedAt(null);
        setSpecialistsConfirmed(false);
        setAgentForm({
            name: "",
            role: "owner",
            oidcSubject: "",
            branchId: "",
        });
    };

    const currentStep = WIZARD_STEPS[stepIndex];

    return (
        <div className="card-surface p-6 mb-8" data-testid="provisioning-wizard">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <div className="badge mb-3">Provisioning Wizard</div>
                    <h2 className="text-2xl font-semibold">Онбординг филиала</h2>
                    <p className="text-sm text-muted-foreground mt-2">
                        Пошаговый flow: филиал → интеграции → команда → Telegram → знания → booking → go/no-go.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${canEdit ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}>
                        {canEdit ? "write" : "read-only"}
                    </span>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={handleReset}
                        disabled={!canEdit}
                    >
                        Сбросить
                    </button>
                </div>
            </div>

            {!canEdit && (
                <div className="mt-6 rounded-xl border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
                    Provisioning доступен только для owner/admin.
                </div>
            )}

            <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card border border-border/60 rounded-lg p-4">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-3">
                        Company
                    </h3>
                    <label className="text-xs text-muted-foreground">Company ID (existing)</label>
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={companyId}
                        onChange={(event) => setCompanyId(event.target.value)}
                        placeholder="UUID компании"
                        disabled={!canEdit}
                    />
                    <label className="mt-3 block text-xs text-muted-foreground">Название компании</label>
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={companyName}
                        onChange={(event) => setCompanyName(event.target.value)}
                        placeholder="Truffles Beauty"
                        disabled={!canEdit}
                    />
                    <label className="mt-3 block text-xs text-muted-foreground">billing_info (JSON, optional)</label>
                    <textarea
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                        rows={3}
                        value={billingInfo}
                        onChange={(event) => setBillingInfo(event.target.value)}
                        placeholder='{"contract":"B2B","currency":"KZT"}'
                        disabled={!canEdit}
                    />
                    <button
                        type="button"
                        className="btn-primary mt-4"
                        onClick={handleCreateCompany}
                        disabled={!canEdit || createCompanyMutation.isPending}
                    >
                        {createCompanyMutation.isPending ? "Создание..." : "Создать компанию"}
                    </button>
                </div>

                <div className="bg-card border border-border/60 rounded-lg p-4">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-3">
                        Client
                    </h3>
                    <label className="text-xs text-muted-foreground">Client ID (existing)</label>
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={clientId}
                        onChange={(event) => setClientId(event.target.value)}
                        placeholder="UUID клиента"
                        disabled={!canEdit}
                    />
                    <label className="mt-3 block text-xs text-muted-foreground">Slug клиента</label>
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={clientSlug}
                        onChange={(event) => setClientSlug(event.target.value)}
                        placeholder="demo_salon"
                        disabled={!canEdit}
                    />
                    <label className="mt-3 block text-xs text-muted-foreground">Company ID (optional)</label>
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={companyId}
                        onChange={(event) => setCompanyId(event.target.value)}
                        placeholder="UUID компании"
                        disabled={!canEdit}
                    />
                    <button
                        type="button"
                        className="btn-primary mt-4"
                        onClick={handleCreateClient}
                        disabled={!canEdit || createClientMutation.isPending}
                    >
                        {createClientMutation.isPending ? "Создание..." : "Создать клиента"}
                    </button>
                    <p className="text-xs text-muted-foreground mt-3">
                        Если клиент уже есть, достаточно указать client_id.
                    </p>
                </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
                {WIZARD_STEPS.map((step, index) => {
                    const active = index === stepIndex;
                    const completed = stepStatus[step.id];
                    return (
                        <button
                            key={step.id}
                            type="button"
                            onClick={() => setStepIndex(index)}
                            className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                                active ? "border-primary bg-primary text-primary-foreground" : "border-border/60 bg-card hover:bg-muted"
                            }`}
                        >
                            <div className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ${
                                active ? "bg-primary-foreground text-primary" : "bg-muted text-foreground"
                            }`}>
                                {index + 1}
                            </div>
                            <div>
                                <div className="text-sm font-semibold">{step.label}</div>
                                <div className={`text-xs ${active ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                                    {completed ? "Готово" : step.hint}
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>

            <div className="mt-6 bg-card border border-border/60 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Step {stepIndex + 1}</p>
                        <h3 className="text-lg font-semibold">{currentStep.label}</h3>
                    </div>
                    {branchData?.id && (
                        <div className="text-xs text-muted-foreground">
                            Branch ID: <span className="font-mono">{branchData.id.slice(0, 8)}</span>
                        </div>
                    )}
                </div>

                {currentStep.id === "branch" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Draft филиал создаётся без instance_id. После создания можно заполнять интеграции и знания.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-muted-foreground">Название филиала</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={branchForm.name}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, name: event.target.value }))}
                                    placeholder="Almaty Downtown"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Slug</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={branchForm.slug}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, slug: event.target.value }))}
                                    placeholder="almaty_center"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Timezone</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={branchForm.timezone}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, timezone: event.target.value }))}
                                    placeholder="Asia/Almaty"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Телефон (опционально)</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={branchForm.phone}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, phone: event.target.value }))}
                                    placeholder="+7 777 000 00 00"
                                    disabled={!canEdit}
                                />
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-3">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={branchData ? handleUpdateBranchDraft : handleCreateBranch}
                                disabled={!canEdit || createBranchMutation.isPending || patchBranchMutation.isPending}
                            >
                                {branchData ? "Обновить филиал" : createBranchMutation.isPending ? "Создание..." : "Создать филиал"}
                            </button>
                            {!clientId && (
                                <span className="text-xs text-muted-foreground">
                                    Укажите client_id перед созданием филиала.
                                </span>
                            )}
                        </div>
                    </div>
                )}

                {currentStep.id === "integrations" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Instance ID подключает WhatsApp канал. Без него филиал остаётся draft.
                        </p>
                        <div>
                            <label className="text-xs text-muted-foreground">instance_id (WA)</label>
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchForm.instanceId}
                                onChange={(event) => setBranchForm((prev) => ({ ...prev, instanceId: event.target.value }))}
                                placeholder="instance-xxxxxxxx"
                                disabled={!canEdit}
                            />
                        </div>
                        <label className="flex items-center gap-2 text-sm">
                            <input
                                type="checkbox"
                                checked={activateOnSave}
                                onChange={(event) => setActivateOnSave(event.target.checked)}
                                disabled={!canEdit}
                            />
                            Активировать филиал после сохранения
                        </label>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handleSaveInstance}
                            disabled={!canEdit || patchBranchMutation.isPending}
                        >
                            {patchBranchMutation.isPending ? "Сохранение..." : "Сохранить instance_id"}
                        </button>
                        {branchData && (
                            <div className="text-xs text-muted-foreground">
                                Статус: {branchData.is_active ? "активен" : "draft"}
                            </div>
                        )}
                    </div>
                )}

                {currentStep.id === "team" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Создайте owner/admin пользователей для доступа в Console. Manager требует branch_id.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-muted-foreground">Имя</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={agentForm.name}
                                    onChange={(event) => setAgentForm((prev) => ({ ...prev, name: event.target.value }))}
                                    placeholder="Алия"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Роль</label>
                                <select
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={agentForm.role}
                                    onChange={(event) => setAgentForm((prev) => ({ ...prev, role: event.target.value as AgentRole }))}
                                    disabled={!canEdit}
                                >
                                    <option value="owner">owner</option>
                                    <option value="admin">admin</option>
                                    <option value="manager">manager</option>
                                    <option value="support">support</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">OIDC subject (optional)</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={agentForm.oidcSubject}
                                    onChange={(event) => setAgentForm((prev) => ({ ...prev, oidcSubject: event.target.value }))}
                                    placeholder="sub из OIDC"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">branch_id (manager)</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={agentForm.branchId}
                                    onChange={(event) => setAgentForm((prev) => ({ ...prev, branchId: event.target.value }))}
                                    placeholder={branchData?.id || "UUID филиала"}
                                    disabled={!canEdit || agentForm.role !== "manager"}
                                />
                            </div>
                        </div>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handleCreateAgent}
                            disabled={!canEdit || createAgentMutation.isPending}
                        >
                            {createAgentMutation.isPending ? "Создание..." : "Добавить пользователя"}
                        </button>
                        {createdAgents.length > 0 && (
                            <div className="mt-4 rounded-lg border border-border/60 bg-background p-3 text-xs">
                                <div className="text-muted-foreground mb-2">Созданные пользователи</div>
                                <div className="space-y-1">
                                    {createdAgents.slice(0, 4).map((agent) => (
                                        <div key={agent.id} className="flex items-center justify-between">
                                            <span>{agent.name || agent.id}</span>
                                            <span className="text-muted-foreground">{agent.role}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {currentStep.id === "telegram" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Telegram chat_id появляется после привязки бота владельцем в Console.
                        </p>
                        <div>
                            <label className="text-xs text-muted-foreground">telegram_chat_id</label>
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchForm.telegramChatId}
                                onChange={(event) => setBranchForm((prev) => ({ ...prev, telegramChatId: event.target.value }))}
                                placeholder="123456789"
                                disabled={!canEdit}
                            />
                        </div>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handleSaveTelegram}
                            disabled={!canEdit || patchBranchMutation.isPending}
                        >
                            {patchBranchMutation.isPending ? "Сохранение..." : "Сохранить chat_id"}
                        </button>
                        {branchData?.telegram_chat_id && (
                            <div className="text-xs text-muted-foreground">
                                Текущий chat_id: {branchData.telegram_chat_id}
                            </div>
                        )}
                    </div>
                )}

                {currentStep.id === "knowledge" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Knowledge tag связывает филиал с pack-файлом (branch-pack).
                        </p>
                        <div>
                            <label className="text-xs text-muted-foreground">knowledge_tag</label>
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchForm.knowledgeTag}
                                onChange={(event) => setBranchForm((prev) => ({ ...prev, knowledgeTag: event.target.value }))}
                                placeholder="demo_salon"
                                disabled={!canEdit}
                            />
                        </div>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handleSaveKnowledge}
                            disabled={!canEdit || patchBranchMutation.isPending}
                        >
                            {patchBranchMutation.isPending ? "Сохранение..." : "Сохранить knowledge_tag"}
                        </button>
                    </div>
                )}

                {currentStep.id === "booking" && (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            booking_settings и working_hours нужны для включения booking capability.
                            Специалисты добавляются в Phase 4 (Team + Calendar).
                        </p>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-muted-foreground">working_hours (JSON)</label>
                                <textarea
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                    rows={7}
                                    value={branchForm.workingHours}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, workingHours: event.target.value }))}
                                    placeholder='{"mon":[{"start":"09:00","end":"20:00"}]}'
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">booking_settings (JSON)</label>
                                <textarea
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                    rows={7}
                                    value={branchForm.bookingSettings}
                                    onChange={(event) => setBranchForm((prev) => ({ ...prev, bookingSettings: event.target.value }))}
                                    placeholder='{"default_duration_min":60,"buffer_min":10}'
                                    disabled={!canEdit}
                                />
                            </div>
                        </div>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={handleSaveBooking}
                            disabled={!canEdit || patchBranchMutation.isPending}
                        >
                            {patchBranchMutation.isPending ? "Сохранение..." : "Сохранить booking данные"}
                        </button>
                    </div>
                )}

                {currentStep.id === "go" && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                                    Capabilities (branch override)
                                </h4>
                                <label className="text-xs text-muted-foreground">domain_slug</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={capabilitiesDraft.domain_slug ?? ""}
                                    onChange={(event) => {
                                        setCapabilitiesTouched(true);
                                        setCapabilitiesDraft((prev) => ({ ...normalizeCapabilities(prev), domain_slug: event.target.value || null }));
                                    }}
                                    placeholder="salon"
                                    disabled={!canEdit}
                                />

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-muted-foreground">WhatsApp</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.channels?.whatsapp)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    channels: {
                                                        ...normalizeCapabilities(prev).channels,
                                                        whatsapp: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">Telegram</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.channels?.telegram)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    channels: {
                                                        ...normalizeCapabilities(prev).channels,
                                                        telegram: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">Instagram</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.channels?.instagram)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    channels: {
                                                        ...normalizeCapabilities(prev).channels,
                                                        instagram: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-muted-foreground">availability_provider</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={capabilitiesDraft.providers?.availability_provider ?? ""}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    providers: {
                                                        ...normalizeCapabilities(prev).providers,
                                                        availability_provider: event.target.value ? event.target.value as CapabilitiesPayload["providers"]["availability_provider"] : null,
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="">Наследовать</option>
                                            <option value="none">none</option>
                                            <option value="google_calendar">google_calendar</option>
                                            <option value="bitrix">bitrix</option>
                                            <option value="amocrm">amocrm</option>
                                            <option value="manual">manual</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">crm_provider</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={capabilitiesDraft.providers?.crm_provider ?? ""}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    providers: {
                                                        ...normalizeCapabilities(prev).providers,
                                                        crm_provider: event.target.value ? event.target.value as CapabilitiesPayload["providers"]["crm_provider"] : null,
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="">Наследовать</option>
                                            <option value="none">none</option>
                                            <option value="amocrm">amocrm</option>
                                            <option value="bitrix">bitrix</option>
                                            <option value="custom">custom</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">calendar_provider</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={capabilitiesDraft.providers?.calendar_provider ?? ""}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    providers: {
                                                        ...normalizeCapabilities(prev).providers,
                                                        calendar_provider: event.target.value ? event.target.value as CapabilitiesPayload["providers"]["calendar_provider"] : null,
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="">Наследовать</option>
                                            <option value="none">none</option>
                                            <option value="google_calendar">google_calendar</option>
                                            <option value="local">local</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-muted-foreground">booking_mode</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={capabilitiesDraft.features?.booking_mode ?? ""}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    features: {
                                                        ...normalizeCapabilities(prev).features,
                                                        booking_mode: event.target.value ? event.target.value as CapabilitiesPayload["features"]["booking_mode"] : null,
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="">Наследовать</option>
                                            <option value="collect_preferences">collect_preferences</option>
                                            <option value="confirm_slots">confirm_slots</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">knowledge_upload</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.features?.knowledge_upload)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    features: {
                                                        ...normalizeCapabilities(prev).features,
                                                        knowledge_upload: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">analytics</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.features?.analytics)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    features: {
                                                        ...normalizeCapabilities(prev).features,
                                                        analytics: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">auto_learn</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={toTriState(capabilitiesDraft.features?.auto_learn)}
                                            onChange={(event) => {
                                                setCapabilitiesTouched(true);
                                                setCapabilitiesDraft((prev) => ({
                                                    ...normalizeCapabilities(prev),
                                                    features: {
                                                        ...normalizeCapabilities(prev).features,
                                                        auto_learn: fromTriState(event.target.value),
                                                    },
                                                }));
                                            }}
                                            disabled={!canEdit}
                                        >
                                            <option value="inherit">Наследовать</option>
                                            <option value="true">Включено</option>
                                            <option value="false">Выключено</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                                    Go/No-Go checks
                                </h4>
                                <div className="space-y-2">
                                    {readinessItems.map((item) => (
                                        <div
                                            key={item.id}
                                            className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs ${
                                                item.required
                                                    ? item.ok
                                                        ? "border-green-200 bg-green-50 text-green-800"
                                                        : "border-destructive/30 bg-destructive/10 text-destructive"
                                                    : "border-border/60 bg-muted/40 text-muted-foreground"
                                            }`}
                                        >
                                            <span>{item.label}</span>
                                            <span>{item.required ? (item.ok ? "OK" : "Missing") : "N/A"}</span>
                                        </div>
                                    ))}
                                </div>
                                {bookingEnabled && (
                                    <label className="flex items-center gap-2 text-sm">
                                        <input
                                            type="checkbox"
                                            checked={specialistsConfirmed}
                                            onChange={(event) => setSpecialistsConfirmed(event.target.checked)}
                                            disabled={!canEdit}
                                        />
                                        Специалисты добавлены (Phase 4)
                                    </label>
                                )}

                                <button
                                    type="button"
                                    className="btn-primary w-full"
                                    onClick={handleSaveCapabilities}
                                    disabled={!canEdit || patchCapabilitiesMutation.isPending || !goNoGoReady}
                                >
                                    {patchCapabilitiesMutation.isPending ? "Сохранение..." : "Сохранить capabilities"}
                                </button>
                                {!goNoGoReady && (
                                    <p className="text-xs text-destructive">
                                        Go/No-Go: заполните обязательные поля для включённых capabilities.
                                    </p>
                                )}
                                {capabilitiesSavedAt && (
                                    <p className="text-xs text-muted-foreground">
                                        Сохранено: {new Date(capabilitiesSavedAt).toLocaleString("ru-RU")}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="border-t border-border/60 pt-4">
                            <h4 className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">
                                Effective capabilities (read-only)
                            </h4>
                            {capabilitiesLoading && (
                                <p className="text-xs text-muted-foreground">Загрузка...</p>
                            )}
                            {capabilitiesError && (
                                <p className="text-xs text-destructive">Не удалось загрузить capabilities.</p>
                            )}
                            {capabilitiesData?.effective && (
                                <pre className="text-xs bg-muted/40 border border-border/60 rounded-lg p-3 overflow-auto">
                                    {JSON.stringify(capabilitiesData.effective, null, 2)}
                                </pre>
                            )}
                            {!capabilitiesLoading && !capabilitiesData?.effective && (
                                <p className="text-xs text-muted-foreground">Нет данных.</p>
                            )}
                        </div>
                    </div>
                )}

                <div className="mt-6 flex items-center justify-between">
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setStepIndex((prev) => Math.max(prev - 1, 0))}
                        disabled={stepIndex === 0}
                    >
                        Назад
                    </button>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={() => setStepIndex((prev) => Math.min(prev + 1, WIZARD_STEPS.length - 1))}
                        disabled={stepIndex === WIZARD_STEPS.length - 1 || (stepIndex === 0 && !branchData?.id)}
                    >
                        Далее
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function SettingsPage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();
    const [verifyTarget, setVerifyTarget] = useState<string | null>(null);
    const [testTarget, setTestTarget] = useState<string | null>(null);
    const [linkTarget, setLinkTarget] = useState<string | null>(null);
    const [linkTokens, setLinkTokens] = useState<Record<string, AgentLinkData>>({});
    const buildSha = process.env.NEXT_PUBLIC_BUILD_SHA;
    const buildTime = process.env.NEXT_PUBLIC_BUILD_TIME;
    const buildShaLabel = buildSha ? buildSha.slice(0, 7) : "unknown";
    const buildTimeLabel = buildTime ?? "unknown";

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ["settings"],
        queryFn: fetchSettings,
        enabled: !!session,
    });

    const { data: agentsData, isLoading: agentsLoading, error: agentsError, refetch: refetchAgents } = useQuery({
        queryKey: ["agents"],
        queryFn: fetchAgents,
        enabled: !!session,
    });

    const verifyMutation = useMutation({
        mutationFn: async (action: { targetKey: string; label: string; payload: { scope: "client" | "branch"; branch_id?: string } }) => {
            const { data } = await telegramApi.verify(action.payload);
            return { data, action };
        },
        onMutate: (action) => {
            setVerifyTarget(action.targetKey);
        },
        onSuccess: ({ data, action }) => {
            if (data.success) {
                toast.success(`Код верификации (${action.label}): ${data.verification_code}`);
            } else {
                toast.error(data.error_message || `Не удалось отправить код (${action.label})`);
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setVerifyTarget(null);
        },
    });

    const testMutation = useMutation({
        mutationFn: async (action: { targetKey: string; label: string; payload: { scope: "client" | "branch"; branch_id?: string; message?: string } }) => {
            const { data } = await telegramApi.test(action.payload);
            return { data, action };
        },
        onMutate: (action) => {
            setTestTarget(action.targetKey);
        },
        onSuccess: ({ data, action }) => {
            if (data.success) {
                toast.success(`Тестовое сообщение отправлено (${action.label})`);
            } else {
                toast.error(data.error_message || `Не удалось отправить тест (${action.label})`);
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTestTarget(null);
        },
    });

    const linkMutation = useMutation({
        mutationFn: async (agentId: string) => {
            const { data } = await agentsApi.linkTelegram(agentId);
            return { data, agentId };
        },
        onMutate: (agentId) => {
            setLinkTarget(agentId);
        },
        onSuccess: ({ data, agentId }) => {
            setLinkTokens((prev) => ({ ...prev, [agentId]: data as unknown as AgentLinkData }));
            toast.success("Ссылка для Telegram создана");
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setLinkTarget(null);
        },
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра настроек.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="settings-title">Настройки</h1>
                <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="settings-title">Настройки</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="settings-error">
                    <p className="text-destructive mb-4">Не удалось загрузить настройки</p>
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="settings-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    const config = data?.bot_config;

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="settings-title">Настройки</h1>
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад в Inbox
                </Link>
            </div>
            <div className="mb-4 text-xs text-muted-foreground" data-testid="settings-build-info">
                Build: <span className="font-mono" title={buildSha ?? "unknown"}>{buildShaLabel}</span> |{" "}
                <span className="font-mono">{buildTimeLabel}</span>
            </div>

            <ProvisioningWizard session={session} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* SLA & Reminders */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-sla">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        ⏱️ SLA и напоминания
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Первое напоминание" value={config.reminder_timeout_1} type="minutes" />
                            <ConfigCard label="Второе напоминание" value={config.reminder_timeout_2} type="minutes" />
                            <ConfigCard label="Авто-закрытие" value={config.auto_close_timeout} type="minutes" />
                            <ConfigCard label="Напоминания включены" value={config.enable_reminders} type="boolean" />
                            <ConfigCard label="Эскалация на владельца" value={config.enable_owner_escalation} type="boolean" />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Quiet Hours */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-quiet-hours">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🌙 Тихие часы
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Тихие часы" value={config.quiet_hours_enabled} type="boolean" />
                            <ConfigCard label="Начало" value={config.quiet_hours_start} />
                            <ConfigCard label="Конец" value={config.quiet_hours_end} />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Bot Behavior */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-bot">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🤖 Поведение бота
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Тон общения" value={config.tone} />
                            <ConfigCard label="Авто-обучение" value={config.autolearn_enabled} type="boolean" />
                            <ConfigCard label="Бронирование" value={config.booking_enabled} type="boolean" />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Telegram Connector */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-telegram-connector">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        📨 Telegram коннектор
                    </h2>
                    <p className="text-sm text-muted-foreground mb-3">
                        Проверка и тест отправки в Telegram (client scope, owner/admin).
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() =>
                                verifyMutation.mutate({
                                    targetKey: "client",
                                    label: "client",
                                    payload: { scope: "client" },
                                })
                            }
                            disabled={verifyTarget === "client"}
                            data-testid="settings-telegram-verify"
                        >
                            {verifyTarget === "client" ? "Отправка..." : "Verify"}
                        </button>
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() =>
                                testMutation.mutate({
                                    targetKey: "client",
                                    label: "client",
                                    payload: { scope: "client" },
                                })
                            }
                            disabled={testTarget === "client"}
                            data-testid="settings-telegram-test"
                        >
                            {testTarget === "client" ? "Отправка..." : "Send test"}
                        </button>
                    </div>
                </div>

                {/* Branches (TG-02) */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-branches">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🏢 Филиалы
                    </h2>
                    <div className="space-y-2">
                        {data?.branches.map((branch) => (
                            <div
                                key={branch.id}
                                className="flex items-center justify-between p-3 bg-muted rounded"
                                data-testid="settings-branch-row"
                            >
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium">{branch.name}</span>
                                        <span className="text-sm text-muted-foreground">({branch.slug})</span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        instance_id: {branch.instance_id || "—"}
                                    </div>
                                    {/* Telegram status */}
                                    <div className="flex items-center gap-1 mt-1">
                                        {branch.telegram_chat_id ? (
                                            <>
                                                <span className="text-primary text-xs">📨</span>
                                                <span className="text-xs text-muted-foreground font-mono">
                                                    {branch.telegram_chat_id.slice(0, 15)}...
                                                </span>
                                            </>
                                        ) : (
                                            <span className="text-xs text-muted-foreground">Telegram не настроен</span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`px-2 py-0.5 rounded text-xs ${branch.is_active
                                            ? "bg-green-100 text-green-800"
                                            : "bg-muted text-muted-foreground"
                                            }`}
                                    >
                                        {branch.is_active ? "Активен" : "Неактивен"}
                                    </span>
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                        onClick={() =>
                                            verifyMutation.mutate({
                                                targetKey: branch.id,
                                                label: branch.name,
                                                payload: { scope: "branch", branch_id: branch.id },
                                            })
                                        }
                                        disabled={!branch.telegram_chat_id || verifyTarget === branch.id}
                                        data-testid="settings-branch-verify"
                                    >
                                        {verifyTarget === branch.id ? "Отправка..." : "Verify"}
                                    </button>
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                        onClick={() =>
                                            testMutation.mutate({
                                                targetKey: branch.id,
                                                label: branch.name,
                                                payload: { scope: "branch", branch_id: branch.id },
                                            })
                                        }
                                        disabled={!branch.telegram_chat_id || testTarget === branch.id}
                                        data-testid="settings-branch-test"
                                    >
                                        {testTarget === branch.id ? "Отправка..." : "Send test"}
                                    </button>
                                </div>
                            </div>
                        ))}
                        {data?.branches.length === 0 && (
                            <p className="text-muted-foreground text-center py-2" data-testid="settings-branches-empty">Нет филиалов</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Team Members - Full Width */}
            <div className="bg-card border border-border/60 rounded-lg p-5 mt-6" data-testid="settings-team">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    👥 Команда
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {agentsLoading && (
                        <p className="text-muted-foreground text-center py-4 col-span-3" data-testid="settings-team-empty">
                            Загрузка команды...
                        </p>
                    )}
                    {!agentsLoading && agentsError && (
                        <div className="text-center py-4 col-span-3">
                            <p className="text-muted-foreground" data-testid="settings-team-empty">
                                Команда недоступна
                            </p>
                            <button
                                type="button"
                                className="mt-2 rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted"
                                onClick={() => refetchAgents()}
                            >
                                Повторить
                            </button>
                        </div>
                    )}
                    {!agentsLoading && !agentsError && agentsData?.items.map((agent) => {
                        const telegramIdentity = agent.identities?.find((identity) => identity.channel === "telegram");
                        const linkData = linkTokens[agent.id];
                        const displayHandle = telegramIdentity?.username
                            ? `@${telegramIdentity.username}`
                            : telegramIdentity?.external_id;

                        return (
                            <div
                                key={agent.id}
                                className="flex flex-col gap-2 p-3 bg-muted rounded"
                                data-testid="settings-team-row"
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 bg-secondary rounded-full flex items-center justify-center text-secondary-foreground font-medium">
                                            {agent.name?.charAt(0).toUpperCase() || "?"}
                                        </div>
                                        <span className="font-medium">{agent.name || "Без имени"}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <RoleBadge role={agent.role} />
                                        <span
                                            className={`w-2 h-2 rounded-full ${agent.is_active ? "bg-green-500" : "bg-muted"
                                                }`}
                                        ></span>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted-foreground">Telegram:</span>
                                    <span className={telegramIdentity ? "font-medium" : "text-muted-foreground"}>
                                        {telegramIdentity ? displayHandle : "не подключен"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between gap-2">
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                        onClick={() => linkMutation.mutate(agent.id)}
                                        disabled={linkTarget === agent.id}
                                        data-testid="settings-team-link"
                                    >
                                        {linkTarget === agent.id
                                            ? "Генерация..."
                                            : telegramIdentity
                                                ? "Переподключить"
                                                : "Подключить Telegram"}
                                    </button>
                                    {telegramIdentity?.linked_at && (
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(telegramIdentity.linked_at).toLocaleDateString("ru-RU")}
                                        </span>
                                    )}
                                </div>
                                {linkData && (
                                    <div className="text-xs bg-background p-2 rounded border border-border/60 space-y-1">
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
                        );
                    })}
                    {!agentsLoading && !agentsError && agentsData?.items.length === 0 && (
                        <p className="text-muted-foreground text-center py-4 col-span-3" data-testid="settings-team-empty">
                            Нет участников команды
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
