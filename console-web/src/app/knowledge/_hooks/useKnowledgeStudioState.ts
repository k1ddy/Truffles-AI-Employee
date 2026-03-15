"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import axios from "axios";
import toast from "react-hot-toast";

import {
    adminApi,
    authApi,
    businessApi,
    canAccessConsole,
    confirmationsApi,
    knowledgeApi,
    learningApi,
    type KnowledgeHistoryItem,
    type LearningCandidate,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { MISSING_LABELS } from "@/components/provisioning-wizard-domain";
import api from "@/lib/api";
import { applyConsoleScopeContext } from "@/lib/console-scope-gate";
import type { components } from "@/types/api.generated";

type SessionData = unknown;
type FleetAttentionItem = components["schemas"]["ConsoleFleetAttentionItem"];
type FleetClient = components["schemas"]["ConsoleClient"];
type FleetBranch = components["schemas"]["ConsoleBranch"];
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

const OWNER_REMEDIATION_HINTS: Record<string, string> = {
    "client_pack.guest_policy": "Опишите правила для новых или гостевых клиентов: кого принимаете, нужны ли ограничения или депозит.",
    "client_pack.policy.payment_info": "Добавьте понятное объяснение оплаты: наличные, карта, предоплата, когда именно клиент платит.",
    "client_pack.policy.reschedule": "Опишите, как клиент может перенести запись и за сколько времени это допустимо.",
    "client_pack.policy.cancel": "Опишите правила отмены: есть ли штраф, сколько времени на бесплатную отмену и кто подтверждает отмену.",
    "client_pack.policy.discounts": "Опишите действующие скидки, акции и ограничения: кому доступны, как считаются, можно ли суммировать.",
};
const LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX = "Lossy structured field rewrite blocked: ";

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
    draftSaved: boolean;
};

function shouldOpenSupportTools(role: string): boolean {
    return role === "admin" || role === "platform_admin";
}

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

function formatKnowledgeValidationIssue(message: string): { title: string; detail?: string } {
    if (message.startsWith(LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX)) {
        const path = message.slice(LOSSY_STRUCTURED_REWRITE_ERROR_PREFIX.length).trim();
        const label = MISSING_LABELS[path] ?? path;
        return {
            title: `Нельзя упростить structured поле: ${label}`,
            detail: "В этом филиале поле хранится как объект. Оставьте guided-поле пустым, чтобы сохранить серверное значение, или редактируйте JSON без смены типа поля.",
        };
    }
    const prefix = "Missing required field:";
    if (!message.startsWith(prefix)) {
        return { title: message };
    }
    const path = message.slice(prefix.length).trim();
    const label = MISSING_LABELS[path] ?? path;
    return {
        title: `Не заполнено: ${label}`,
        detail: OWNER_REMEDIATION_HINTS[path] ?? `Проверьте и заполните поле «${label}» в knowledge pack этого филиала.`,
    };
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

function extractApiErrorMessage(error: unknown): string | null {
    if (!axios.isAxiosError(error)) {
        return null;
    }
    const payload = error.response?.data as { error?: { message?: unknown } } | undefined;
    const message = payload?.error?.message;
    if (typeof message !== "string") {
        return null;
    }
    const trimmed = message.trim();
    return trimmed || null;
}

function extractApiErrorValidationIssues(error: unknown): string[] {
    if (!axios.isAxiosError(error)) {
        return [];
    }
    const payload = error.response?.data as { error?: { details?: { errors?: unknown } } } | undefined;
    const issues = payload?.error?.details?.errors;
    return normalizeStringList(issues);
}

function resolveKnowledgeActionErrorMessage(error: unknown): string {
    if (isGatewayLikeError(error)) {
        return "Сервис знаний временно недоступен (gateway). Повторите позже или проверьте OPS.";
    }
    const code = extractApiErrorCode(error);
    if (code === "CLIENT_SELECTION_REQUIRED") {
        return "Выберите клиента в контексте Console и повторите.";
    }
    if (code === "BRANCH_SELECTION_REQUIRED") {
        return "Выберите филиал в контексте Console и повторите.";
    }
    if (code === "KNOWLEDGE_INVALID") {
        const issues = extractApiErrorValidationIssues(error);
        if (issues.length > 0) {
            return formatKnowledgeValidationIssue(issues[0]).title;
        }
    }
    const apiMessage = extractApiErrorMessage(error);
    if (apiMessage) {
        return apiMessage;
    }
    if (error instanceof Error && error.message.trim()) {
        return error.message;
    }
    return "Не удалось выполнить действие. Проверьте контекст и попробуйте снова.";
}

function knowledgeSyncStatusClass(status?: string | null): string {
    if (status === "ready") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "failed") {
        return "bg-red-100 text-red-800";
    }
    return "bg-slate-100 text-slate-700";
}

function isKnowledgeSyncPending(status?: string | null): boolean {
    return status === "pending";
}

function resolveKnowledgeSyncMessage(
    status?: string | null,
): string {
    if (status === "failed") {
        return "Синхронизация требует внимания. Повторите ее перед проверкой консультанта.";
    }
    if (status === "ready") {
        return "Последняя версия опубликована и синхронизирована.";
    }
    if (status === "pending") {
        return "Синхронизация выполняется. Проверка консультанта откроется после завершения.";
    }
    return "Синхронизация еще не подтверждена.";
}

function resolveKnowledgeSyncDetails(error?: string | null): string | null {
    if (!error || !error.trim()) {
        return null;
    }
    return `Техническая причина: ${error}`;
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

function isStructuredKnowledgeValue(value: unknown): boolean {
    return Boolean(value) && typeof value === "object";
}

function applyGuidedTextField(baseValue: unknown, nextValue: string): unknown {
    const trimmed = nextValue.trim();
    if (typeof baseValue === "string") {
        return trimmed;
    }
    if (trimmed.length > 0) {
        return trimmed;
    }
    if (baseValue !== null && baseValue !== undefined) {
        return baseValue;
    }
    return "";
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
        payment_info: applyGuidedTextField(policy.payment_info, policyProfile.paymentInfo),
        reschedule: applyGuidedTextField(policy.reschedule, policyProfile.reschedule),
        cancel: applyGuidedTextField(policy.cancel, policyProfile.cancel),
        discounts: applyGuidedTextField(policy.discounts, policyProfile.discounts),
    };

    root.client_pack = {
        ...clientPack,
        salon: nextSalon,
        guest_policy: applyGuidedTextField(clientPack.guest_policy, salonProfile.guestPolicy),
        booking: nextBooking,
        policy: nextPolicy,
        services_catalog: {
            ...servicesCatalog,
            services: nextServices,
        },
    };

    return root;
}



export function useKnowledgeStudioState({ session }: { session: SessionData }) {

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
    const [lastValidatedDraftHash, setLastValidatedDraftHash] = useState<string | null>(null);
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
        draftSaved: true,
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
    const supportToolsDefaultOpen = shouldOpenSupportTools(role);
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

    useEffect(() => {
        setDraftText("");
        setValidation({
            ran: false,
            errors: [],
            warnings: [],
            diff: "",
            draftSaved: true,
        });
        setLastValidatedDraft(null);
        setLastValidatedDraftHash(null);
        setAckWarnings(false);
    }, [selectedClientId, selectedBranchId]);

    const currentQuery = useQuery({
        queryKey: ["knowledge-current", selectedClientId, selectedBranchId],
        queryFn: async () => {
            const response = await knowledgeApi.getCurrent();
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
        refetchInterval: (query) => (isKnowledgeSyncPending(query.state.data?.sync_status) ? 5000 : false),
    });

    const historyQuery = useQuery({
        queryKey: ["knowledge-history", selectedClientId, selectedBranchId],
        queryFn: async () => {
            const response = await knowledgeApi.history();
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canRead && !branchSelectionRequired,
        retry: false,
        refetchInterval: (query) =>
            (query.state.data?.items ?? []).some((item: { sync_status?: string | null }) => isKnowledgeSyncPending(item?.sync_status))
                ? 5000
                : false,
    });

    const consultantVerificationReadinessQuery = useQuery({
        queryKey: ["knowledge-consultant-verification-readiness", selectedClientId, selectedBranchId],
        queryFn: async () => {
            const response = await businessApi.getConsultantVerificationReadiness();
            return response.data;
        },
        enabled: !!session && !!meData && !apiUnavailable && canEdit && !branchSelectionRequired && !!selectedBranchId,
        retry: false,
        refetchInterval: isKnowledgeSyncPending(currentQuery.data?.sync_status) ? 5000 : false,
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
            setGatewayError("Список клиентов по сети временно недоступен (gateway).");
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
            setGatewayError("Список филиалов по сети временно недоступен (gateway).");
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
            setFleetAttentionError("Сигналы по сети клиентов временно недоступны. Попробуйте обновить позже.");
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

    const workspacePayloadObject = useMemo(() => {
        const payload = currentQuery.data?.edit_base_payload ?? currentQuery.data?.payload;
        if (payload && typeof payload === "object" && !Array.isArray(payload)) {
            return payload as Record<string, unknown>;
        }
        return null;
    }, [currentQuery.data]);
    const clientPackObject = useMemo(() => {
        if (!workspacePayloadObject) {
            return {} as Record<string, unknown>;
        }
        return ensureObject(workspacePayloadObject.client_pack);
    }, [workspacePayloadObject]);
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
            .filter((value) => {
                if (typeof value === "string") {
                    return value.trim().length > 0;
                }
                return isStructuredKnowledgeValue(value);
            }).length;
        return {
            servicesCount: services.length,
            priceRowsCount: priceList.length,
            collectFieldsCount: collectFields.length,
            policyFilledCount,
            flattenedFieldsCount: flatClientPackPaths.length,
        };
    }, [clientPackObject, flatClientPackPaths.length]);
    const structuredGuidedFields = useMemo(() => {
        const policy = ensureObject(clientPackObject.policy);
        const items: string[] = [];
        if (isStructuredKnowledgeValue(clientPackObject.guest_policy)) {
            items.push("guest_policy");
        }
        if (isStructuredKnowledgeValue(policy.payment_info)) {
            items.push("policy.payment_info");
        }
        if (isStructuredKnowledgeValue(policy.reschedule)) {
            items.push("policy.reschedule");
        }
        if (isStructuredKnowledgeValue(policy.cancel)) {
            items.push("policy.cancel");
        }
        if (isStructuredKnowledgeValue(policy.discounts)) {
            items.push("policy.discounts");
        }
        return items;
    }, [clientPackObject]);

    const currentText = useMemo(() => {
        if (!currentQuery.data) {
            return "";
        }
        const payload = currentQuery.data.content ?? currentQuery.data.payload ?? currentQuery.data;
        return formatPayload(payload);
    }, [currentQuery.data]);
    const draftServerText = useMemo(() => {
        if (!currentQuery.data) {
            return "";
        }
        const payload = currentQuery.data.draft_content ?? currentQuery.data.draft_payload;
        return formatPayload(payload);
    }, [currentQuery.data]);
    const editBaseText = useMemo(() => {
        if (!currentQuery.data) {
            return "";
        }
        const payload = currentQuery.data.edit_base_content ?? currentQuery.data.edit_base_payload;
        return formatPayload(payload);
    }, [currentQuery.data]);
    const editBaseSource = currentQuery.data?.edit_base_source ?? "none";
    const editBaseUpdatedAt = currentQuery.data?.edit_base_updated_at ?? null;
    const draftUpdatedAt = currentQuery.data?.draft_updated_at ?? null;
    const hasSavedDraft = Boolean(currentQuery.data?.draft_version_id && draftServerText.trim().length > 0);
    const currentSyncStatus = currentQuery.data?.sync_status ?? null;
    const currentSyncStatusLabel = currentQuery.data?.sync_status_label ?? "Синхронизация не подтверждена";
    const currentSyncError = currentQuery.data?.sync_error ?? null;
    const currentSafeMode = Boolean(currentQuery.data?.knowledge_safe_mode);
    const currentSafeModeReason = currentQuery.data?.knowledge_safe_mode_reason ?? null;
    const currentSyncPending = isKnowledgeSyncPending(currentSyncStatus);
    const currentSyncFailed = currentSyncStatus === "failed" || currentSafeMode;
    const currentSyncBlocked = currentSyncPending || currentSyncFailed;
    const currentSyncDetails = currentSyncPending
        ? null
        : resolveKnowledgeSyncDetails(currentSyncError ?? currentSafeModeReason);

    const historyItems = useMemo(
        () => extractHistoryItems(historyQuery.data),
        [historyQuery.data]
    );
    const learningCandidateItems = useMemo(
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
        return extractPayloadWorkingHours(workspacePayloadObject);
    }, [selectedBranchWorkingHours, workspacePayloadObject]);
    const hasBranchWorkingHours = Object.keys(selectedBranchWorkingHours).length > 0;
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
        if (draftText.trim().length > 0) {
            return;
        }
        if (!editBaseText.trim()) {
            return;
        }
        setDraftText(editBaseText);
    }, [draftText, editBaseText]);

    useEffect(() => {
        setGuidedHours(extractGuidedHours(workspacePayloadObject));
        const extractedServices = extractGuidedServices(workspacePayloadObject);
        if (extractedServices.length > 0) {
            setGuidedServices(extractedServices);
        } else {
            setGuidedServices([{ id: `svc-${Date.now()}`, name: "" }]);
        }
        setGuidedSalonProfile(extractGuidedSalonProfile(workspacePayloadObject));
        setGuidedBooking(extractGuidedBooking(workspacePayloadObject));
        setGuidedPolicy(extractGuidedPolicy(workspacePayloadObject));
    }, [workspacePayloadObject, selectedBranchId]);

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
    const consultantVerificationReadiness = consultantVerificationReadinessQuery.data?.readiness;
    const consultantVerificationReadinessErrorMessage = consultantVerificationReadinessQuery.error
        ? resolveKnowledgeActionErrorMessage(consultantVerificationReadinessQuery.error)
        : null;
    const compareRequired = consultantVerificationReadiness?.compare_required ?? false;
    const compareReady = !consultantVerificationReadinessQuery.isError
        && (!compareRequired || consultantVerificationReadiness?.status === "ready");
    const compareStatusLabel = consultantVerificationReadinessQuery.isError
        ? "Не удалось проверить"
        : consultantVerificationReadiness?.status_label
            ?? (compareRequired ? "Еще не запускали" : "Сравнение не требуется");
    const editBaseSourceLabel = editBaseSource === "draft"
        ? "сохраненный draft"
        : editBaseSource === "published"
            ? "опубликованная версия"
            : "пустой workspace";
    const canPublish = canEdit
        && !apiUnavailable
        && validation.ran
        && !hasErrors
        && !isDraftDirty
        && (!hasWarnings || ackWarnings)
        && compareReady
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
            const draftHash = typeof data?.draft_hash === "string" ? data.draft_hash : null;
            const draftSaved = data?.draft_saved !== false;
            setValidation({ ran: true, errors, warnings, diff, draftSaved });
            setLastValidatedDraft(draftText);
            setLastValidatedDraftHash(draftHash);
            setAckWarnings(false);
            void queryClient.invalidateQueries({
                queryKey: ["knowledge-consultant-verification-readiness", selectedClientId, selectedBranchId],
            });
            if (!draftSaved) {
                toast.error("Черновик не сохранён: обнаружена потеря structured данных.");
            } else if (valid) {
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
            if (isGatewayLikeError(error)) {
                const message = resolveKnowledgeActionErrorMessage(error);
                setGatewayError(message);
                toast.error(message);
                return;
            }
            const code = extractApiErrorCode(error);
            if (code === "CLIENT_SELECTION_REQUIRED" || code === "BRANCH_SELECTION_REQUIRED") {
                toast.error(resolveKnowledgeActionErrorMessage(error));
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
        onSuccess: async (data) => {
            setLastPublishAt(data?.published_at ?? new Date().toISOString());
            toast.success(data?.message || "Версия опубликована. Синхронизация выполняется.");
            await refreshKnowledgeServerState();
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            if (isGatewayLikeError(error)) {
                const message = resolveKnowledgeActionErrorMessage(error);
                setGatewayError(message);
                toast.error(message);
                return;
            }
            if (extractApiErrorCode(error) === "KNOWLEDGE_PREFLIGHT_REQUIRED") {
                toast.error("Сначала выполните Validate для текущего draft, затем Publish.");
                setStepIndex(1);
                return;
            }
            if (extractApiErrorCode(error) === "KNOWLEDGE_COMPARE_REQUIRED") {
                toast.error("Сначала выполните live vs draft compare для текущего draft.");
                setStepIndex(3);
                return;
            }
            if (extractApiErrorCode(error) === "KNOWLEDGE_INVALID") {
                toast.error(resolveKnowledgeActionErrorMessage(error));
                setStepIndex(1);
                return;
            }
            const code = extractApiErrorCode(error);
            if (code === "CLIENT_SELECTION_REQUIRED" || code === "BRANCH_SELECTION_REQUIRED") {
                toast.error(resolveKnowledgeActionErrorMessage(error));
                return;
            }
            handleError(error);
        },
    });

    const retrySyncMutation = useMutation({
        mutationFn: async (versionId: string) => {
            const response = await knowledgeApi.retrySync(versionId);
            return response.data;
        },
        onSuccess: async (data) => {
            toast.success(data?.message || "Синхронизация запущена повторно.");
            await refreshKnowledgeServerState();
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            if (isGatewayLikeError(error)) {
                const message = resolveKnowledgeActionErrorMessage(error);
                setGatewayError(message);
                toast.error(message);
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
        onSuccess: async (data) => {
            setLastRollbackAt(new Date().toISOString());
            toast.success(data?.message || "Версия восстановлена. Синхронизация выполняется.");
            await refreshKnowledgeServerState();
            setShowRollbackConfirm(false);
            setRollbackReason("");
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            if (isGatewayLikeError(error)) {
                const message = resolveKnowledgeActionErrorMessage(error);
                setGatewayError(message);
                toast.error(message);
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
            const workingHoursPatch = (parsedBranchWorkingHours.value ?? {}) as Record<string, never>;

            const draftResponse = await adminApi.draftBranchChange({
                branch_id: selectedBranchContext.id,
                reason,
                patch: {
                    knowledge_tag: branchKnowledgeTagDraft.trim() || null,
                    working_hours: workingHoursPatch,
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
                throw new Error(firstError || "Проверка изменения филиала не пройдена");
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
            const message = resolveKnowledgeActionErrorMessage(error);
            if (isGatewayLikeError(error)) {
                setGatewayError(message);
            }
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
            await applyConsoleScopeContext({
                queryClient,
                companyId,
                clientId,
                branchId: nextBranchId,
                invalidateKeys: [
                    ["knowledge-current", selectedClientId, selectedBranchId],
                    ["knowledge-history", selectedClientId, selectedBranchId],
                    ["learning-candidates"],
                    ["knowledge-specialists", selectedClientId, selectedBranchId],
                    ["knowledge-specialists-all", selectedClientId],
                ],
            });
            if (successMessage) {
                toast.success(successMessage);
            }
        } finally {
            setIsApplyingFleetContext(false);
        }
    }, [queryClient, selectedBranchId, selectedClientId]);

    const refreshKnowledgeServerState = useCallback(async () => {
        const currentKey = ["knowledge-current", selectedClientId, selectedBranchId] as const;
        const historyKey = ["knowledge-history", selectedClientId, selectedBranchId] as const;
        const readinessKey = ["knowledge-consultant-verification-readiness", selectedClientId, selectedBranchId] as const;

        await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["console-me"] }),
            queryClient.invalidateQueries({ queryKey: currentKey, exact: true }),
            queryClient.invalidateQueries({ queryKey: historyKey, exact: true }),
            queryClient.invalidateQueries({ queryKey: readinessKey, exact: true }),
        ]);
        await Promise.all([
            queryClient.refetchQueries({ queryKey: ["console-me"], exact: true }),
            queryClient.refetchQueries({ queryKey: currentKey, exact: true }),
            queryClient.refetchQueries({ queryKey: historyKey, exact: true }),
            queryClient.refetchQueries({ queryKey: readinessKey, exact: true }),
        ]);
    }, [queryClient, selectedBranchId, selectedClientId]);

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
            workspacePayloadObject,
            guidedHours,
            normalizedServices,
            guidedSalonProfile,
            guidedBooking,
            guidedPolicy,
        );
        setDraftText(JSON.stringify(payload, null, 2));
        setValidation((prev) => (prev.ran ? { ...prev, ran: false } : prev));
        toast.success("Структурированный черновик обновлен");
    };


    const fallbackBranchId = branchOptions[0]?.id ?? "";
    const effectiveHoursSummary = formatWorkingHoursSummary(effectiveWorkingHours);
    const effectiveHoursSource = hasBranchWorkingHours ? "переопределение филиала" : "опубликованный пакет";
    const canApplyBranchPatch = canEdit
        && !applyBranchKnowledgePatchMutation.isPending
        && isBranchPatchDirty
        && hasBranchChangeReason
        && !parsedBranchWorkingHours.error;
    const branchPatchHint = !isBranchPatchDirty
        ? "Нет несохраненных изменений: измените тег знаний или часы работы."
        : !hasBranchChangeReason
        ? "Добавьте причину изменения для журнала аудита."
        : null;

    const flowSidebarProps = {
        steps: KNOWLEDGE_STEPS,
        stepIndex,
        stepStatus,
        onSelectStep: setStepIndex,
    };

    const draftStageProps = {
        canEdit,
        draftText,
        onDraftTextChange: (value: string) => {
            setDraftText(value);
            setValidation((prev) => prev.ran ? { ...prev, ran: false } : prev);
        },
        currentText,
        editBaseText,
        hasSavedDraft,
        editBaseSource,
        editBaseSourceLabel,
        editBaseUpdatedAt,
        draftUpdatedAt,
        formatTimestamp,
        structuredGuidedFields,
        supportToolsDefaultOpen,
        inspectorSummary,
        packInspectorQuery,
        onPackInspectorQueryChange: setPackInspectorQuery,
        filteredPackPaths,
        applyStructuredDraft,
        guidedHours,
        onGuidedHoursChange: setGuidedHours,
        guidedSalonProfile,
        onGuidedSalonProfileChange: setGuidedSalonProfile,
        guidedBooking,
        onGuidedBookingChange: setGuidedBooking,
        guidedPolicy,
        onGuidedPolicyChange: setGuidedPolicy,
        guidedServices,
        onAddGuidedService: addGuidedService,
        onUpdateGuidedService: updateGuidedService,
        onRemoveGuidedService: removeGuidedService,
        specialistsLoading: specialistsQuery.isLoading,
        allSpecialistsLoading: allSpecialistsQuery.isLoading,
        specialists,
        allSpecialists,
        missingBranchSpecialistsButClientHasSome,
        specialistsInOtherBranchesCount: specialistsInOtherBranches.length,
        specialistsByBranch,
        onOpenTeam: () => void openRouteWithFleetContext(
            "/team",
            selectedClientId || fleetClientId,
            selectedCompanyId || fleetCompanyId,
            selectedBranchId || null,
        ),
        teamButtonDisabled: isFleetBusy,
        onLoadEditBase: () => setDraftText(editBaseText || currentText),
        onLoadPublished: () => setDraftText(currentText),
        onLoadSavedDraft: () => setDraftText(draftServerText),
    };

    const validateStageProps = {
        canEdit,
        apiUnavailable,
        draftText,
        validation,
        hasErrors,
        isDraftDirty,
        onValidate: () => validateMutation.mutate(),
        isValidating: validateMutation.isPending,
        formatKnowledgeValidationIssue,
    };

    const previewStageProps = {
        validation,
        currentText,
        draftText,
    };

    const publishStageProps = {
        validation,
        hasErrors,
        hasWarnings,
        isDraftDirty,
        compareReady,
        compareRequired,
        compareStatusLabel,
        consultantVerificationReadinessSummary: consultantVerificationReadiness?.summary ?? null,
        consultantVerificationReadinessErrorMessage,
        lastValidatedDraftHash,
        currentVersionId: currentQuery.data?.version_id ?? null,
        currentSyncStatus,
        currentSyncStatusLabel,
        currentSyncError,
        knowledgeSyncStatusClass,
        resolveKnowledgeSyncMessage,
        resolveKnowledgeSyncDetails,
        ackWarnings,
        onAckWarningsChange: setAckWarnings,
        canEdit,
        canPublish,
        isPublishing: publishMutation.isPending,
        onPublish: () => publishMutation.mutate(),
    };

    const historyStageProps = {
        items: historyItems,
        selectedVersionId,
        onSelectVersion: setSelectedVersionId,
        knowledgeSyncStatusClass,
    };

    const rollbackStageProps = {
        selectedVersionId,
        lastRollbackAt,
        canEdit,
        apiUnavailable,
        isRollbackPending: rollbackMutation.isPending,
        onOpenRollbackConfirm: () => {
            if (!selectedVersionId) {
                toast.error("Выберите версию для rollback");
                return;
            }
            setShowRollbackConfirm(true);
        },
    };


    const banners = {
        apiUnavailable,
        gatewayError,
        clearGatewayError: () => setGatewayError(null),
        retryGatewayRequests: () => {
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
        },
        retryApiAvailability: () => {
            setApiUnavailable(false);
            currentQuery.refetch();
            historyQuery.refetch();
        },
    };

    const platformAdminFleet = {
        visible: isPlatformAdmin,
        clientId: fleetClientId,
        companyId: fleetCompanyId,
        branchId: fleetBranchId,
        clients: fleetClients,
        branches: fleetBranches,
        attentionEnabled: fleetAttentionEnabled,
        attentionError: fleetAttentionError,
        attentionItems: fleetAttentionItems,
        attentionSummary: fleetSummary,
        isApplyingContext: isApplyingFleetContext,
        isBusy: isFleetBusy,
        isClientsLoading: fleetClientsQuery.isLoading,
        isBranchesLoading: fleetBranchesQuery.isLoading,
        isAttentionLoading: fleetAttentionQuery.isLoading,
        onToggleAttention: () => {
            if (fleetAttentionEnabled) {
                setFleetAttentionEnabled(false);
                setFleetAttentionError(null);
                return;
            }
            setFleetAttentionError(null);
            setFleetAttentionEnabled(true);
        },
        onRefresh: () => {
            setFleetAttentionError(null);
            fleetClientsQuery.refetch();
            if (fleetClientId) {
                fleetBranchesQuery.refetch();
            }
            if (fleetAttentionEnabled) {
                fleetAttentionQuery.refetch();
            }
        },
        onClientChange: (nextClientId: string) => {
            const nextClient = fleetClients.find((client) => client.id === nextClientId);
            setFleetClientId(nextClientId);
            setFleetCompanyId(nextClient?.company_id ?? "");
            setFleetBranchId("");
        },
        onBranchChange: handleFleetBranchSelect,
        onApplyContext: () => void selectKnowledgeBranch(),
        onOpenIntegrations: () => void openRouteWithFleetContext(
            "/integrations",
            fleetClientId,
            fleetCompanyId,
            resolveBranchContextForClient(fleetClientId),
        ),
        onOpenInbox: () => void openRouteWithFleetContext(
            "/",
            fleetClientId,
            fleetCompanyId,
            resolveBranchContextForClient(fleetClientId),
        ),
        onAttentionSelectClient: (item: FleetAttentionItem) => void applyConsoleContext({
            companyId: item.company_id,
            clientId: item.client_id,
            branchId: null,
            successMessage: "Контекст клиента обновлен",
        }),
        onAttentionOpenIntegrations: (item: FleetAttentionItem) => void openRouteWithFleetContext(
            "/integrations",
            item.client_id,
            item.company_id,
            resolveBranchContextForClient(item.client_id),
        ),
    };

    const branchReadiness = selectedBranchContext
        ? {
            selectedBranchContext,
            hasKnowledgeTag: Boolean((selectedBranchContext.knowledge_tag ?? "").trim()),
            hasBranchWorkingHours,
            effectiveHoursSummary,
            effectiveHoursSource,
            currentVersionId: currentQuery.data?.version_id ?? null,
            currentSyncStatus,
            currentSyncStatusLabel,
            currentSyncStatusClass: knowledgeSyncStatusClass(currentSyncStatus),
            currentSyncMessage: resolveKnowledgeSyncMessage(currentSyncStatus),
            currentSafeMode,
            currentSyncBlocked,
            currentSyncFailed,
            currentSyncDetails,
            canEdit,
            canApplyPatch: canApplyBranchPatch,
            isApplyingPatch: applyBranchKnowledgePatchMutation.isPending,
            branchKnowledgeTagDraft,
            branchWorkingHoursDraft,
            branchChangeReason,
            parsedBranchWorkingHoursError: parsedBranchWorkingHours.error ?? null,
            branchPatchHint,
            onBranchKnowledgeTagDraftChange: setBranchKnowledgeTagDraft,
            onBranchWorkingHoursDraftChange: setBranchWorkingHoursDraft,
            onBranchChangeReasonChange: setBranchChangeReason,
            onUsePublishedHours: () => {
                if (!effectiveWorkingHours || Object.keys(effectiveWorkingHours).length === 0) {
                    toast.error("Нет опубликованных часов для подстановки");
                    return;
                }
                setBranchWorkingHoursDraft(JSON.stringify(effectiveWorkingHours, null, 2));
            },
            onResetHoursOverride: () => setBranchWorkingHoursDraft("{}"),
            onApplyPatch: () => applyBranchKnowledgePatchMutation.mutate(),
            onOpenTeam: () => void openRouteWithFleetContext(
                "/team",
                selectedClientId || fleetClientId,
                selectedCompanyId || fleetCompanyId,
                selectedBranchId || null,
            ),
            onOpenCalendar: () => void openRouteWithFleetContext(
                "/calendar",
                selectedClientId || fleetClientId,
                selectedCompanyId || fleetCompanyId,
                selectedBranchId || null,
            ),
            teamActionsDisabled: isApplyingFleetContext,
            canRetrySync: currentSyncFailed && Boolean(currentQuery.data?.version_id),
            isRetrySyncPending: retrySyncMutation.isPending,
            onRetrySync: () => retrySyncMutation.mutate(currentQuery.data?.version_id ?? ""),
        }
        : null;

    const branchGate = {
        required: branchSelectionRequired,
        isPlatformAdmin,
        branchOptions,
        branchId,
        fallbackBranchId,
        isSelectingBranch,
        selectedClientId,
        selectedCompanyId,
        selectedBranchId,
        onBranchIdChange: setBranchId,
        onApplyPlatformFallback: async () => {
            if (!fallbackBranchId) {
                return;
            }
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
        },
        onApply: async () => {
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
        },
    };

    const learningCandidates = {
        candidates: learningCandidateItems,
        isLoading: candidatesQuery.isLoading,
        canEdit,
        approvePending: approveCandidateMutation.isPending,
        rejectPending: rejectCandidateMutation.isPending,
        onApprove: (candidateId: string) => {
            approveCandidateMutation.mutate(candidateId);
        },
        onReject: (candidateId: string) => {
            rejectCandidateMutation.mutate(candidateId);
        },
        formatTimestamp,
    };

    const rollbackDialog = {
        open: showRollbackConfirm,
        selectedVersionId,
        rollbackReason,
        onRollbackReasonChange: setRollbackReason,
        onCancel: () => {
            setShowRollbackConfirm(false);
            setRollbackReason("");
        },
        onConfirm: () => {
            const reason = rollbackReason.trim();
            if (!reason) {
                toast.error("Укажите причину");
                return;
            }
            rollbackMutation.mutate(reason);
        },
        isPending: rollbackMutation.isPending,
    };

    const flow = {
        sidebar: flowSidebarProps,
        currentStep,
        draftStage: draftStageProps,
        validateStage: validateStageProps,
        previewStage: previewStageProps,
        publishStage: publishStageProps,
        historyStage: historyStageProps,
        rollbackStage: rollbackStageProps,
        onPrevStep: () => setStepIndex((prev) => Math.max(prev - 1, 0)),
        onNextStep: () => setStepIndex((prev) => Math.min(prev + 1, KNOWLEDGE_STEPS.length - 1)),
        isFirstStep: stepIndex === 0,
        isLastStep: stepIndex === KNOWLEDGE_STEPS.length - 1,
    };

    return {
        role,
        canRead,
        canEdit,
        apiUnavailable,
        gatewayError,
        supportToolsDefaultOpen,
        lastPublishAt,
        platformAdminFleet,
        branchReadiness,
        branchGate,
        banners,
        flow,
        learningCandidates,
        rollbackDialog,
    };
}
