"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import axios from "axios";
import toast from "react-hot-toast";
import {
    adminApi,
    authApi,
    canAccessConsole,
    confirmationsApi,
    knowledgeApi,
    learningApi,
    type KnowledgeHistoryItem,
    type LearningCandidate,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import AccessDenied from "@/components/AccessDenied";
import api from "@/lib/api";
import type { components } from "@/types/api.generated";

type SessionData = ReturnType<typeof useSession>["data"];
type FleetAttentionItem = components["schemas"]["FleetAttentionItem"];
type FleetClient = components["schemas"]["Client"];
type FleetBranch = components["schemas"]["Branch"];
type GuidedHours = {
    days: string;
    open: string;
    close: string;
};
type GuidedService = {
    id: string;
    name: string;
};
type GuidedSalonProfile = {
    salonName: string;
    city: string;
    addressFull: string;
    servicesSummary: string;
    languages: string;
    guestPolicy: string;
};
type GuidedBooking = {
    collectFields: string;
    botCanConfirm: boolean;
};
type GuidedPolicy = {
    paymentInfo: string;
    reschedule: string;
    cancel: string;
    discounts: string;
};
type SpecialistSummary = {
    id: string;
    name: string;
    branch_id?: string | null;
    branch_name?: string | null;
    services?: Array<Record<string, unknown>>;
    is_active?: boolean;
};

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

const KNOWLEDGE_STEPS = [
    { id: "draft", label: "Draft", hint: "редактирование" },
    { id: "validate", label: "Validate", hint: "валидация" },
    { id: "preview", label: "Preview", hint: "diff" },
    { id: "publish", label: "Publish", hint: "go/no-go" },
    { id: "history", label: "History", hint: "версии" },
    { id: "rollback", label: "Rollback", hint: "восстановление" },
] as const;

type KnowledgeStepId = (typeof KNOWLEDGE_STEPS)[number]["id"];

type ValidationState = {
    ran: boolean;
    errors: string[];
    warnings: string[];
    diff: string;
};

function isApiUnavailable(error: unknown) {
    return axios.isAxiosError(error)
        && [404, 501].includes(error.response?.status ?? 0);
}

function isGatewayLikeError(error: unknown) {
    if (!axios.isAxiosError(error)) {
        return false;
    }
    const status = error.response?.status ?? 0;
    const payload = error.response?.data as { error?: { code?: unknown } } | undefined;
    const code = payload?.error?.code;
    return status === 502
        || status === 503
        || status === 504
        || code === "PROXY_ERROR"
        || code === "UPSTREAM_ERROR"
        || code === "UPSTREAM_INVALID_RESPONSE";
}

function extractApiErrorCode(error: unknown): string | null {
    if (!axios.isAxiosError(error)) {
        return null;
    }
    const payload = error.response?.data as { error?: { code?: unknown } } | undefined;
    const code = payload?.error?.code;
    if (typeof code === "string" && code.trim()) {
        return code.trim();
    }
    return null;
}

function normalizeStringList(value: unknown): string[] {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.filter((item): item is string => typeof item === "string");
}

function formatPayload(value: unknown): string {
    if (typeof value === "string") {
        return value;
    }
    if (value === null || value === undefined) {
        return "";
    }
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

function formatTimestamp(value?: string | null): string {
    if (!value) {
        return "—";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString();
}

function extractHistoryItems(value: unknown): KnowledgeHistoryItem[] {
    if (!value || typeof value !== "object") {
        return [];
    }
    const payload = value as Record<string, unknown>;
    const items = payload.items ?? payload.history ?? payload.versions;
    if (!Array.isArray(items)) {
        return [];
    }
    return items as KnowledgeHistoryItem[];
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

function parseOptionalJson(value: string, label: string): { value?: Record<string, unknown>; error?: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return { value: {} };
    }
    try {
        const parsed = JSON.parse(trimmed);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return { error: `${label}: ожидается JSON-объект` };
        }
        return { value: parsed as Record<string, unknown> };
    } catch {
        return { error: `${label}: некорректный JSON` };
    }
}

function normalizeKnowledgeTag(value: string | null | undefined): string | null {
    const trimmed = (value ?? "").trim();
    return trimmed.length > 0 ? trimmed : null;
}

function sortJsonValue(value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map((item) => sortJsonValue(item));
    }
    if (!value || typeof value !== "object") {
        return value;
    }
    const entries = Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, sortJsonValue(item)] as const);
    return Object.fromEntries(entries);
}

function stableJsonStringify(value: unknown): string {
    return JSON.stringify(sortJsonValue(value));
}

function extractPayloadWorkingHours(payload: Record<string, unknown> | null): Record<string, unknown> | null {
    if (!payload) {
        return null;
    }
    const clientPack = ensureObject(payload.client_pack);
    const salon = ensureObject(clientPack.salon);
    const hours = salon.hours;
    if (!hours || typeof hours !== "object" || Array.isArray(hours)) {
        return null;
    }
    return hours as Record<string, unknown>;
}

function formatWorkingHoursSummary(hours: Record<string, unknown> | null | undefined): string {
    if (!hours || Object.keys(hours).length === 0) {
        return "не заданы";
    }
    const days = typeof hours.days === "string" ? hours.days.trim() : "";
    const open = typeof hours.open === "string" ? hours.open.trim() : "";
    const close = typeof hours.close === "string" ? hours.close.trim() : "";
    const base = [days, open && close ? `${open}-${close}` : ""].filter(Boolean);
    if (base.length > 0) {
        return base.join(" · ");
    }
    return `JSON (${Object.keys(hours).join(", ")})`;
}

function createDefaultPayload(): Record<string, unknown> {
    return {
        client_pack: {
            salon: {
                hours: {
                    days: "",
                    open: "",
                    close: "",
                },
            },
            services_catalog: {
                services: [],
            },
        },
    };
}

function ensureObject(value: unknown): Record<string, unknown> {
    if (value && typeof value === "object" && !Array.isArray(value)) {
        return { ...(value as Record<string, unknown>) };
    }
    return {};
}

function extractGuidedHours(payload: Record<string, unknown> | null): GuidedHours {
    const root = ensureObject(payload);
    const clientPack = ensureObject(root.client_pack);
    const salon = ensureObject(clientPack.salon);
    const hours = ensureObject(salon.hours);
    return {
        days: typeof hours.days === "string" ? hours.days : "",
        open: typeof hours.open === "string" ? hours.open : "",
        close: typeof hours.close === "string" ? hours.close : "",
    };
}

function extractGuidedServices(payload: Record<string, unknown> | null): GuidedService[] {
    const root = ensureObject(payload);
    const clientPack = ensureObject(root.client_pack);
    const servicesCatalog = ensureObject(clientPack.services_catalog);
    const services = Array.isArray(servicesCatalog.services) ? servicesCatalog.services : [];
    return services
        .map((item, index) => {
            if (!item || typeof item !== "object" || Array.isArray(item)) {
                return null;
            }
            const service = item as Record<string, unknown>;
            const name = typeof service.name === "string" ? service.name.trim() : "";
            if (!name) {
                return null;
            }
            return {
                id: `svc-${index}-${name.toLowerCase()}`,
                name,
            };
        })
        .filter((item): item is GuidedService => Boolean(item));
}

function normalizeString(value: unknown): string {
    return typeof value === "string" ? value : "";
}

function parseCsvLikeList(value: string): string[] {
    return value
        .split(/[,\n;]/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function extractGuidedSalonProfile(payload: Record<string, unknown> | null): GuidedSalonProfile {
    const root = ensureObject(payload);
    const clientPack = ensureObject(root.client_pack);
    const salon = ensureObject(clientPack.salon);
    const address = ensureObject(salon.address);
    const communication = ensureObject(salon.communication);
    const languages = Array.isArray(communication.languages)
        ? communication.languages.filter((item): item is string => typeof item === "string")
        : [];
    return {
        salonName: normalizeString(salon.name),
        city: normalizeString(salon.city),
        addressFull: normalizeString(address.full),
        servicesSummary: normalizeString(salon.services_summary),
        languages: languages.join(", "),
        guestPolicy: normalizeString(clientPack.guest_policy),
    };
}

function extractGuidedBooking(payload: Record<string, unknown> | null): GuidedBooking {
    const root = ensureObject(payload);
    const clientPack = ensureObject(root.client_pack);
    const booking = ensureObject(clientPack.booking);
    const collectFields = Array.isArray(booking.collect_fields)
        ? booking.collect_fields.filter((item): item is string => typeof item === "string")
        : [];
    return {
        collectFields: collectFields.join(", "),
        botCanConfirm: Boolean(booking.bot_can_confirm),
    };
}

function extractGuidedPolicy(payload: Record<string, unknown> | null): GuidedPolicy {
    const root = ensureObject(payload);
    const clientPack = ensureObject(root.client_pack);
    const policy = ensureObject(clientPack.policy);
    return {
        paymentInfo: normalizeString(policy.payment_info),
        reschedule: normalizeString(policy.reschedule),
        cancel: normalizeString(policy.cancel),
        discounts: normalizeString(policy.discounts),
    };
}

function flattenClientPackPaths(
    value: unknown,
    prefix = "client_pack",
    result: Array<{ path: string; preview: string }> = [],
) {
    if (result.length >= 200) {
        return result;
    }
    if (value === null || value === undefined) {
        result.push({ path: prefix, preview: "null" });
        return result;
    }
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        result.push({ path: prefix, preview: String(value) });
        return result;
    }
    if (Array.isArray(value)) {
        if (value.length === 0) {
            result.push({ path: prefix, preview: "[]" });
            return result;
        }
        value.slice(0, 8).forEach((item, index) => {
            flattenClientPackPaths(item, `${prefix}[${index}]`, result);
        });
        return result;
    }
    if (typeof value === "object") {
        const entries = Object.entries(value as Record<string, unknown>);
        if (entries.length === 0) {
            result.push({ path: prefix, preview: "{}" });
            return result;
        }
        entries.forEach(([key, item]) => {
            flattenClientPackPaths(item, `${prefix}.${key}`, result);
        });
    }
    return result;
}

function buildStructuredDraftPayload(
    basePayload: Record<string, unknown> | null,
    hours: GuidedHours,
    services: GuidedService[],
    salonProfile: GuidedSalonProfile,
    bookingProfile: GuidedBooking,
    policyProfile: GuidedPolicy,
): Record<string, unknown> {
    const root = {
        ...(basePayload ?? createDefaultPayload()),
    };
    const clientPack = ensureObject(root.client_pack);
    const salon = ensureObject(clientPack.salon);
    const salonHours = ensureObject(salon.hours);
    const salonAddress = ensureObject(salon.address);
    const salonCommunication = ensureObject(salon.communication);
    const booking = ensureObject(clientPack.booking);
    const policy = ensureObject(clientPack.policy);
    const servicesCatalog = ensureObject(clientPack.services_catalog);
    const currentServices = Array.isArray(servicesCatalog.services) ? servicesCatalog.services : [];

    const currentByName = new Map<string, Record<string, unknown>>();
    for (const item of currentServices) {
        if (!item || typeof item !== "object" || Array.isArray(item)) {
            continue;
        }
        const service = item as Record<string, unknown>;
        const name = typeof service.name === "string" ? service.name.trim().toLowerCase() : "";
        if (!name) {
            continue;
        }
        currentByName.set(name, { ...service });
    }

    const nextServices = services
        .map((service) => service.name.trim())
        .filter(Boolean)
        .map((name) => {
            const reused = currentByName.get(name.toLowerCase());
            if (reused) {
                return { ...reused, name };
            }
            return {
                name,
                synonyms: [],
                price_items: [],
            };
        });

    const nextHours: Record<string, unknown> = {
        ...salonHours,
        days: hours.days.trim(),
        open: hours.open.trim(),
        close: hours.close.trim(),
    };
    const nextSalon: Record<string, unknown> = {
        ...salon,
        name: salonProfile.salonName.trim(),
        city: salonProfile.city.trim(),
        services_summary: salonProfile.servicesSummary.trim(),
        hours: nextHours,
        address: {
            ...salonAddress,
            full: salonProfile.addressFull.trim(),
        },
        communication: {
            ...salonCommunication,
            languages: parseCsvLikeList(salonProfile.languages),
        },
    };
    const nextBooking: Record<string, unknown> = {
        ...booking,
        collect_fields: parseCsvLikeList(bookingProfile.collectFields),
        bot_can_confirm: bookingProfile.botCanConfirm,
    };
    const nextPolicy: Record<string, unknown> = {
        ...policy,
        payment_info: policyProfile.paymentInfo.trim(),
        reschedule: policyProfile.reschedule.trim(),
        cancel: policyProfile.cancel.trim(),
        discounts: policyProfile.discounts.trim(),
    };

    root.client_pack = {
        ...clientPack,
        salon: nextSalon,
        guest_policy: salonProfile.guestPolicy.trim(),
        booking: nextBooking,
        policy: nextPolicy,
        services_catalog: {
            ...servicesCatalog,
            services: nextServices,
        },
    };

    return root;
}

function KnowledgeStudio({ session }: { session: SessionData }) {
    const { handleError } = useErrorHandler();
    const queryClient = useQueryClient();
    const router = useRouter();
    const [stepIndex, setStepIndex] = useState(0);
    const [draftText, setDraftText] = useState("");
    const [ackWarnings, setAckWarnings] = useState(false);
    const [apiUnavailable, setApiUnavailable] = useState(false);
    const [gatewayError, setGatewayError] = useState<string | null>(null);
    const [selectedVersionId, setSelectedVersionId] = useState("");
    const [lastValidatedDraft, setLastValidatedDraft] = useState<string | null>(null);
    const [lastPublishAt, setLastPublishAt] = useState<string | null>(null);
    const [lastRollbackAt, setLastRollbackAt] = useState<string | null>(null);
    const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);
    const [rollbackReason, setRollbackReason] = useState("");
    const [branchId, setBranchId] = useState("");
    const [isSelectingBranch, setIsSelectingBranch] = useState(false);
    const [fleetClientId, setFleetClientId] = useState("");
    const [fleetCompanyId, setFleetCompanyId] = useState("");
    const [fleetBranchId, setFleetBranchId] = useState("");
    const [isApplyingFleetContext, setIsApplyingFleetContext] = useState(false);
    const [fleetAttentionEnabled, setFleetAttentionEnabled] = useState(false);
    const [fleetAttentionError, setFleetAttentionError] = useState<string | null>(null);
    const fleetAutoApplyRef = useRef<string | null>(null);
    const [branchKnowledgeTagDraft, setBranchKnowledgeTagDraft] = useState("");
    const [branchWorkingHoursDraft, setBranchWorkingHoursDraft] = useState("{}");
    const [branchChangeReason, setBranchChangeReason] = useState("");
    const [guidedHours, setGuidedHours] = useState<GuidedHours>({
        days: "",
        open: "",
        close: "",
    });
    const [guidedServices, setGuidedServices] = useState<GuidedService[]>([]);
    const [guidedSalonProfile, setGuidedSalonProfile] = useState<GuidedSalonProfile>({
        salonName: "",
        city: "",
        addressFull: "",
        servicesSummary: "",
        languages: "",
        guestPolicy: "",
    });
    const [guidedBooking, setGuidedBooking] = useState<GuidedBooking>({
        collectFields: "",
        botCanConfirm: false,
    });
    const [guidedPolicy, setGuidedPolicy] = useState<GuidedPolicy>({
        paymentInfo: "",
        reschedule: "",
        cancel: "",
        discounts: "",
    });
    const [packInspectorQuery, setPackInspectorQuery] = useState("");
    const [validation, setValidation] = useState<ValidationState>({
        ran: false,
        errors: [],
        warnings: [],
        diff: "",
    });

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const isPlatformAdmin = role === "platform_admin";
    const canRead = canAccessConsole(role, "knowledge", "read");
    const canEdit = canAccessConsole(role, "knowledge", "write");
    const branches = useMemo(
        () => (meData?.branches ?? []) as FleetBranch[],
        [meData?.branches]
    );
    const selectedClientId = meData?.client?.id ?? "";
    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? "";
    const selectedBranchId = meData?.selected_branch_id ?? "";
    const branchIsValid = selectedBranchId
        ? branches.some((branch) => branch.id === selectedBranchId)
        : false;
    const branchSelectionRequired = Boolean(meData) && !branchIsValid;
    const branchOptions = branches.filter((branch) => branch.id);

    useEffect(() => {
        setBranchId(selectedBranchId ?? "");
    }, [selectedBranchId]);

    const currentQuery = useQuery({
        queryKey: ["knowledge-current"],
        queryFn: async () => {
            const response = await knowledgeApi.getCurrent();
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
    });

    const historyQuery = useQuery({
        queryKey: ["knowledge-history"],
        queryFn: async () => {
            const response = await knowledgeApi.history();
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
    });

    const candidatesQuery = useQuery({
        queryKey: ["learning-candidates"],
        queryFn: async () => {
            const response = await learningApi.list({ status: "pending", limit: 25 });
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
    });

    const fleetClientsQuery = useQuery({
        queryKey: ["knowledge-fleet-clients"],
        queryFn: async () => {
            const response = await adminApi.listClients({
                lifecycle: "active",
                include_fleet: "true",
                limit: 100,
            });
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && isPlatformAdmin,
        retry: false,
    });

    const fleetBranchesQuery = useQuery({
        queryKey: ["knowledge-fleet-branches", fleetClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                client_id: fleetClientId || undefined,
                lifecycle: "active",
                limit: 100,
            });
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && isPlatformAdmin && !!fleetClientId,
        retry: false,
    });

    const fleetAttentionQuery = useQuery({
        queryKey: ["knowledge-fleet-attention"],
        queryFn: async () => {
            const response = await adminApi.listFleetAttention({ limit: 12 });
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && isPlatformAdmin && fleetAttentionEnabled,
        retry: false,
    });

    const specialistsQuery = useQuery({
        queryKey: ["knowledge-specialists", selectedClientId, selectedBranchId],
        queryFn: async () => {
            const query = selectedBranchId ? `?branch_id=${selectedBranchId}` : "";
            const response = await api.get(`/calendar/specialists${query}`);
            return response.data as { items?: SpecialistSummary[] };
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
    });

    const allSpecialistsQuery = useQuery({
        queryKey: ["knowledge-specialists-all", selectedClientId],
        queryFn: async () => {
            const response = await api.get("/calendar/specialists");
            return response.data as { items?: SpecialistSummary[] };
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired && !!selectedClientId,
        retry: false,
    });

    const approveCandidateMutation = useMutation({
        mutationFn: async (candidateId: string) => {
            const response = await learningApi.approve(candidateId);
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Кандидат одобрен");
            candidatesQuery.refetch();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const rejectCandidateMutation = useMutation({
        mutationFn: async (candidateId: string) => {
            const response = await learningApi.reject(candidateId);
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Кандидат отклонен");
            candidatesQuery.refetch();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    useEffect(() => {
        const error = currentQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Knowledge API временно недоступен (gateway). Попробуйте обновить позже.");
            return;
        }
        handleError(error);
    }, [currentQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = historyQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("History недоступен из-за временной ошибки gateway.");
            return;
        }
        handleError(error);
    }, [historyQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = candidatesQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Learning candidates временно недоступны (gateway).");
            return;
        }
        handleError(error);
    }, [candidatesQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = fleetClientsQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Fleet clients временно недоступны (gateway).");
            return;
        }
        handleError(error);
    }, [fleetClientsQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = fleetBranchesQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Fleet branches временно недоступны (gateway).");
            return;
        }
        handleError(error);
    }, [fleetBranchesQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = fleetAttentionQuery.error;
        if (!fleetAttentionEnabled || !error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setFleetAttentionError("Fleet сигналы временно недоступны. Попробуйте обновить позже.");
            return;
        }
        handleError(error);
    }, [fleetAttentionQuery.error, fleetAttentionEnabled, apiUnavailable, handleError]);

    useEffect(() => {
        if (!fleetAttentionEnabled) {
            setFleetAttentionError(null);
            return;
        }
        if (!fleetAttentionQuery.isSuccess) {
            return;
        }
        setFleetAttentionError(null);
    }, [fleetAttentionEnabled, fleetAttentionQuery.isSuccess, fleetAttentionQuery.dataUpdatedAt]);

    useEffect(() => {
        const error = specialistsQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Список мастеров временно недоступен (gateway).");
            return;
        }
        handleError(error);
    }, [specialistsQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = allSpecialistsQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        if (isGatewayLikeError(error)) {
            setGatewayError("Список мастеров по клиенту временно недоступен (gateway).");
            return;
        }
        handleError(error);
    }, [allSpecialistsQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        if (
            currentQuery.isSuccess
            || historyQuery.isSuccess
            || specialistsQuery.isSuccess
            || allSpecialistsQuery.isSuccess
        ) {
            setGatewayError(null);
        }
    }, [
        currentQuery.isSuccess,
        historyQuery.isSuccess,
        specialistsQuery.isSuccess,
        allSpecialistsQuery.isSuccess,
    ]);

    const currentPayloadObject = useMemo(() => {
        const payload = currentQuery.data?.payload;
        if (payload && typeof payload === "object" && !Array.isArray(payload)) {
            return payload as Record<string, unknown>;
        }
        return null;
    }, [currentQuery.data]);
    const clientPackObject = useMemo(() => {
        if (!currentPayloadObject) {
            return {} as Record<string, unknown>;
        }
        return ensureObject(currentPayloadObject.client_pack);
    }, [currentPayloadObject]);
    const flatClientPackPaths = useMemo(
        () => flattenClientPackPaths(clientPackObject),
        [clientPackObject]
    );
    const filteredPackPaths = useMemo(() => {
        const query = packInspectorQuery.trim().toLowerCase();
        if (!query) {
            return flatClientPackPaths.slice(0, 14);
        }
        return flatClientPackPaths
            .filter((item) => item.path.toLowerCase().includes(query) || item.preview.toLowerCase().includes(query))
            .slice(0, 14);
    }, [flatClientPackPaths, packInspectorQuery]);
    const inspectorSummary = useMemo(() => {
        const servicesCatalog = ensureObject(clientPackObject.services_catalog);
        const services = Array.isArray(servicesCatalog.services) ? servicesCatalog.services : [];
        const priceList = Array.isArray(clientPackObject.price_list) ? clientPackObject.price_list : [];
        const booking = ensureObject(clientPackObject.booking);
        const policy = ensureObject(clientPackObject.policy);
        const collectFields = Array.isArray(booking.collect_fields) ? booking.collect_fields : [];
        const policyFilledCount = ["payment_info", "reschedule", "cancel", "discounts"]
            .map((key) => policy[key])
            .filter((value) => typeof value === "string" && value.trim().length > 0).length;
        return {
            servicesCount: services.length,
            priceRowsCount: priceList.length,
            collectFieldsCount: collectFields.length,
            policyFilledCount,
            flattenedFieldsCount: flatClientPackPaths.length,
        };
    }, [clientPackObject, flatClientPackPaths.length]);

    const currentText = useMemo(() => {
        if (!currentQuery.data) {
            return "";
        }
        const payload = currentQuery.data.content ?? currentQuery.data.payload ?? currentQuery.data;
        return formatPayload(payload);
    }, [currentQuery.data]);

    const historyItems = useMemo(
        () => extractHistoryItems(historyQuery.data),
        [historyQuery.data]
    );
    const learningCandidates = useMemo(
        () => (candidatesQuery.data?.items ?? []) as LearningCandidate[],
        [candidatesQuery.data]
    );
    const fleetClients = useMemo(
        () => (fleetClientsQuery.data?.items ?? []).filter((client): client is FleetClient => Boolean(client?.id)),
        [fleetClientsQuery.data]
    );
    const fleetBranches = useMemo(
        () => (fleetBranchesQuery.data?.items ?? []).filter((branch): branch is FleetBranch => Boolean(branch?.id)),
        [fleetBranchesQuery.data]
    );
    const fleetAttentionItems = useMemo(
        () => (fleetAttentionQuery.data?.items ?? []) as FleetAttentionItem[],
        [fleetAttentionQuery.data]
    );
    const specialists = useMemo(
        () => (specialistsQuery.data?.items ?? []).filter((item): item is SpecialistSummary => Boolean(item?.id)),
        [specialistsQuery.data]
    );
    const allSpecialists = useMemo(
        () => (allSpecialistsQuery.data?.items ?? []).filter((item): item is SpecialistSummary => Boolean(item?.id)),
        [allSpecialistsQuery.data]
    );
    const specialistsInOtherBranches = useMemo(
        () => allSpecialists.filter((item) => item.branch_id && item.branch_id !== selectedBranchId),
        [allSpecialists, selectedBranchId]
    );
    const specialistsByBranch = useMemo(() => {
        const counts = new Map<string, { label: string; count: number }>();
        for (const specialist of specialistsInOtherBranches) {
            const key = specialist.branch_id ?? "unknown";
            const label = specialist.branch_name ?? specialist.branch_id ?? "Другой филиал";
            const existing = counts.get(key);
            if (existing) {
                existing.count += 1;
                continue;
            }
            counts.set(key, { label, count: 1 });
        }
        return Array.from(counts.values()).sort((a, b) => b.count - a.count);
    }, [specialistsInOtherBranches]);
    const missingBranchSpecialistsButClientHasSome = specialists.length === 0 && specialistsInOtherBranches.length > 0;
    const fleetSummary = fleetAttentionQuery.data?.summary;
    const selectedBranchContext = useMemo(
        () => branches.find((branch) => branch.id === selectedBranchId) ?? null,
        [branches, selectedBranchId]
    );
    const selectedBranchWorkingHours = useMemo(() => {
        if (!selectedBranchContext?.working_hours) {
            return {} as Record<string, unknown>;
        }
        if (
            typeof selectedBranchContext.working_hours === "object"
            && !Array.isArray(selectedBranchContext.working_hours)
        ) {
            return selectedBranchContext.working_hours as Record<string, unknown>;
        }
        return {} as Record<string, unknown>;
    }, [selectedBranchContext]);
    const parsedBranchWorkingHours = useMemo(
        () => parseOptionalJson(branchWorkingHoursDraft, "working_hours"),
        [branchWorkingHoursDraft]
    );
    const effectiveWorkingHours = useMemo(() => {
        if (Object.keys(selectedBranchWorkingHours).length > 0) {
            return selectedBranchWorkingHours;
        }
        return extractPayloadWorkingHours(currentPayloadObject);
    }, [selectedBranchWorkingHours, currentPayloadObject]);
    const hasBranchChangeReason = branchChangeReason.trim().length > 0;
    const isBranchPatchDirty = useMemo(() => {
        if (!selectedBranchContext || parsedBranchWorkingHours.error) {
            return false;
        }
        const currentTag = normalizeKnowledgeTag(selectedBranchContext.knowledge_tag);
        const draftTag = normalizeKnowledgeTag(branchKnowledgeTagDraft);
        if (currentTag !== draftTag) {
            return true;
        }
        const currentHours = selectedBranchWorkingHours ?? {};
        const draftHours = parsedBranchWorkingHours.value ?? {};
        return stableJsonStringify(currentHours) !== stableJsonStringify(draftHours);
    }, [
        selectedBranchContext,
        parsedBranchWorkingHours.error,
        parsedBranchWorkingHours.value,
        branchKnowledgeTagDraft,
        selectedBranchWorkingHours,
    ]);

    useEffect(() => {
        if (!selectedBranchContext) {
            setBranchKnowledgeTagDraft("");
            setBranchWorkingHoursDraft("{}");
            return;
        }
        setBranchKnowledgeTagDraft(selectedBranchContext.knowledge_tag ?? "");
        const workingHours = selectedBranchContext.working_hours;
        if (workingHours && typeof workingHours === "object" && !Array.isArray(workingHours)) {
            setBranchWorkingHoursDraft(JSON.stringify(workingHours, null, 2));
        } else {
            setBranchWorkingHoursDraft("{}");
        }
    }, [selectedBranchContext]);

    useEffect(() => {
        setGuidedHours(extractGuidedHours(currentPayloadObject));
        const extractedServices = extractGuidedServices(currentPayloadObject);
        if (extractedServices.length > 0) {
            setGuidedServices(extractedServices);
        } else {
            setGuidedServices([{ id: `svc-${Date.now()}`, name: "" }]);
        }
        setGuidedSalonProfile(extractGuidedSalonProfile(currentPayloadObject));
        setGuidedBooking(extractGuidedBooking(currentPayloadObject));
        setGuidedPolicy(extractGuidedPolicy(currentPayloadObject));
    }, [currentPayloadObject, selectedBranchId]);

    useEffect(() => {
        if (!isPlatformAdmin || fleetClients.length === 0) {
            return;
        }
        if (fleetClientId && fleetClients.some((client) => client.id === fleetClientId)) {
            return;
        }
        const preferredClientId = selectedClientId && fleetClients.some((client) => client.id === selectedClientId)
            ? selectedClientId
            : fleetClients[0]?.id;
        if (!preferredClientId) {
            return;
        }
        const preferredClient = fleetClients.find((client) => client.id === preferredClientId);
        setFleetClientId(preferredClientId);
        setFleetCompanyId(preferredClient?.company_id ?? selectedCompanyId ?? "");
    }, [isPlatformAdmin, fleetClients, fleetClientId, selectedClientId, selectedCompanyId]);

    useEffect(() => {
        if (!fleetClientId) {
            setFleetBranchId("");
            return;
        }
        if (fleetBranches.length === 0) {
            setFleetBranchId("");
            return;
        }
        if (fleetBranchId && fleetBranches.some((branch) => branch.id === fleetBranchId)) {
            return;
        }
        const preferredBranchId = selectedBranchId && fleetBranches.some((branch) => branch.id === selectedBranchId)
            ? selectedBranchId
            : fleetBranches[0]?.id;
        setFleetBranchId(preferredBranchId ?? "");
    }, [fleetClientId, fleetBranches, fleetBranchId, selectedBranchId]);

    const hasErrors = validation.errors.length > 0;
    const hasWarnings = validation.warnings.length > 0;
    const isDraftDirty = lastValidatedDraft !== null && lastValidatedDraft !== draftText;
    const canPublish = canEdit
        && !apiUnavailable
        && validation.ran
        && !hasErrors
        && !isDraftDirty
        && (!hasWarnings || ackWarnings)
        && draftText.trim().length > 0;

    const validateMutation = useMutation({
        mutationFn: async () => {
            const response = await knowledgeApi.validate(draftText.trim());
            return response.data;
        },
        onSuccess: (data) => {
            const errors = normalizeStringList(data?.errors);
            const warnings = normalizeStringList(data?.warnings);
            const diff = typeof data?.diff === "string" ? data.diff : "";
            const valid = data?.valid ?? errors.length === 0;
            setValidation({ ran: true, errors, warnings, diff });
            setLastValidatedDraft(draftText);
            setAckWarnings(false);
            if (valid) {
                toast.success("Валидация пройдена");
            } else {
                toast.error("Валидация не пройдена");
            }
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            handleError(error);
        },
    });

    const publishMutation = useMutation({
        mutationFn: async () => {
            const response = await knowledgeApi.publish(draftText.trim());
            return response.data;
        },
        onSuccess: (data) => {
            setLastPublishAt(data?.published_at ?? new Date().toISOString());
            toast.success(data?.message || "Знания опубликованы");
            currentQuery.refetch();
            historyQuery.refetch();
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            if (extractApiErrorCode(error) === "KNOWLEDGE_PREFLIGHT_REQUIRED") {
                toast.error("Сначала выполните Validate для текущего draft, затем Publish.");
                setStepIndex(1);
                return;
            }
            handleError(error);
        },
    });

    const rollbackMutation = useMutation({
        mutationFn: async (reason: string) => {
            const confirmation = await confirmationsApi.create({
                action: "knowledge_rollback",
                target_type: "knowledge_version",
                target_id: selectedVersionId,
                reason,
            });
            const confirmationId = confirmation.data.confirmation_id;
            const response = await knowledgeApi.rollback(selectedVersionId, confirmationId);
            return response.data;
        },
        onSuccess: () => {
            setLastRollbackAt(new Date().toISOString());
            toast.success("Версия восстановлена");
            currentQuery.refetch();
            historyQuery.refetch();
            setShowRollbackConfirm(false);
            setRollbackReason("");
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            handleError(error);
        },
    });

    const applyBranchKnowledgePatchMutation = useMutation({
        mutationFn: async () => {
            if (!selectedBranchContext?.id) {
                throw new Error("Выберите филиал");
            }
            if (parsedBranchWorkingHours.error) {
                throw new Error(parsedBranchWorkingHours.error);
            }
            if (!isBranchPatchDirty) {
                throw new Error("Нет изменений для публикации");
            }
            const reason = branchChangeReason.trim();
            if (!reason) {
                throw new Error("Укажите причину изменения");
            }

            const draftResponse = await adminApi.draftBranchChange({
                branch_id: selectedBranchContext.id,
                reason,
                patch: {
                    knowledge_tag: branchKnowledgeTagDraft.trim() || null,
                    working_hours: parsedBranchWorkingHours.value ?? {},
                },
            });
            const draftChange = draftResponse.data.change;
            const changeId = draftChange?.id;
            if (!changeId) {
                throw new Error("Не удалось создать черновик изменения");
            }

            const validateResponse = await adminApi.validateBranchChange(changeId);
            const validatedChange = validateResponse.data.change;
            if (validatedChange?.status !== "validated") {
                const validationPayload = validatedChange?.validation_payload as
                    | { errors?: string[] }
                    | undefined;
                const firstError = validationPayload?.errors?.[0];
                throw new Error(firstError || "Валидация branch change не пройдена");
            }

            await adminApi.publishBranchChange(changeId, {});
            return changeId;
        },
        onSuccess: async () => {
            toast.success("Изменения знаний филиала опубликованы");
            setBranchChangeReason("");
            await queryClient.invalidateQueries({ queryKey: ["console-me"] });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-current"] });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-history"] });
            if (isPlatformAdmin) {
                await fleetBranchesQuery.refetch();
                await fleetAttentionQuery.refetch();
            }
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : "Не удалось применить изменения";
            toast.error(message);
        },
    });

    const stepStatus: Record<KnowledgeStepId, boolean> = {
        draft: draftText.trim().length > 0,
        validate: validation.ran && !hasErrors,
        preview: validation.ran && !hasErrors,
        publish: !!lastPublishAt,
        history: historyItems.length > 0,
        rollback: !!lastRollbackAt,
    };

    const currentStep = KNOWLEDGE_STEPS[stepIndex];
    const selectedFleetClient = fleetClients.find((client) => client.id === fleetClientId);
    const isFleetBusy = isApplyingFleetContext
        || fleetClientsQuery.isFetching
        || fleetBranchesQuery.isFetching
        || (fleetAttentionEnabled && fleetAttentionQuery.isFetching);

    const applyConsoleContext = useCallback(async ({
        companyId,
        clientId,
        branchId: nextBranchId,
        successMessage,
    }: {
        companyId?: string | null;
        clientId?: string | null;
        branchId?: string | null;
        successMessage?: string;
    }) => {
        setIsApplyingFleetContext(true);
        setGatewayError(null);
        try {
            setLocalStorageValue(COMPANY_ID_STORAGE_KEY, companyId ?? null);
            setLocalStorageValue(CLIENT_ID_STORAGE_KEY, clientId ?? null);
            setLocalStorageValue(BRANCH_ID_STORAGE_KEY, nextBranchId ?? null);
            await queryClient.invalidateQueries({ queryKey: ["console-me"] });
            await queryClient.refetchQueries({ queryKey: ["console-me"], exact: true });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-current"] });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-history"] });
            await queryClient.invalidateQueries({ queryKey: ["learning-candidates"] });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-specialists"] });
            await queryClient.invalidateQueries({ queryKey: ["knowledge-specialists-all"] });
            if (successMessage) {
                toast.success(successMessage);
            }
        } finally {
            setIsApplyingFleetContext(false);
        }
    }, [queryClient]);

    const resolveFleetCompanyId = useCallback((clientId?: string | null): string | null => {
        if (clientId) {
            const matchedClient = fleetClients.find((client) => client.id === clientId);
            if (matchedClient?.company_id) {
                return matchedClient.company_id;
            }
        }
        return fleetCompanyId || selectedFleetClient?.company_id || selectedCompanyId || null;
    }, [fleetClients, fleetCompanyId, selectedFleetClient?.company_id, selectedCompanyId]);

    const openRouteWithFleetContext = async (
        path: string,
        clientId?: string,
        companyId?: string | null,
        branchId?: string | null,
    ) => {
        if (!clientId) {
            toast.error("Выберите клиента");
            return;
        }
        await applyConsoleContext({
            companyId: companyId ?? resolveFleetCompanyId(clientId),
            clientId,
            branchId: branchId ?? null,
        });
        router.push(path);
    };

    const resolveBranchContextForClient = (clientId?: string | null): string | null => {
        if (!clientId) {
            return selectedBranchId || fleetBranchId || null;
        }
        if (selectedClientId === clientId && selectedBranchId) {
            return selectedBranchId;
        }
        if (fleetClientId === clientId && fleetBranchId) {
            return fleetBranchId;
        }
        return null;
    };

    const handleFleetBranchSelect = (nextBranchId: string) => {
        setFleetBranchId(nextBranchId);
        if (!fleetClientId || !nextBranchId || isApplyingFleetContext) {
            return;
        }
        void applyConsoleContext({
            companyId: resolveFleetCompanyId(fleetClientId),
            clientId: fleetClientId,
            branchId: nextBranchId,
            successMessage: branchSelectionRequired ? "Контекст филиала применен автоматически" : undefined,
        });
    };

    const selectKnowledgeBranch = async () => {
        if (!fleetClientId || !fleetBranchId) {
            toast.error("Выберите клиента и филиал");
            return;
        }
        await applyConsoleContext({
            companyId: resolveFleetCompanyId(fleetClientId),
            clientId: fleetClientId,
            branchId: fleetBranchId,
            successMessage: "Контекст Knowledge обновлен",
        });
    };

    useEffect(() => {
        if (!isPlatformAdmin || !branchSelectionRequired || isApplyingFleetContext) {
            return;
        }
        if (!fleetClientId || !fleetBranchId) {
            return;
        }
        const autoKey = `${fleetClientId}:${fleetBranchId}`;
        if (fleetAutoApplyRef.current === autoKey) {
            return;
        }
        fleetAutoApplyRef.current = autoKey;
        void applyConsoleContext({
            companyId: resolveFleetCompanyId(fleetClientId),
            clientId: fleetClientId,
            branchId: fleetBranchId,
            successMessage: "Контекст филиала применен автоматически",
        });
    }, [
        isPlatformAdmin,
        branchSelectionRequired,
        isApplyingFleetContext,
        fleetClientId,
        fleetBranchId,
        applyConsoleContext,
        resolveFleetCompanyId,
    ]);

    useEffect(() => {
        if (branchSelectionRequired) {
            return;
        }
        fleetAutoApplyRef.current = null;
    }, [branchSelectionRequired]);

    const addGuidedService = () => {
        setGuidedServices((prev) => [
            ...prev,
            { id: `svc-${Date.now()}-${prev.length}`, name: "" },
        ]);
    };

    const updateGuidedService = (id: string, value: string) => {
        setGuidedServices((prev) =>
            prev.map((service) => (service.id === id ? { ...service, name: value } : service))
        );
    };

    const removeGuidedService = (id: string) => {
        setGuidedServices((prev) => prev.filter((service) => service.id !== id));
    };

    const applyStructuredDraft = () => {
        const normalizedServices = guidedServices
            .map((service) => ({
                ...service,
                name: service.name.trim(),
            }))
            .filter((service) => service.name.length > 0);
        if (normalizedServices.length === 0) {
            toast.error("Добавьте хотя бы одну услугу");
            return;
        }
        const payload = buildStructuredDraftPayload(
            currentPayloadObject,
            guidedHours,
            normalizedServices,
            guidedSalonProfile,
            guidedBooking,
            guidedPolicy,
        );
        setDraftText(JSON.stringify(payload, null, 2));
        setValidation((prev) => (prev.ran ? { ...prev, ran: false } : prev));
        toast.success("Structured draft обновлен");
    };

    const renderPlatformAdminFleetPanel = () => {
        if (!isPlatformAdmin) {
            return null;
        }
        return (
            <div className="card-surface p-5" data-testid="knowledge-fleet-control">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">Fleet Knowledge Control</h2>
                        <p className="text-sm text-muted-foreground">
                            Быстрый выбор клиента и филиала для управления знаниями по всей платформе.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => {
                                if (fleetAttentionEnabled) {
                                    setFleetAttentionEnabled(false);
                                    setFleetAttentionError(null);
                                    return;
                                }
                                setFleetAttentionError(null);
                                setFleetAttentionEnabled(true);
                            }}
                            disabled={isApplyingFleetContext}
                        >
                            {fleetAttentionEnabled ? "Скрыть сигналы" : "Показать сигналы"}
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => {
                                setFleetAttentionError(null);
                                fleetClientsQuery.refetch();
                                if (fleetClientId) {
                                    fleetBranchesQuery.refetch();
                                }
                                if (fleetAttentionEnabled) {
                                    fleetAttentionQuery.refetch();
                                }
                            }}
                            disabled={isFleetBusy}
                        >
                            {isFleetBusy ? "Обновление..." : "Обновить"}
                        </button>
                    </div>
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    <label className="text-xs text-muted-foreground">
                        Клиент
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={fleetClientId}
                            onChange={(event) => {
                                const nextClientId = event.target.value;
                                const nextClient = fleetClients.find((client) => client.id === nextClientId);
                                setFleetClientId(nextClientId);
                                setFleetCompanyId(nextClient?.company_id ?? "");
                                setFleetBranchId("");
                            }}
                        >
                            <option value="">Выберите клиента</option>
                            {fleetClients.map((client) => (
                                <option key={client.id} value={client.id}>
                                    {client.name ?? client.slug ?? client.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Филиал
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={fleetBranchId}
                            onChange={(event) => handleFleetBranchSelect(event.target.value)}
                            disabled={!fleetClientId || fleetBranchesQuery.isLoading}
                        >
                            <option value="">Выберите филиал</option>
                            {fleetBranches.map((branch) => (
                                <option key={branch.id} value={branch.id}>
                                    {`${branch.name ?? branch.slug ?? branch.id} · ${branch.slug ?? String(branch.id).slice(0, 8)}`}
                                </option>
                            ))}
                        </select>
                    </label>
                    <div className="flex flex-wrap items-end gap-2">
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={() => void selectKnowledgeBranch()}
                            disabled={!fleetClientId || !fleetBranchId || isApplyingFleetContext}
                        >
                            {isApplyingFleetContext ? "Применение..." : "Применить контекст"}
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => void openRouteWithFleetContext(
                                "/integrations",
                                fleetClientId,
                                fleetCompanyId,
                                resolveBranchContextForClient(fleetClientId),
                            )}
                            disabled={!fleetClientId || isApplyingFleetContext}
                        >
                            Интеграции
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => void openRouteWithFleetContext(
                                "/",
                                fleetClientId,
                                fleetCompanyId,
                                resolveBranchContextForClient(fleetClientId),
                            )}
                            disabled={!fleetClientId || isApplyingFleetContext}
                        >
                            Заявки
                        </button>
                    </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                    Контекст филиала применяется автоматически после выбора в поле `Филиал`.
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                    Переходы в `Интеграции` и `Заявки` сохраняют branch context, если выбран филиал клиента.
                </div>
                {!fleetAttentionEnabled && (
                    <div className="mt-4 text-xs text-muted-foreground">
                        Fleet-сигналы отключены по умолчанию: включайте при необходимости оперативного контроля рисков и SLA.
                    </div>
                )}

                {fleetAttentionEnabled && (
                    <div className="mt-4 space-y-2">
                        {fleetAttentionQuery.isLoading && (
                            <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                                Загрузка fleet-сигналов...
                            </div>
                        )}

                        {fleetAttentionError && (
                            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
                                {fleetAttentionError}
                                <button
                                    type="button"
                                    className="btn-ghost ml-2"
                                    onClick={() => {
                                        setFleetAttentionError(null);
                                        fleetAttentionQuery.refetch();
                                    }}
                                >
                                    Повторить
                                </button>
                            </div>
                        )}

                        {!fleetAttentionError && fleetSummary && (
                            <div className="text-xs text-muted-foreground">
                                активных клиентов {fleetSummary.active_clients_total} · с риском {fleetSummary.clients_with_attention} ·
                                высокий {fleetSummary.high_risk_clients} · средний {fleetSummary.medium_risk_clients}
                            </div>
                        )}

                        {!fleetAttentionError && fleetAttentionItems.length > 0 && (
                            <div className="space-y-2">
                                {fleetAttentionItems.slice(0, 5).map((item) => (
                                    <div
                                        key={item.client_id}
                                        className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground"
                                    >
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <span className="font-medium text-foreground">
                                                {item.client_name ?? item.client_slug}
                                            </span>
                                            <span>risk {item.attention_level} · score {item.attention_score}</span>
                                        </div>
                                        <div className="mt-1">
                                            сервис {item.service_state} · stale {item.stale_branches} · outbox_failed_24h {item.outbox_failed_24h}
                                        </div>
                                        <div className="mt-2 flex flex-wrap items-center gap-2">
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={() => void applyConsoleContext({
                                                    companyId: item.company_id,
                                                    clientId: item.client_id,
                                                    branchId: null,
                                                    successMessage: "Контекст клиента обновлен",
                                                })}
                                                disabled={isFleetBusy}
                                            >
                                                В контекст клиента
                                            </button>
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={() => void openRouteWithFleetContext(
                                                    "/integrations",
                                                    item.client_id,
                                                    item.company_id,
                                                    resolveBranchContextForClient(item.client_id),
                                                )}
                                                disabled={isFleetBusy}
                                            >
                                                Интеграции
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {!fleetAttentionError && !fleetAttentionQuery.isLoading && fleetAttentionItems.length === 0 && (
                            <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                                Активных проблем во fleet-сигналах не найдено.
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    const renderBranchKnowledgeReadiness = () => {
        if (!selectedBranchContext) {
            return null;
        }
        const hasKnowledgeTag = Boolean((selectedBranchContext.knowledge_tag ?? "").trim());
        const hasBranchWorkingHours = Object.keys(selectedBranchWorkingHours).length > 0;
        const effectiveHoursSummary = formatWorkingHoursSummary(effectiveWorkingHours);
        const effectiveHoursSource = hasBranchWorkingHours ? "branch override" : "published pack";
        const canApplyPatch = canEdit
            && !applyBranchKnowledgePatchMutation.isPending
            && isBranchPatchDirty
            && hasBranchChangeReason
            && !parsedBranchWorkingHours.error;
        const branchPatchHint = !isBranchPatchDirty
            ? "Нет несохраненных изменений: измените тег знаний или часы работы."
            : !hasBranchChangeReason
            ? "Добавьте причину изменения для audit trail."
            : null;
        return (
            <div className="card-surface p-5" data-testid="knowledge-branch-readiness">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">Branch Knowledge Readiness</h2>
                        <p className="text-sm text-muted-foreground">
                            Оперативные настройки branch knowledge для текущего филиала.
                        </p>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        <div>{selectedBranchContext.name ?? selectedBranchContext.slug ?? selectedBranchContext.id}</div>
                        <div className="mt-1 font-mono">branch_id: {selectedBranchContext.id}</div>
                        <div className="mt-1">status: {selectedBranchContext.is_active ? "active" : "inactive"}</div>
                    </div>
                </div>

                <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        knowledge_tag: {hasKnowledgeTag ? selectedBranchContext.knowledge_tag : "не задан для этого филиала"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        working_hours: {hasBranchWorkingHours ? "заданы для филиала" : "не заданы (используется published pack)"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        onboarding: {selectedBranchContext.onboarding_state ?? "—"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        go_live: {selectedBranchContext.go_live_state ?? "pending"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        effective_hours: {effectiveHoursSummary}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        source: {effectiveHoursSource} · version: {currentQuery.data?.version_id ?? "не опубликована"}
                    </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                    Поля ниже изменяют данные только после кнопки `Сохранить branch change`.
                </div>

                {canEdit && (
                    <div className="mt-4 grid gap-3">
                        <label className="text-xs text-muted-foreground">
                            Тег знаний филиала (`knowledge_tag`, опционально)
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchKnowledgeTagDraft}
                                onChange={(event) => setBranchKnowledgeTagDraft(event.target.value)}
                                disabled={applyBranchKnowledgePatchMutation.isPending}
                                placeholder="Например: demo_salon_main"
                            />
                        </label>
                        <label className="text-xs text-muted-foreground">
                            Часы работы филиала (`working_hours`, JSON override)
                            <textarea
                                className="mt-1 min-h-[140px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                value={branchWorkingHoursDraft}
                                onChange={(event) => setBranchWorkingHoursDraft(event.target.value)}
                                disabled={applyBranchKnowledgePatchMutation.isPending}
                            />
                            <div className="mt-1">
                                Пустой объект <span className="font-mono">{`{}`}</span> очистит часы работы филиала.
                            </div>
                            {parsedBranchWorkingHours.error && (
                                <div className="mt-1 text-destructive">{parsedBranchWorkingHours.error}</div>
                            )}
                        </label>
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => {
                                    if (!effectiveWorkingHours || Object.keys(effectiveWorkingHours).length === 0) {
                                        toast.error("Нет published часов для подстановки");
                                        return;
                                    }
                                    setBranchWorkingHoursDraft(JSON.stringify(effectiveWorkingHours, null, 2));
                                }}
                                disabled={applyBranchKnowledgePatchMutation.isPending}
                            >
                                Подставить effective hours
                            </button>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => setBranchWorkingHoursDraft("{}")}
                                disabled={applyBranchKnowledgePatchMutation.isPending}
                            >
                                Очистить override
                            </button>
                        </div>
                        <label className="text-xs text-muted-foreground">
                            Причина изменения (audit)
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchChangeReason}
                                onChange={(event) => setBranchChangeReason(event.target.value)}
                                disabled={applyBranchKnowledgePatchMutation.isPending}
                                placeholder="Например: обновление часов после смены графика"
                            />
                        </label>
                        {branchPatchHint && <div className="text-xs text-muted-foreground">{branchPatchHint}</div>}
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => applyBranchKnowledgePatchMutation.mutate()}
                                disabled={!canApplyPatch}
                            >
                                {applyBranchKnowledgePatchMutation.isPending ? "Применение..." : "Сохранить branch change"}
                            </button>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => void openRouteWithFleetContext(
                                    "/team",
                                    selectedClientId || fleetClientId,
                                    selectedCompanyId || fleetCompanyId,
                                    selectedBranchId || null,
                                )}
                                disabled={isApplyingFleetContext}
                            >
                                Команда и мастера
                            </button>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => void openRouteWithFleetContext(
                                    "/calendar",
                                    selectedClientId || fleetClientId,
                                    selectedCompanyId || fleetCompanyId,
                                    selectedBranchId || null,
                                )}
                                disabled={isApplyingFleetContext}
                            >
                                Календарь
                            </button>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    if (!canRead) {
        return <AccessDenied message="Эта роль не имеет доступа к знаниям." />;
    }

    if (branchSelectionRequired) {
        if (isPlatformAdmin) {
            const fallbackBranchId = branchOptions[0]?.id ?? "";
            return (
                <div className="space-y-4">
                    {renderPlatformAdminFleetPanel()}
                    <div className="card-surface max-w-xl p-8" data-testid="knowledge-branch-gate-platform">
                        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется контекст</p>
                        <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите филиал во Fleet Control</h2>
                        <p className="text-sm text-muted-foreground mb-4">
                            Для Platform Admin контекст филиала применяется автоматически после выбора клиента и филиала.
                            Кнопка `Применить контекст` нужна как резервный шаг.
                        </p>
                        <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                            client_id: {selectedClientId || "—"} · branch_id: {selectedBranchId || "не выбран"}
                        </div>
                        {fallbackBranchId && (
                            <div className="mt-4">
                                <button
                                    className="btn-ghost"
                                    onClick={async () => {
                                        setIsSelectingBranch(true);
                                        try {
                                            await applyConsoleContext({
                                                companyId: selectedCompanyId || null,
                                                clientId: selectedClientId || null,
                                                branchId: fallbackBranchId,
                                                successMessage: "Филиал выбран из текущего клиента",
                                            });
                                        } finally {
                                            setIsSelectingBranch(false);
                                        }
                                    }}
                                    disabled={isSelectingBranch || !selectedClientId}
                                >
                                    {isSelectingBranch ? "Загрузка..." : "Открыть первый филиал (резерв)"}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            );
        }
        return (
            <div className="space-y-4">
                {renderPlatformAdminFleetPanel()}
                {renderBranchKnowledgeReadiness()}
                <div className="card-surface max-w-xl p-8" data-testid="knowledge-branch-gate">
                    <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                    <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите филиал</h2>
                    <p className="text-sm text-muted-foreground mb-6">
                        Управление знаниями выполняется отдельно для каждого филиала.
                    </p>
                    {branchOptions.length > 0 ? (
                        <select
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={branchId}
                            onChange={(event) => setBranchId(event.target.value)}
                        >
                            <option value="">Выберите филиал</option>
                            {branchOptions.map((branch) => (
                                <option key={branch.id} value={branch.id ?? ""}>
                                    {`${branch.name ?? branch.slug ?? branch.id} · ${branch.slug ?? String(branch.id).slice(0, 8)}`}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <div className="rounded-lg border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
                            Нет доступных филиалов.
                        </div>
                    )}
                    <div className="mt-6 flex justify-end">
                        <button
                            className="btn-primary"
                            onClick={async () => {
                                if (!branchId) {
                                    toast.error("Выберите филиал");
                                    return;
                                }
                                setIsSelectingBranch(true);
                                try {
                                    await applyConsoleContext({
                                        companyId: selectedCompanyId || null,
                                        clientId: selectedClientId || null,
                                        branchId,
                                        successMessage: "Филиал выбран",
                                    });
                                } finally {
                                    setIsSelectingBranch(false);
                                }
                            }}
                            disabled={!branchId || isSelectingBranch || branchOptions.length === 0}
                        >
                            {isSelectingBranch ? "Загрузка..." : "Продолжить"}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="knowledge-studio">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="badge mb-3">Knowledge Studio</div>
                    <h1 className="text-2xl font-semibold">Управление знаниями</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Draft → Validate → Preview → Publish → History → Rollback. Публикация только после валидного draft.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${canEdit ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}>
                        {canEdit ? "write" : "read-only"}
                    </span>
                    {lastPublishAt && (
                        <span className="text-xs text-muted-foreground">
                            Published: {new Date(lastPublishAt).toLocaleString("ru-RU")}
                        </span>
                    )}
                </div>
            </div>

            {renderPlatformAdminFleetPanel()}
            {renderBranchKnowledgeReadiness()}

            {gatewayError && !apiUnavailable && (
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-700">
                    <div>{gatewayError}</div>
                    <button
                        type="button"
                        className="btn-ghost mt-3"
                        onClick={() => {
                            setGatewayError(null);
                            currentQuery.refetch();
                            historyQuery.refetch();
                            candidatesQuery.refetch();
                            specialistsQuery.refetch();
                            allSpecialistsQuery.refetch();
                            if (isPlatformAdmin && fleetClientId) {
                                fleetBranchesQuery.refetch();
                            }
                            if (isPlatformAdmin && fleetAttentionEnabled) {
                                fleetAttentionQuery.refetch();
                            }
                        }}
                    >
                        Повторить запросы
                    </button>
                </div>
            )}

            {apiUnavailable && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                    <div>Knowledge API недоступен. UI работает в режиме просмотра до появления endpoints.</div>
                    <button
                        type="button"
                        className="btn-ghost mt-3"
                        onClick={() => {
                            setApiUnavailable(false);
                            currentQuery.refetch();
                            historyQuery.refetch();
                        }}
                    >
                        Проверить снова
                    </button>
                </div>
            )}

            {!canEdit && (
                <div className="rounded-xl border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
                    Роль {role}: доступ только для просмотра. Публикация и откат доступны owner/admin/platform admin.
                </div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="card-surface p-4">
                    <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-4">
                        Flow
                    </h2>
                    <div className="flex flex-col gap-2">
                        {KNOWLEDGE_STEPS.map((step, index) => {
                            const active = index === stepIndex;
                            const done = stepStatus[step.id];
                            return (
                                <button
                                    key={step.id}
                                    type="button"
                                    onClick={() => setStepIndex(index)}
                                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition ${
                                        active ? "border-primary bg-primary/10" : "border-border/60 hover:bg-muted"
                                    }`}
                                >
                                    <div>
                                        <div className="font-medium">{step.label}</div>
                                        <div className="text-xs text-muted-foreground">{step.hint}</div>
                                    </div>
                                    {done && <span className="text-xs text-green-600">✓</span>}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="card-surface p-6 lg:col-span-2">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold">{currentStep.label}</h2>
                        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            {currentStep.hint}
                        </span>
                    </div>

                    {currentStep.id === "draft" && (
                        <div className="mt-4 space-y-4">
                            <div className="flex flex-wrap items-center gap-3">
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => setDraftText(currentText)}
                                    disabled={!currentText || !canEdit}
                                >
                                    Загрузить current в draft
                                </button>
                                <span className="text-xs text-muted-foreground">
                                    Draft хранится локально до публикации.
                                </span>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                                <div className="flex flex-wrap items-start justify-between gap-2">
                                    <div>
                                        <p className="text-sm font-medium">Structured Draft Builder</p>
                                        <p className="text-xs text-muted-foreground">
                                            Обновите часы и каталог услуг без ручного редактирования JSON.
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        className="btn-primary"
                                        onClick={applyStructuredDraft}
                                        disabled={!canEdit}
                                    >
                                        Собрать structured draft
                                    </button>
                                </div>

                                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-medium">Client Pack Inspector</p>
                                        <span className="text-xs text-muted-foreground">
                                            полей {inspectorSummary.flattenedFieldsCount}
                                        </span>
                                    </div>
                                    <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
                                        <div className="rounded-lg border border-border/60 px-2 py-1">
                                            services_catalog: {inspectorSummary.servicesCount}
                                        </div>
                                        <div className="rounded-lg border border-border/60 px-2 py-1">
                                            price_list: {inspectorSummary.priceRowsCount}
                                        </div>
                                        <div className="rounded-lg border border-border/60 px-2 py-1">
                                            booking.collect_fields: {inspectorSummary.collectFieldsCount}
                                        </div>
                                        <div className="rounded-lg border border-border/60 px-2 py-1">
                                            policy заполнено: {inspectorSummary.policyFilledCount}/4
                                        </div>
                                    </div>
                                    <label className="mt-3 block text-xs text-muted-foreground">
                                        Поиск по ключам Client_Pack
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={packInspectorQuery}
                                            onChange={(event) => setPackInspectorQuery(event.target.value)}
                                            placeholder="Например: client_pack.booking.collect_fields"
                                        />
                                    </label>
                                    <div className="mt-2 max-h-44 overflow-auto rounded-lg border border-border/60 bg-muted/30 p-2 text-xs">
                                        {filteredPackPaths.length === 0 && (
                                            <div className="text-muted-foreground">Совпадений не найдено.</div>
                                        )}
                                        {filteredPackPaths.map((item) => (
                                            <div key={`${item.path}-${item.preview}`} className="mb-1">
                                                <span className="font-mono text-foreground">{item.path}</span>
                                                <span className="text-muted-foreground"> = {item.preview}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                                    <label className="text-xs text-muted-foreground">
                                        Дни работы
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedHours.days}
                                            onChange={(event) =>
                                                setGuidedHours((prev) => ({ ...prev, days: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Пн-Вс"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Открытие
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedHours.open}
                                            onChange={(event) =>
                                                setGuidedHours((prev) => ({ ...prev, open: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="10:00"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Закрытие
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedHours.close}
                                            onChange={(event) =>
                                                setGuidedHours((prev) => ({ ...prev, close: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="21:00"
                                        />
                                    </label>
                                </div>

                                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                    <label className="text-xs text-muted-foreground">
                                        Название салона
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.salonName}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, salonName: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Например: Truffles Beauty"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Город
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.city}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, city: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Алматы"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground sm:col-span-2">
                                        Полный адрес
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.addressFull}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, addressFull: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="ул. Пример, 10"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Языки общения (через запятую)
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.languages}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, languages: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="ru, kk"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Guest policy
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.guestPolicy}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, guestPolicy: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="например: работаем только по записи"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground sm:col-span-2">
                                        Кратко об услугах
                                        <textarea
                                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedSalonProfile.servicesSummary}
                                            onChange={(event) =>
                                                setGuidedSalonProfile((prev) => ({ ...prev, servicesSummary: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Короткое описание специализации салона"
                                        />
                                    </label>
                                </div>

                                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                    <label className="text-xs text-muted-foreground">
                                        Booking: collect_fields (через запятую)
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedBooking.collectFields}
                                            onChange={(event) =>
                                                setGuidedBooking((prev) => ({ ...prev, collectFields: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="service, date, time, name, phone"
                                        />
                                    </label>
                                    <label className="flex items-center gap-2 rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                                        <input
                                            type="checkbox"
                                            checked={guidedBooking.botCanConfirm}
                                            onChange={(event) =>
                                                setGuidedBooking((prev) => ({ ...prev, botCanConfirm: event.target.checked }))
                                            }
                                            disabled={!canEdit}
                                        />
                                        Booking: bot_can_confirm
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Policy: payment_info
                                        <textarea
                                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedPolicy.paymentInfo}
                                            onChange={(event) =>
                                                setGuidedPolicy((prev) => ({ ...prev, paymentInfo: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Как проходит оплата"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Policy: reschedule
                                        <textarea
                                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedPolicy.reschedule}
                                            onChange={(event) =>
                                                setGuidedPolicy((prev) => ({ ...prev, reschedule: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Правила переноса"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Policy: cancel
                                        <textarea
                                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedPolicy.cancel}
                                            onChange={(event) =>
                                                setGuidedPolicy((prev) => ({ ...prev, cancel: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Правила отмены"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        Policy: discounts
                                        <textarea
                                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={guidedPolicy.discounts}
                                            onChange={(event) =>
                                                setGuidedPolicy((prev) => ({ ...prev, discounts: event.target.value }))
                                            }
                                            disabled={!canEdit}
                                            placeholder="Скидки и акции"
                                        />
                                    </label>
                                </div>

                                <div className="mt-4 space-y-2">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-medium">Услуги</p>
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={addGuidedService}
                                            disabled={!canEdit}
                                        >
                                            Добавить услугу
                                        </button>
                                    </div>
                                    {guidedServices.map((service) => (
                                        <div key={service.id} className="flex items-center gap-2">
                                            <input
                                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={service.name}
                                                onChange={(event) => updateGuidedService(service.id, event.target.value)}
                                                disabled={!canEdit}
                                                placeholder="Название услуги"
                                            />
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={() => removeGuidedService(service.id)}
                                                disabled={!canEdit || guidedServices.length <= 1}
                                            >
                                                Удалить
                                            </button>
                                        </div>
                                    ))}
                                </div>

                                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-medium">Мастера филиала</p>
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={() => void openRouteWithFleetContext(
                                                "/team",
                                                selectedClientId || fleetClientId,
                                                selectedCompanyId || fleetCompanyId,
                                                selectedBranchId || null,
                                            )}
                                            disabled={isFleetBusy}
                                        >
                                            Управлять в Team
                                        </button>
                                    </div>
                                    <div className="mt-2 text-xs text-muted-foreground">
                                        {specialistsQuery.isLoading && "Загрузка мастеров..."}
                                        {!specialistsQuery.isLoading && specialists.length === 0 && !missingBranchSpecialistsButClientHasSome && "В выбранном филиале пока нет мастеров в Calendar."}
                                        {!allSpecialistsQuery.isLoading && allSpecialists.length > 0 && (
                                            <div className="mt-1">
                                                Всего по клиенту: {allSpecialists.length}
                                            </div>
                                        )}
                                    </div>
                                    {!specialistsQuery.isLoading && missingBranchSpecialistsButClientHasSome && (
                                        <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
                                            В этом филиале мастеров нет. В других филиалах клиента найдено {specialistsInOtherBranches.length}.
                                            {specialistsByBranch.length > 0 && (
                                                <div className="mt-1">
                                                    {specialistsByBranch
                                                        .slice(0, 3)
                                                        .map((item) => `${item.label}: ${item.count}`)
                                                        .join(" · ")}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {!specialistsQuery.isLoading && specialists.length > 0 && (
                                        <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
                                            {specialists.slice(0, 6).map((specialist) => (
                                                <div key={specialist.id}>
                                                    {specialist.name} · услуг {specialist.services?.length ?? 0}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                            <textarea
                                className="min-h-[240px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
                                placeholder="Вставьте YAML/JSON draft знаний..."
                                value={draftText}
                                onChange={(event) => {
                                    setDraftText(event.target.value);
                                    setValidation((prev) => prev.ran ? { ...prev, ran: false } : prev);
                                }}
                                disabled={!canEdit}
                            />
                            <div className="text-xs text-muted-foreground">
                                {draftText.trim().length} символов
                            </div>
                        </div>
                    )}

                    {currentStep.id === "validate" && (
                        <div className="mt-4 space-y-4">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => validateMutation.mutate()}
                                disabled={!canEdit || apiUnavailable || !draftText.trim() || validateMutation.isPending}
                            >
                                {validateMutation.isPending ? "Проверка..." : "Запустить валидацию"}
                            </button>
                            {validation.ran && (
                                <div className="space-y-3">
                                    <div className={`rounded-lg border p-3 text-sm ${hasErrors ? "border-destructive/40 bg-destructive/10 text-destructive" : "border-border/60 bg-muted/30"}`}>
                                        {hasErrors ? "Ошибки найдены" : "Ошибок нет"}
                                    </div>
                                    {validation.errors.length > 0 && (
                                        <ul className="list-disc space-y-1 pl-5 text-sm text-destructive">
                                            {validation.errors.map((error, idx) => (
                                                <li key={`${error}-${idx}`}>{error}</li>
                                            ))}
                                        </ul>
                                    )}
                                    {validation.warnings.length > 0 && (
                                        <div>
                                            <p className="text-sm font-medium text-muted-foreground">Warnings</p>
                                            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                                                {validation.warnings.map((warning, idx) => (
                                                    <li key={`${warning}-${idx}`}>{warning}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {isDraftDirty && (
                                        <div className="text-xs text-muted-foreground">
                                            Draft изменён после валидации — повторите Validate перед Publish.
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {currentStep.id === "preview" && (
                        <div className="mt-4 space-y-4">
                            {validation.diff ? (
                                <pre className="max-h-[340px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                    {validation.diff}
                                </pre>
                            ) : (
                                <div className="grid gap-4 lg:grid-cols-2">
                                    <div>
                                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Current</p>
                                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                            {currentText || "Нет данных"}
                                        </pre>
                                    </div>
                                    <div>
                                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Draft</p>
                                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                            {draftText || "Draft пуст"}
                                        </pre>
                                    </div>
                                </div>
                            )}
                            {!validation.ran && (
                                <p className="text-sm text-muted-foreground">
                                    Запустите Validate, чтобы получить diff.
                                </p>
                            )}
                        </div>
                    )}

                    {currentStep.id === "publish" && (
                        <div className="mt-4 space-y-4">
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                                <div className="flex items-center justify-between">
                                    <span>Validation</span>
                                    <span className={validation.ran && !hasErrors ? "text-green-600" : "text-muted-foreground"}>
                                        {validation.ran ? (hasErrors ? "errors" : "ok") : "not run"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span>Warnings</span>
                                    <span className={hasWarnings ? "text-amber-600" : "text-muted-foreground"}>
                                        {hasWarnings ? validation.warnings.length : "0"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span>Draft dirty</span>
                                    <span className={isDraftDirty ? "text-amber-600" : "text-muted-foreground"}>
                                        {isDraftDirty ? "yes" : "no"}
                                    </span>
                                </div>
                            </div>

                            {hasWarnings && (
                                <label className="flex items-start gap-2 text-sm text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        className="mt-1"
                                        checked={ackWarnings}
                                        onChange={(event) => setAckWarnings(event.target.checked)}
                                        disabled={!canEdit}
                                    />
                                    Я подтверждаю предупреждения и понимаю риски изменений.
                                </label>
                            )}

                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => publishMutation.mutate()}
                                disabled={!canPublish || publishMutation.isPending}
                            >
                                {publishMutation.isPending ? "Публикация..." : "Опубликовать"}
                            </button>
                            {!canPublish && (
                                <p className="text-xs text-muted-foreground">
                                    Publish доступен только после валидации без ошибок и подтверждения warnings.
                                </p>
                            )}
                        </div>
                    )}

                    {currentStep.id === "history" && (
                        <div className="mt-4 space-y-4">
                            {historyItems.length === 0 && (
                                <p className="text-sm text-muted-foreground">История пока пуста.</p>
                            )}
                            {historyItems.length > 0 && (
                                <div className="space-y-3">
                                    {historyItems.map((item, index) => (
                                        <label
                                            key={item.id ?? `history-${index}`}
                                            className={`flex cursor-pointer items-start justify-between rounded-lg border p-3 text-sm ${
                                                selectedVersionId === item.id ? "border-primary bg-primary/10" : "border-border/60"
                                            }`}
                                        >
                                            <div>
                                                <div className="font-medium">
                                                    {item.summary || item.id || "unknown-version"}
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    {item.status ?? "status неизвестен"}
                                                </div>
                                                {item.published_at && (
                                                    <div className="text-xs text-muted-foreground">
                                                        Published: {new Date(item.published_at).toLocaleString("ru-RU")}
                                                    </div>
                                                )}
                                            </div>
                                            <input
                                                type="radio"
                                                name="knowledge-version"
                                                className="mt-1"
                                                value={item.id ?? ""}
                                                checked={selectedVersionId === item.id}
                                                onChange={() => setSelectedVersionId(item.id ?? "")}
                                                disabled={!item.id}
                                            />
                                        </label>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {currentStep.id === "rollback" && (
                        <div className="mt-4 space-y-4">
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                                <div className="flex items-center justify-between">
                                    <span>Выбранная версия</span>
                                    <span className="font-mono text-xs">{selectedVersionId || "не выбрана"}</span>
                                </div>
                                {lastRollbackAt && (
                                    <div className="mt-2 text-xs text-muted-foreground">
                                        Last rollback: {new Date(lastRollbackAt).toLocaleString("ru-RU")}
                                    </div>
                                )}
                            </div>
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => {
                                    if (!selectedVersionId) {
                                        toast.error("Выберите версию для rollback");
                                        return;
                                    }
                                    setShowRollbackConfirm(true);
                                }}
                                disabled={!canEdit || apiUnavailable || !selectedVersionId || rollbackMutation.isPending}
                            >
                                {rollbackMutation.isPending ? "Откат..." : "Выполнить rollback"}
                            </button>
                            <p className="text-xs text-muted-foreground">
                                Rollback возвращает выбранную версию и фиксируется в audit.
                            </p>
                        </div>
                    )}

                    <div className="mt-8 flex items-center justify-between border-t border-border/60 pt-4">
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
                            onClick={() => setStepIndex((prev) => Math.min(prev + 1, KNOWLEDGE_STEPS.length - 1))}
                            disabled={stepIndex === KNOWLEDGE_STEPS.length - 1}
                        >
                            Далее
                        </button>
                    </div>
                </div>
            </div>

            <div className="card-surface mt-6 p-5" data-testid="learning-candidates">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <h2 className="text-lg font-semibold">Кандидаты обучения</h2>
                        <p className="text-sm text-muted-foreground">
                            Pending-кандидаты из ответов менеджера. Одобрение добавляет их в draft.
                        </p>
                    </div>
                    {!canEdit && (
                        <span className="text-xs text-muted-foreground">Только owner/admin</span>
                    )}
                </div>

                {candidatesQuery.isLoading && (
                    <p className="mt-4 text-sm text-muted-foreground">Загрузка кандидатов...</p>
                )}

                {!candidatesQuery.isLoading && learningCandidates.length === 0 && (
                    <p className="mt-4 text-sm text-muted-foreground">Пока нет pending-кандидатов.</p>
                )}

                {!candidatesQuery.isLoading && learningCandidates.length > 0 && (
                    <div className="mt-4 space-y-4">
                        {learningCandidates.map((candidate) => (
                            <div
                                key={candidate.id ?? candidate.question_text}
                                className="rounded-lg border border-border/60 p-4"
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                                    <span>Статус: {candidate.status ?? "unknown"}</span>
                                    <span>Создано: {formatTimestamp(candidate.created_at)}</span>
                                    <span>Retention: {formatTimestamp(candidate.retention_expires_at)}</span>
                                </div>
                                <div className="mt-3 text-sm">
                                    <div className="font-medium">Вопрос</div>
                                    <div className="text-muted-foreground">{candidate.question_text}</div>
                                </div>
                                <div className="mt-3 text-sm">
                                    <div className="font-medium">Ответ</div>
                                    <div className="text-muted-foreground">{candidate.response_text}</div>
                                </div>
                                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                    <span>Источник: {candidate.source_name ?? "—"}</span>
                                    <span>Роль: {candidate.source_role ?? "—"}</span>
                                </div>
                                <div className="mt-4 flex flex-wrap items-center gap-2">
                                    <button
                                        type="button"
                                        className="btn-primary"
                                        onClick={() => {
                                            if (candidate.id) {
                                                approveCandidateMutation.mutate(candidate.id);
                                            }
                                        }}
                                        disabled={
                                            !candidate.id
                                            || !canEdit
                                            || !candidate.can_approve
                                            || approveCandidateMutation.isPending
                                        }
                                    >
                                        {approveCandidateMutation.isPending ? "Одобрение..." : "Одобрить"}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={() => {
                                            if (candidate.id) {
                                                rejectCandidateMutation.mutate(candidate.id);
                                            }
                                        }}
                                        disabled={!candidate.id || !canEdit || rejectCandidateMutation.isPending}
                                    >
                                        {rejectCandidateMutation.isPending ? "Отклонение..." : "Отклонить"}
                                    </button>
                                    {!candidate.can_approve && candidate.ineligible_reason && (
                                        <span className="text-xs text-muted-foreground">
                                            Блокировка: {candidate.ineligible_reason}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showRollbackConfirm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="card-surface w-full max-w-lg space-y-4 p-6">
                        <div>
                            <h3 className="text-lg font-semibold">Подтвердите rollback</h3>
                            <p className="text-sm text-muted-foreground">
                                Версия: {selectedVersionId || "—"}. Откат изменит активные знания и требует причины.
                            </p>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Причина</label>
                            <textarea
                                className="min-h-[90px] w-full rounded-lg border border-border/60 bg-background p-3 text-sm"
                                value={rollbackReason}
                                onChange={(event) => setRollbackReason(event.target.value)}
                                placeholder="Например: ошибка в опубликованном pack, откат до стабильной версии"
                            />
                        </div>
                        <div className="flex flex-wrap justify-end gap-2">
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => {
                                    setShowRollbackConfirm(false);
                                    setRollbackReason("");
                                }}
                                disabled={rollbackMutation.isPending}
                            >
                                Отмена
                            </button>
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => {
                                    const reason = rollbackReason.trim();
                                    if (!reason) {
                                        toast.error("Укажите причину");
                                        return;
                                    }
                                    rollbackMutation.mutate(reason);
                                }}
                                disabled={rollbackMutation.isPending}
                            >
                                {rollbackMutation.isPending ? "Подтверждение..." : "Подтвердить rollback"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function KnowledgePage() {
    const { data: session } = useSession();

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра знаний.
            </div>
        );
    }

    return <KnowledgeStudio session={session} />;
}
