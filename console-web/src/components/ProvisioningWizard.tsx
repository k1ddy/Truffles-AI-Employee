"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import { adminApi, authApi, canAccessConsole, onboardingApi, type ConsoleRole, type ConsoleSection } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

type SessionData = ReturnType<typeof useSession>["data"];
type ProvisioningBranch = components["schemas"]["Branch"];
type ProvisioningAgent = components["schemas"]["Agent"];
type CapabilitiesPayload = components["schemas"]["CapabilitiesPayload"];
type CapabilitiesResponse = components["schemas"]["CapabilitiesResponse"];
type OnboardingContractPayload = components["schemas"]["OnboardingContractPayload"];
type OnboardingContractResponse = components["schemas"]["OnboardingContractResponse"];
type OnboardingAutopilotRequest = components["schemas"]["OnboardingAutopilotRequest"];
type OnboardingAutopilotResponse = components["schemas"]["OnboardingAutopilotResponse"];
type OnboardingPurchasedService = components["schemas"]["OnboardingPurchasedService"];
type ReferencePackListResponse = components["schemas"]["ReferencePackListResponse"];
type OnboardingStatus = components["schemas"]["OnboardingStatusResponse"];
type OnboardingStepStatus = components["schemas"]["OnboardingStepStatus"];

type AgentRole = ConsoleRole;
type OnboardingMode = "autopilot" | "manual";

const DEFAULT_TIMEZONE = "Asia/Almaty";
const WORKING_DAYS = [
    { id: "mon", label: "Пн" },
    { id: "tue", label: "Вт" },
    { id: "wed", label: "Ср" },
    { id: "thu", label: "Чт" },
    { id: "fri", label: "Пт" },
    { id: "sat", label: "Сб" },
    { id: "sun", label: "Вс" },
] as const;

const WIZARD_STEPS = [
    { id: "branch_draft", label: "Филиал", hint: "Draft" },
    { id: "integrations", label: "Интеграции", hint: "instance_id" },
    { id: "team", label: "Команда", hint: "Owner/Admin" },
    { id: "telegram", label: "Telegram", hint: "chat_id" },
    { id: "knowledge", label: "Knowledge", hint: "pack" },
    { id: "booking", label: "Booking", hint: "calendar" },
    { id: "go_no_go", label: "Go/No-Go", hint: "capabilities" },
] as const;

const MISSING_LABELS: Record<string, string> = {
    phone: "phone (WhatsApp branch)",
    instance_id: "instance_id (WhatsApp)",
    owner_admin: "Owner/Admin",
    telegram_chat_id: "telegram_chat_id",
    knowledge_tag: "knowledge_tag",
    knowledge_published: "Knowledge publish",
    working_hours: "working_hours",
    booking_settings: "booking_settings",
    specialists: "specialists",
    capabilities: "capabilities",
    onboarding_contract: "Onboarding contract",
    payment_confirmed: "Payment confirmed",
    webhook_secret: "Webhook secret",
    reference_pack_domain: "Niche domain (domain_slug)",
    reference_pack: "Reference pack",
    branch_active: "Филиал активен",
    "client_pack.salon.name": "Название салона",
    "client_pack.salon.city": "Город",
    "client_pack.salon.address.full": "Адрес",
    "client_pack.salon.hours.days": "Часы работы: дни",
    "client_pack.salon.hours.open": "Часы работы: открытие",
    "client_pack.salon.hours.close": "Часы работы: закрытие",
    "client_pack.salon.services_summary": "Кратко об услугах",
    "client_pack.salon.communication.languages": "Языки общения (ru + kk)",
    "client_pack.services_catalog.services": "Каталог услуг",
    "client_pack.service_duration_estimates": "Длительности услуг",
    "client_pack.booking.collect_fields": "Booking: обязательные поля",
    "client_pack.booking.bot_can_confirm": "Booking: подтверждение",
    "client_pack.guest_policy": "Guest policy",
    "client_pack.safety.medical_note": "Дисклеймер: противопоказания",
    "client_pack.pricing.price_from_reason": "Дисклеймер: цена \"от\"",
    "client_pack.quality.expectations_photo": "Дисклеймер: ожидания/референс",
    "client_pack.price_list": "Прайс-лист",
    "client_pack.policy.hard_law": "Policy: hard_law",
    "client_pack.policy.payment_info": "Policy: payment",
    "client_pack.policy.reschedule": "Policy: reschedule",
    "client_pack.policy.cancel": "Policy: cancel",
    "client_pack.policy.medical": "Policy: medical",
    "client_pack.policy.legal": "Policy: legal",
    "client_pack.policy.complaint": "Policy: complaint",
    "client_pack.policy.discounts": "Policy: discounts",
    "client_pack.policy.guard_topics.refund": "Policy: refund keywords",
};

const CAPABILITY_FIELD_LABELS: Record<string, string> = {
    "channels.whatsapp": "WhatsApp",
    "channels.telegram": "Telegram",
    "channels.instagram": "Instagram",
    "providers.availability_provider": "availability_provider",
    "providers.crm_provider": "crm_provider",
    "providers.calendar_provider": "calendar_provider",
    "features.booking_mode": "booking_mode",
    "features.knowledge_upload": "knowledge_upload",
    "features.analytics": "analytics",
    "features.auto_learn": "auto_learn",
};

const AUTOPILOT_SERVICE_OPTIONS: Array<{
    id: OnboardingPurchasedService;
    label: string;
}> = [
    { id: "whatsapp", label: "WhatsApp" },
    { id: "telegram", label: "Telegram" },
    { id: "instagram", label: "Instagram" },
    { id: "booking_collect", label: "Booking: collect" },
    { id: "booking_confirm", label: "Booking: confirm" },
    { id: "knowledge_upload", label: "Knowledge upload" },
    { id: "analytics", label: "Analytics" },
    { id: "auto_learn", label: "Auto learn" },
    { id: "provider_google_calendar", label: "Google Calendar" },
    { id: "provider_local_calendar", label: "Local Calendar" },
    { id: "provider_manual", label: "Manual provider" },
    { id: "provider_amocrm", label: "amoCRM" },
    { id: "provider_bitrix", label: "Bitrix" },
];

type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

type FieldGuideItem = {
    field: string;
    required: boolean;
    purpose: string;
    relation: string;
    output: string;
};

const AUTOPILOT_FIELD_GUIDE: FieldGuideItem[] = [
    {
        field: "phone",
        required: true,
        purpose: "Номер филиала для inbound/outbound",
        relation: "branches.phone (уникально в client)",
        output: "Branch routing и anti-loop контур",
    },
    {
        field: "instance_id",
        required: true,
        purpose: "Идентификатор WA instance",
        relation: "branches.instance_id (уникально в client)",
        output: "WA канал + генерация webhook_secret",
    },
    {
        field: "client_data_text",
        required: true,
        purpose: "Свободный текст данных клиента",
        relation: "intake -> normalize -> validate",
        output: "draft payload + missing_fields/questions",
    },
    {
        field: "purchased_services",
        required: true,
        purpose: "Подключенные услуги по договору",
        relation: "onboarding_contract.purchased -> capabilities",
        output: "Go/No-Go capability_mismatch контроль",
    },
    {
        field: "company_id | company_name",
        required: true,
        purpose: "Привязка/создание компании",
        relation: "companies -> clients",
        output: "Company контекст",
    },
    {
        field: "client_id | client_slug",
        required: true,
        purpose: "Привязка/создание клиента",
        relation: "clients -> branches",
        output: "Client контекст",
    },
    {
        field: "branch_name",
        required: true,
        purpose: "Имя филиала при создании",
        relation: "branches.name",
        output: "Создание нового branch",
    },
    {
        field: "payment_status",
        required: false,
        purpose: "Коммерческий статус запуска",
        relation: "onboarding_contract.payment_status",
        output: "Go/No-Go gate payment_confirmed",
    },
];

const MANUAL_STEP_FIELD_GUIDE: Record<WizardStepId, FieldGuideItem[]> = {
    branch_draft: [
        {
            field: "name",
            required: true,
            purpose: "Читаемое имя филиала",
            relation: "branches.name",
            output: "Branch draft запись",
        },
        {
            field: "slug",
            required: true,
            purpose: "Технический идентификатор филиала",
            relation: "branches.slug (уникален в client)",
            output: "Branch lookup в UI/API",
        },
        {
            field: "timezone",
            required: false,
            purpose: "Часовой пояс филиала",
            relation: "branches.timezone",
            output: "Корректное время в слотах",
        },
        {
            field: "phone",
            required: true,
            purpose: "Телефон WA филиала",
            relation: "branches.phone (уникален в client)",
            output: "Требуется для WA go-live",
        },
    ],
    integrations: [
        {
            field: "instance_id",
            required: true,
            purpose: "Привязка WA инстанса",
            relation: "branches.instance_id",
            output: "Активируем branch + webhook",
        },
        {
            field: "phone",
            required: true,
            purpose: "Явная связка с instance",
            relation: "branches.phone + branches.instance_id",
            output: "Устойчивый branch routing",
        },
    ],
    team: [
        {
            field: "role + name",
            required: true,
            purpose: "Console доступ сотрудников",
            relation: "agents + agent_memberships",
            output: "Owner/Admin/Manager доступ",
        },
        {
            field: "oidc_subject",
            required: false,
            purpose: "Привязка Keycloak user",
            relation: "agent_identities(channel=oidc)",
            output: "SSO авторизация",
        },
    ],
    telegram: [
        {
            field: "telegram_chat_id",
            required: true,
            purpose: "Эскалации менеджеру",
            relation: "branches.telegram_chat_id",
            output: "HANDOFF delivery в Telegram",
        },
    ],
    knowledge: [
        {
            field: "knowledge_tag",
            required: true,
            purpose: "Связка branch с knowledge pack",
            relation: "branches.knowledge_tag",
            output: "Publish/Sync готовность",
        },
    ],
    booking: [
        {
            field: "working_hours",
            required: true,
            purpose: "График филиала",
            relation: "branches.working_hours",
            output: "Booking slot availability",
        },
        {
            field: "booking_settings",
            required: true,
            purpose: "Правила записи",
            relation: "branches.booking_settings",
            output: "Детерминированный booking flow",
        },
    ],
    go_no_go: [
        {
            field: "capabilities + onboarding_contract",
            required: true,
            purpose: "Сверка купленного и включенного",
            relation: "client_capabilities + onboarding_contract",
            output: "capability mismatch detection",
        },
        {
            field: "payment + webhook + reference pack",
            required: true,
            purpose: "Коммерческий и тех readiness",
            relation: "payment_status + branches.webhook_secret + reference_packs",
            output: "Go/No-Go final unlock",
        },
    ],
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

function formatMissingRequirement(code: string): string {
    if (code.startsWith("capability_mismatch:")) {
        const key = code.slice("capability_mismatch:".length);
        return `Несоответствие договору: ${CAPABILITY_FIELD_LABELS[key] ?? key}`;
    }
    return MISSING_LABELS[code] ?? code;
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

function normalizeOnboardingContractPayload(
    payload?: OnboardingContractPayload | null,
): OnboardingContractPayload {
    return {
        domain_slug: payload?.domain_slug ?? null,
        purchased: normalizeCapabilities(payload?.purchased ?? null),
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

function formatEffectiveValue(value: string | number | boolean | null | undefined): string {
    if (value === true) {
        return "Включено";
    }
    if (value === false) {
        return "Выключено";
    }
    if (value === null || value === undefined || value === "") {
        return "—";
    }
    return String(value);
}

function isNonEmptyRecord(value: unknown): value is Record<string, unknown> {
    if (!value || typeof value !== "object") {
        return false;
    }
    return Object.keys(value as Record<string, unknown>).length > 0;
}

type ProvisioningWizardProps = {
    session: SessionData;
    accessSection?: ConsoleSection;
};

function ProvisioningWizard({ session, accessSection = "settings" }: ProvisioningWizardProps) {
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
    const canEdit = canAccessConsole(role, accessSection, "write");

    const [onboardingMode, setOnboardingMode] = useState<OnboardingMode>("autopilot");
    const [stepIndex, setStepIndex] = useState(0);
    const [autoStepSync, setAutoStepSync] = useState(true);
    const [companyName, setCompanyName] = useState("");
    const [companyId, setCompanyId] = useState("");
    const [billingInfo, setBillingInfo] = useState("");
    const [billingContract, setBillingContract] = useState("");
    const [billingCurrency, setBillingCurrency] = useState("");
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
    const [branchBootstrap, setBranchBootstrap] = useState({
        enabled: true,
        createOwner: true,
        createAdmin: true,
        createManager: true,
        ownerName: "",
        ownerOidcSubject: "",
        adminName: "",
        adminOidcSubject: "",
        managerName: "",
        managerOidcSubject: "",
    });
    const [workingHoursDays, setWorkingHoursDays] = useState<string[]>([]);
    const [workingHoursStart, setWorkingHoursStart] = useState("");
    const [workingHoursEnd, setWorkingHoursEnd] = useState("");
    const [bookingDefaultDuration, setBookingDefaultDuration] = useState("");
    const [bookingBufferMin, setBookingBufferMin] = useState("");
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
    const [onboardingContractDraft, setOnboardingContractDraft] = useState<OnboardingContractPayload>(() => (
        normalizeOnboardingContractPayload()
    ));
    const [onboardingContractTouched, setOnboardingContractTouched] = useState(false);
    const [onboardingContractSavedAt, setOnboardingContractSavedAt] = useState<string | null>(null);
    const [purchasedJsonDraft, setPurchasedJsonDraft] = useState("{}");
    const [paymentStatusDraft, setPaymentStatusDraft] = useState<"pending" | "confirmed" | "rejected">("pending");
    const [referencePackTitle, setReferencePackTitle] = useState("");
    const [specialistsConfirmed, setSpecialistsConfirmed] = useState(false);
    const [integrationWebhookSecret, setIntegrationWebhookSecret] = useState("");
    const [integrationWebhookUrl, setIntegrationWebhookUrl] = useState("");
    const [autopilotForm, setAutopilotForm] = useState({
        companyName: "",
        clientSlug: "",
        branchName: "",
        branchSlug: "",
        timezone: DEFAULT_TIMEZONE,
        phone: "",
        instanceId: "",
        domainSlug: "beauty",
        paymentStatus: "pending" as "pending" | "confirmed" | "rejected",
        clientDataText: "",
    });
    const [autopilotServices, setAutopilotServices] = useState<OnboardingPurchasedService[]>(["whatsapp"]);
    const [autopilotResult, setAutopilotResult] = useState<OnboardingAutopilotResponse | null>(null);

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
        setWorkingHoursDays([]);
        setWorkingHoursStart("");
        setWorkingHoursEnd("");
        setBookingDefaultDuration("");
        setBookingBufferMin("");
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

    useEffect(() => {
        if (!billingInfo.trim()) {
            return;
        }
        if (billingContract || billingCurrency) {
            return;
        }
        const parsed = parseOptionalJson(billingInfo, "billing_info");
        if (!parsed.value) {
            return;
        }
        const contract = parsed.value.contract;
        const currency = parsed.value.currency;
        if (typeof contract === "string") {
            setBillingContract(contract);
        }
        if (typeof currency === "string") {
            setBillingCurrency(currency);
        }
    }, [billingInfo, billingContract, billingCurrency]);

    useEffect(() => {
        if (!branchForm.workingHours.trim()) {
            return;
        }
        if (workingHoursDays.length || workingHoursStart || workingHoursEnd) {
            return;
        }
        const parsed = parseOptionalJson(branchForm.workingHours, "working_hours");
        if (!parsed.value) {
            return;
        }
        const availableDays = new Set<string>(WORKING_DAYS.map((day) => day.id));
        const dayKeys = Object.keys(parsed.value).filter((day) => availableDays.has(day));
        if (dayKeys.length) {
            setWorkingHoursDays(dayKeys);
        }
        const firstDay = dayKeys[0];
        if (firstDay) {
            const slots = parsed.value[firstDay];
            if (Array.isArray(slots) && slots[0] && typeof slots[0] === "object") {
                const slot = slots[0] as { start?: unknown; end?: unknown };
                if (typeof slot.start === "string") {
                    setWorkingHoursStart(slot.start);
                }
                if (typeof slot.end === "string") {
                    setWorkingHoursEnd(slot.end);
                }
            }
        }
    }, [branchForm.workingHours, workingHoursDays.length, workingHoursStart, workingHoursEnd]);

    useEffect(() => {
        if (!branchForm.bookingSettings.trim()) {
            return;
        }
        if (bookingDefaultDuration || bookingBufferMin) {
            return;
        }
        const parsed = parseOptionalJson(branchForm.bookingSettings, "booking_settings");
        if (!parsed.value) {
            return;
        }
        const defaultDuration = parsed.value.default_duration_min;
        const bufferMin = parsed.value.buffer_min;
        if (typeof defaultDuration === "number" || typeof defaultDuration === "string") {
            setBookingDefaultDuration(String(defaultDuration));
        }
        if (typeof bufferMin === "number" || typeof bufferMin === "string") {
            setBookingBufferMin(String(bufferMin));
        }
    }, [branchForm.bookingSettings, bookingDefaultDuration, bookingBufferMin]);

    useEffect(() => {
        setAutoStepSync(true);
        setOnboardingContractTouched(false);
        setOnboardingContractSavedAt(null);
        setReferencePackTitle("");
    }, [branchData?.id]);

    const buildBillingInfoPayload = () => {
        const payload: Record<string, unknown> = {};
        const contract = billingContract.trim();
        const currency = billingCurrency.trim();
        if (contract) {
            payload.contract = contract;
        }
        if (currency) {
            payload.currency = currency;
        }
        return Object.keys(payload).length ? payload : undefined;
    };

    const applyBillingToJson = () => {
        const payload = buildBillingInfoPayload();
        setBillingInfo(payload ? JSON.stringify(payload, null, 2) : "");
    };

    const loadBillingFromJson = () => {
        const parsed = parseOptionalJson(billingInfo, "billing_info");
        if (parsed.error) {
            toast.error(parsed.error);
            return;
        }
        const payload = (parsed.value ?? {}) as Record<string, unknown>;
        const contract = payload.contract;
        const currency = payload.currency;
        setBillingContract(typeof contract === "string" ? contract : "");
        setBillingCurrency(typeof currency === "string" ? currency : "");
    };

    const buildWorkingHoursPayload = (): { value?: Record<string, unknown>; error?: string } => {
        const selectedDays = workingHoursDays;
        const start = workingHoursStart.trim();
        const end = workingHoursEnd.trim();
        if (!selectedDays.length && !start && !end) {
            return {};
        }
        if (!selectedDays.length) {
            return { error: "Укажите рабочие дни" };
        }
        if (!start || !end) {
            return { error: "Укажите время открытия и закрытия" };
        }
        const payload: Record<string, unknown> = {};
        selectedDays.forEach((day) => {
            payload[day] = [{ start, end }];
        });
        return { value: payload };
    };

    const applyWorkingHoursToJson = () => {
        const built = buildWorkingHoursPayload();
        if (built.error) {
            toast.error(built.error);
            return;
        }
        const nextValue = built.value ? JSON.stringify(built.value, null, 2) : "";
        setBranchForm((prev) => ({ ...prev, workingHours: nextValue }));
    };

    const loadWorkingHoursFromJson = () => {
        const parsed = parseOptionalJson(branchForm.workingHours, "working_hours");
        if (parsed.error) {
            toast.error(parsed.error);
            return;
        }
        const payload = (parsed.value ?? {}) as Record<string, unknown>;
        const orderedDays = WORKING_DAYS.map((day) => day.id);
        const dayKeys = orderedDays.filter((day) => Array.isArray(payload[day]));
        setWorkingHoursDays(dayKeys);
        setWorkingHoursStart("");
        setWorkingHoursEnd("");
        const firstDay = dayKeys[0];
        if (!firstDay) {
            return;
        }
        const slots = payload[firstDay];
        if (Array.isArray(slots) && slots[0] && typeof slots[0] === "object") {
            const slot = slots[0] as { start?: unknown; end?: unknown };
            if (typeof slot.start === "string") {
                setWorkingHoursStart(slot.start);
            }
            if (typeof slot.end === "string") {
                setWorkingHoursEnd(slot.end);
            }
        }
    };

    const buildBookingSettingsPayload = (): { value?: Record<string, unknown>; error?: string } => {
        const defaultDurationRaw = bookingDefaultDuration.trim();
        const bufferMinRaw = bookingBufferMin.trim();
        if (!defaultDurationRaw && !bufferMinRaw) {
            return {};
        }
        const payload: Record<string, unknown> = {};
        if (defaultDurationRaw) {
            const parsed = Number(defaultDurationRaw);
            if (Number.isNaN(parsed)) {
                return { error: "default_duration_min: укажите число" };
            }
            payload.default_duration_min = parsed;
        }
        if (bufferMinRaw) {
            const parsed = Number(bufferMinRaw);
            if (Number.isNaN(parsed)) {
                return { error: "buffer_min: укажите число" };
            }
            payload.buffer_min = parsed;
        }
        return { value: payload };
    };

    const applyBookingSettingsToJson = () => {
        const built = buildBookingSettingsPayload();
        if (built.error) {
            toast.error(built.error);
            return;
        }
        const nextValue = built.value ? JSON.stringify(built.value, null, 2) : "";
        setBranchForm((prev) => ({ ...prev, bookingSettings: nextValue }));
    };

    const loadBookingSettingsFromJson = () => {
        const parsed = parseOptionalJson(branchForm.bookingSettings, "booking_settings");
        if (parsed.error) {
            toast.error(parsed.error);
            return;
        }
        const payload = (parsed.value ?? {}) as Record<string, unknown>;
        const defaultDuration = payload.default_duration_min;
        const bufferMin = payload.buffer_min;
        setBookingDefaultDuration((typeof defaultDuration === "number" || typeof defaultDuration === "string")
            ? String(defaultDuration)
            : "");
        setBookingBufferMin((typeof bufferMin === "number" || typeof bufferMin === "string")
            ? String(bufferMin)
            : "");
    };

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

    const {
        data: onboardingContractData,
        isLoading: onboardingContractLoading,
        error: onboardingContractError,
        refetch: refetchOnboardingContract,
    } = useQuery({
        queryKey: ["admin-onboarding-contract", clientId, branchData?.id],
        queryFn: async () => {
            const response = await adminApi.getOnboardingContract({
                branch_id: branchData?.id,
                clientId: clientId || undefined,
            });
            return response.data as OnboardingContractResponse;
        },
        enabled: !!session && !!clientId && !!branchData?.id,
    });

    const referencePackDomainSlug = (
        onboardingContractDraft.domain_slug
        || capabilitiesDraft.domain_slug
        || ""
    ).trim();
    const {
        data: referencePackData,
        isLoading: referencePackLoading,
        error: referencePackError,
        refetch: refetchReferencePacks,
    } = useQuery({
        queryKey: ["admin-reference-packs", referencePackDomainSlug],
        queryFn: async () => {
            const response = await adminApi.listReferencePacks({
                domain_slug: referencePackDomainSlug || undefined,
            });
            return response.data as ReferencePackListResponse;
        },
        enabled: !!session && referencePackDomainSlug.length > 0,
    });

    const { data: onboardingStatus, refetch: refetchOnboarding } = useQuery({
        queryKey: ["onboarding-status", branchData?.id],
        queryFn: async () => {
            if (!branchData?.id) {
                return null;
            }
            const response = await onboardingApi.status(branchData.id);
            return response.data as OnboardingStatus;
        },
        enabled: !!session && !!branchData?.id,
    });

    useEffect(() => {
        if (capabilitiesTouched || !capabilitiesData) {
            return;
        }
        const base = capabilitiesData.branch_capabilities?.payload ?? capabilitiesData.effective ?? null;
        setCapabilitiesDraft(normalizeCapabilities(base));
    }, [capabilitiesData, capabilitiesTouched]);

    useEffect(() => {
        if (onboardingContractTouched || !onboardingContractData) {
            return;
        }
        const basePayload = onboardingContractData.branch_contract?.payload ?? onboardingContractData.effective ?? null;
        const normalized = normalizeOnboardingContractPayload(basePayload);
        setOnboardingContractDraft(normalized);
        setPurchasedJsonDraft(JSON.stringify(normalized.purchased ?? normalizeCapabilities(), null, 2));
        setPaymentStatusDraft(onboardingContractData.payment_status ?? "pending");
    }, [onboardingContractData, onboardingContractTouched]);

    useEffect(() => {
        if (referencePackTitle.trim()) {
            return;
        }
        const first = referencePackData?.items?.[0];
        if (first?.title) {
            setReferencePackTitle(first.title);
        }
    }, [referencePackData, referencePackTitle]);

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

    useEffect(() => {
        if (!autoStepSync || !onboardingStatus?.steps?.length) {
            return;
        }
        const nextIndex = onboardingStatus.steps.findIndex((step) => step.status === "available");
        setStepIndex(nextIndex >= 0 ? nextIndex : WIZARD_STEPS.length - 1);
        setAutoStepSync(false);
    }, [autoStepSync, onboardingStatus]);

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
            const bootstrapAgents = (data.created_agents ?? []) as ProvisioningAgent[];
            if (bootstrapAgents.length > 0) {
                setCreatedAgents((prev) => [...bootstrapAgents, ...prev]);
                queryClient.invalidateQueries({ queryKey: ["agents"] });
            }
            refetchOnboarding();
            toast.success(
                bootstrapAgents.length > 0
                    ? `Филиал создан, добавлено аккаунтов: ${bootstrapAgents.length}`
                    : "Филиал создан"
            );
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
            refetchOnboarding();
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
            refetchOnboarding();
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
            refetchOnboarding();
            toast.success("Capabilities сохранены");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const patchOnboardingContractMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["OnboardingContractPatchRequest"]) => {
            const response = await adminApi.patchOnboardingContract(payload, clientId || undefined);
            return response.data;
        },
        onSuccess: (data) => {
            setOnboardingContractSavedAt(data.updated_at ?? new Date().toISOString());
            refetchOnboardingContract();
            refetchOnboarding();
            toast.success("Onboarding contract сохранён");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const upsertReferencePackMutation = useMutation({
        mutationFn: async (payload: { domainSlug: string; title: string }) => {
            const response = await adminApi.upsertReferencePack(payload.domainSlug, {
                title: payload.title,
                status: "active",
            });
            return response.data;
        },
        onSuccess: () => {
            refetchReferencePacks();
            refetchOnboardingContract();
            refetchOnboarding();
            toast.success("Reference pack обновлён");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const runAutopilotMutation = useMutation({
        mutationFn: async (payload: OnboardingAutopilotRequest) => {
            const response = await adminApi.runOnboardingAutopilot(payload);
            return response.data as OnboardingAutopilotResponse;
        },
        onSuccess: (data) => {
            setAutopilotResult(data);
            if (data.company?.id) {
                setCompanyId(data.company.id);
            }
            if (data.client?.id) {
                setClientId(data.client.id);
            }
            if (data.client?.slug) {
                setClientSlug(data.client.slug);
            }
            if (data.branch) {
                setBranchData(data.branch as ProvisioningBranch);
            }
            if (data.capabilities?.payload) {
                setCapabilitiesDraft(normalizeCapabilities(data.capabilities.payload));
                setCapabilitiesTouched(false);
            }
            if (data.onboarding_contract?.payload) {
                setOnboardingContractDraft(normalizeOnboardingContractPayload(data.onboarding_contract.payload));
                setOnboardingContractTouched(false);
                setPurchasedJsonDraft(JSON.stringify(
                    normalizeCapabilities(data.onboarding_contract.payload.purchased),
                    null,
                    2,
                ));
            }
            if (data.payment_status) {
                setPaymentStatusDraft(data.payment_status);
            }
            if (data.webhook_secret) {
                setIntegrationWebhookSecret(data.webhook_secret);
            }
            if (data.webhook_url) {
                setIntegrationWebhookUrl(data.webhook_url);
            }
            setAutoStepSync(true);
            queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
            queryClient.invalidateQueries({ queryKey: ["admin-capabilities"] });
            queryClient.invalidateQueries({ queryKey: ["admin-onboarding-contract"] });
            refetchCapabilities();
            refetchOnboardingContract();
            refetchReferencePacks();
            refetchOnboarding();
            toast.success("Авто-онбординг выполнен");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const getWebhookSecretMutation = useMutation({
        mutationFn: async (payload: { branchId?: string }) => {
            const response = await adminApi.getWebhookSecret({
                branch_id: payload.branchId,
                clientId: clientId || undefined,
            });
            return response.data;
        },
        onSuccess: (data) => {
            setIntegrationWebhookSecret(data.webhook_secret ?? "");
            setIntegrationWebhookUrl(data.webhook_url ?? "");
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const resolveNextStepIndex = (status?: OnboardingStatus | null) => {
        if (!status?.steps?.length) {
            return 0;
        }
        const nextIndex = status.steps.findIndex((step) => step.status === "available");
        return nextIndex >= 0 ? nextIndex : WIZARD_STEPS.length - 1;
    };

    const advanceOnboardingMutation = useMutation({
        mutationFn: async (stepId: WizardStepId) => {
            if (!branchData?.id) {
                throw new Error("BRANCH_REQUIRED");
            }
            const response = await onboardingApi.advance({
                branch_id: branchData.id,
                step_id: stepId,
            });
            return response.data as OnboardingStatus;
        },
        onSuccess: (data) => {
            queryClient.setQueryData(["onboarding-status", branchData?.id], data);
            setStepIndex(resolveNextStepIndex(data));
            setAutoStepSync(false);
            refetchOnboarding();
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                toast.error("Сначала создайте филиал");
                return;
            }
            handleError(error);
        },
    });

    const stepStateById = useMemo(() => {
        const map: Partial<Record<WizardStepId, OnboardingStepStatus>> = {};
        if (onboardingStatus?.steps?.length) {
            onboardingStatus.steps.forEach((step) => {
                map[step.id as WizardStepId] = step;
            });
        }
        return map;
    }, [onboardingStatus]);

    const stepStatus = useMemo(() => {
        if (onboardingStatus?.steps?.length) {
            const status: Record<WizardStepId, boolean> = {
                branch_draft: false,
                integrations: false,
                team: false,
                telegram: false,
                knowledge: false,
                booking: false,
                go_no_go: false,
            };
            onboardingStatus.steps.forEach((step) => {
                status[step.id as WizardStepId] = step.status === "complete" || step.status === "skipped";
            });
            return status;
        }
        const hasWorkingHours = isNonEmptyRecord(branchData?.working_hours);
        const hasBookingSettings = isNonEmptyRecord(branchData?.booking_settings);
        return {
            branch_draft: !!branchData?.id,
            integrations: !!branchData?.instance_id && !!branchData?.phone,
            team: createdAgents.length > 0,
            telegram: !!branchData?.telegram_chat_id,
            knowledge: !!branchData?.knowledge_tag,
            booking: hasWorkingHours && hasBookingSettings,
            go_no_go: !!capabilitiesSavedAt || !!onboardingContractSavedAt,
        };
    }, [onboardingStatus, branchData, createdAgents.length, capabilitiesSavedAt, onboardingContractSavedAt]);

    const capabilitiesPreview = useMemo(() => {
        const clientPayload = capabilitiesData?.client_capabilities?.payload ?? null;
        return mergeCapabilities(clientPayload, capabilitiesDraft);
    }, [capabilitiesData, capabilitiesDraft]);

    const canManagePayment = role === "platform_admin";
    const canManageReferencePacks = role === "platform_admin";
    const hasOnboardingContractRecord = !!onboardingContractData?.client_contract || !!onboardingContractData?.branch_contract;
    const paymentStatusEffective = onboardingContractData?.payment_status ?? "pending";
    const capabilityMismatches = onboardingContractData?.capability_mismatches ?? [];
    const referencePacks = referencePackData?.items ?? [];
    const hasActiveReferencePack = referencePacks.some((item) => item.status === "active");

    const effectiveCapabilities = capabilitiesData?.effective ?? null;
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
            {
                id: "onboarding_contract",
                label: "Onboarding contract",
                required: true,
                ok: hasOnboardingContractRecord,
            },
            {
                id: "payment_confirmed",
                label: "Payment confirmed",
                required: true,
                ok: paymentStatusEffective === "confirmed",
            },
            {
                id: "reference_pack",
                label: "Reference pack active",
                required: true,
                ok: referencePackDomainSlug.length > 0 && hasActiveReferencePack,
            },
        ];
    }, [
        branchData,
        capabilitiesPreview,
        bookingEnabled,
        hasOnboardingContractRecord,
        paymentStatusEffective,
        referencePackDomainSlug,
        hasActiveReferencePack,
        hasBookingSettings,
        hasWorkingHours,
        specialistsConfirmed,
    ]);

    const missingRequirements = readinessItems.filter((item) => item.required && !item.ok);
    const goNoGoMissing = stepStateById.go_no_go?.missing ?? [];
    const goNoGoReady = missingRequirements.length === 0 && goNoGoMissing.length === 0;
    const autopilotPhone = autopilotForm.phone.trim();
    const autopilotInstanceId = autopilotForm.instanceId.trim();
    const autopilotCompanyRef = companyId.trim() || autopilotForm.companyName.trim();
    const autopilotClientRef = clientId.trim() || autopilotForm.clientSlug.trim();
    const autopilotNeedsBranchName = !branchData?.id;
    const autopilotBranchName = autopilotForm.branchName.trim();
    const autopilotClientDataText = autopilotForm.clientDataText.trim();
    const autopilotMissingInputs: string[] = [];
    if (!autopilotPhone) {
        autopilotMissingInputs.push("phone");
    }
    if (!autopilotInstanceId) {
        autopilotMissingInputs.push("instance_id");
    }
    if (!autopilotCompanyRef) {
        autopilotMissingInputs.push("company_id или company_name");
    }
    if (!autopilotClientRef) {
        autopilotMissingInputs.push("client_id или client_slug");
    }
    if (autopilotNeedsBranchName && !autopilotBranchName) {
        autopilotMissingInputs.push("branch_name (для нового branch)");
    }
    if (!autopilotServices.length) {
        autopilotMissingInputs.push("минимум 1 подключённая услуга");
    }
    if (!autopilotClientDataText) {
        autopilotMissingInputs.push("client_data_text");
    }
    const canRunAutopilot = canEdit && !runAutopilotMutation.isPending && autopilotMissingInputs.length === 0;

    const handleToggleAutopilotService = (serviceId: OnboardingPurchasedService) => {
        setAutopilotServices((prev) => (
            prev.includes(serviceId)
                ? prev.filter((item) => item !== serviceId)
                : [...prev, serviceId]
        ));
    };

    const handleRunAutopilot = () => {
        if (autopilotMissingInputs.length > 0) {
            toast.error(`Не хватает данных: ${autopilotMissingInputs.join(", ")}`);
            return;
        }
        const payload: OnboardingAutopilotRequest = {
            company_id: companyId.trim() || undefined,
            company_name: autopilotForm.companyName.trim() || undefined,
            client_id: clientId.trim() || undefined,
            client_slug: autopilotForm.clientSlug.trim() || undefined,
            branch_id: branchData?.id || undefined,
            branch_slug: autopilotForm.branchSlug.trim() || undefined,
            branch_name: autopilotForm.branchName.trim() || undefined,
            timezone: autopilotForm.timezone.trim() || undefined,
            phone: autopilotPhone,
            instance_id: autopilotInstanceId,
            payment_status: canManagePayment ? autopilotForm.paymentStatus : "pending",
            domain_slug: autopilotForm.domainSlug.trim() || undefined,
            purchased_services: autopilotServices.length ? autopilotServices : undefined,
            client_data_text: autopilotClientDataText || undefined,
            activate_branch: true,
            auto_create_reference_pack: true,
            auto_publish_knowledge: false,
        };
        runAutopilotMutation.mutate(payload);
    };

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
        let billingPayload = billing.value;
        if (!billingPayload) {
            billingPayload = buildBillingInfoPayload();
            if (billingPayload) {
                setBillingInfo(JSON.stringify(billingPayload, null, 2));
            }
        }
        createCompanyMutation.mutate({
            name,
            billing_info: billingPayload,
        });
    };

    const handleCreateClient = () => {
        const slug = clientSlug.trim();
        if (!slug) {
            toast.error("Укажите slug клиента");
            return;
        }
        if (!companyId.trim()) {
            toast.error("Укажите company_id компании");
            return;
        }
        createClientMutation.mutate({
            slug,
            company_id: companyId.trim(),
        });
    };

    const buildBranchBootstrapAccounts = (): components["schemas"]["BranchBootstrapAccountTemplate"][] => {
        if (!branchBootstrap.enabled) {
            return [];
        }
        const branchLabel = branchForm.name.trim() || "Branch";
        const accounts: components["schemas"]["BranchBootstrapAccountTemplate"][] = [];
        if (branchBootstrap.createOwner) {
            accounts.push({
                role: "owner",
                name: branchBootstrap.ownerName.trim() || `${branchLabel} Owner`,
                oidc_subject: branchBootstrap.ownerOidcSubject.trim() || undefined,
            });
        }
        if (branchBootstrap.createAdmin) {
            accounts.push({
                role: "admin",
                name: branchBootstrap.adminName.trim() || `${branchLabel} Admin`,
                oidc_subject: branchBootstrap.adminOidcSubject.trim() || undefined,
            });
        }
        if (branchBootstrap.createManager) {
            accounts.push({
                role: "manager",
                name: branchBootstrap.managerName.trim() || `${branchLabel} Manager`,
                oidc_subject: branchBootstrap.managerOidcSubject.trim() || undefined,
            });
        }
        return accounts;
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
        const bootstrapAccounts = buildBranchBootstrapAccounts();
        createBranchMutation.mutate({
            client_id: clientId,
            name,
            slug,
            timezone: branchForm.timezone.trim() || undefined,
            phone: branchForm.phone.trim() || undefined,
            is_active: false,
            bootstrap_accounts: bootstrapAccounts.length > 0 ? bootstrapAccounts : undefined,
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
        const phone = branchForm.phone.trim();
        if (!phone) {
            toast.error("Укажите phone филиала");
            return;
        }
        patchBranchMutation.mutate(
            {
                phone,
                instance_id: instanceId,
                is_active: activateOnSave,
            },
            {
                onSuccess: (data) => {
                    const typed = data as ProvisioningBranch;
                    if (typed?.id && typed.instance_id) {
                        getWebhookSecretMutation.mutate({ branchId: typed.id });
                    }
                },
            },
        );
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
        let workingPayload = workingHours.value;
        let bookingPayload = bookingSettings.value;
        let nextWorkingJson: string | null = null;
        let nextBookingJson: string | null = null;
        if (!workingPayload) {
            const built = buildWorkingHoursPayload();
            if (built.error) {
                toast.error(built.error);
                return;
            }
            workingPayload = built.value;
            if (built.value) {
                nextWorkingJson = JSON.stringify(built.value, null, 2);
            }
        }
        if (!bookingPayload) {
            const built = buildBookingSettingsPayload();
            if (built.error) {
                toast.error(built.error);
                return;
            }
            bookingPayload = built.value;
            if (built.value) {
                nextBookingJson = JSON.stringify(built.value, null, 2);
            }
        }
        if (!workingPayload && !bookingPayload) {
            toast.error("Заполните working_hours или booking_settings");
            return;
        }
        if (nextWorkingJson || nextBookingJson) {
            setBranchForm((prev) => ({
                ...prev,
                workingHours: nextWorkingJson ?? prev.workingHours,
                bookingSettings: nextBookingJson ?? prev.bookingSettings,
            }));
        }
        patchBranchMutation.mutate({
            working_hours: workingPayload,
            booking_settings: bookingPayload,
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
        if (roleValue === "manager" || roleValue === "specialist") {
            const branchId = agentForm.branchId || branchData?.id;
            if (!branchId) {
                toast.error("branch_id обязателен для manager/specialist");
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
        const sanitized = normalizeCapabilities(capabilitiesDraft);
        sanitized.domain_slug = sanitized.domain_slug?.trim() || null;
        patchCapabilitiesMutation.mutate({
            scope: "branch",
            branch_id: branchData.id,
            payload: sanitized,
        });
    };

    const handleSaveOnboardingContract = () => {
        if (!branchData?.id || !clientId) {
            toast.error("Нужны client_id и branch_id");
            return;
        }
        const parsedPurchased = parseOptionalJson(purchasedJsonDraft, "purchased");
        if (parsedPurchased.error) {
            toast.error(parsedPurchased.error);
            return;
        }
        const payload: OnboardingContractPayload = {
            domain_slug: onboardingContractDraft.domain_slug?.trim() || null,
            purchased: normalizeCapabilities((parsedPurchased.value as CapabilitiesPayload) ?? null),
        };
        const requestPayload: components["schemas"]["OnboardingContractPatchRequest"] = {
            scope: "branch",
            branch_id: branchData.id,
            payload,
        };
        if (canManagePayment) {
            requestPayload.payment_status = paymentStatusDraft;
        }
        patchOnboardingContractMutation.mutate(requestPayload);
    };

    const handleUpsertReferencePack = () => {
        if (!canManageReferencePacks) {
            toast.error("Только platform_admin может управлять reference packs");
            return;
        }
        const domainSlug = referencePackDomainSlug.trim();
        if (!domainSlug) {
            toast.error("Укажите domain_slug");
            return;
        }
        const title = referencePackTitle.trim() || `Reference pack: ${domainSlug}`;
        upsertReferencePackMutation.mutate({ domainSlug, title });
    };

    const handleReset = () => {
        setOnboardingMode("autopilot");
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
        setWorkingHoursDays([]);
        setWorkingHoursStart("");
        setWorkingHoursEnd("");
        setBookingDefaultDuration("");
        setBookingBufferMin("");
        setCreatedAgents([]);
        setCapabilitiesDraft(normalizeCapabilities());
        setCapabilitiesTouched(false);
        setCapabilitiesSavedAt(null);
        setOnboardingContractDraft(normalizeOnboardingContractPayload());
        setOnboardingContractTouched(false);
        setOnboardingContractSavedAt(null);
        setPurchasedJsonDraft("{}");
        setPaymentStatusDraft("pending");
        setReferencePackTitle("");
        setSpecialistsConfirmed(false);
        setAgentForm({
            name: "",
            role: "owner",
            oidcSubject: "",
            branchId: "",
        });
        setAutopilotForm({
            companyName: "",
            clientSlug: "",
            branchName: "",
            branchSlug: "",
            timezone: DEFAULT_TIMEZONE,
            phone: "",
            instanceId: "",
            domainSlug: "beauty",
            paymentStatus: "pending",
            clientDataText: "",
        });
        setAutopilotServices(["whatsapp"]);
        setAutopilotResult(null);
        setIntegrationWebhookSecret("");
        setIntegrationWebhookUrl("");
    };

    const currentStep = WIZARD_STEPS[stepIndex];
    const currentStepState = stepStateById[currentStep.id];
    const currentStepMissing = currentStepState?.missing ?? [];
    const currentStepMissingLabels = currentStepMissing.map((item) => formatMissingRequirement(item));
    const currentStepLocked = currentStepState?.status === "locked";
    const advanceBlocked = currentStepLocked || (currentStepState?.required && currentStepMissing.length > 0);
    const currentStepFieldGuide = MANUAL_STEP_FIELD_GUIDE[currentStep.id];

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
                    Provisioning доступен только для owner/admin/platform admin.
                </div>
            )}

            <div className="mt-6 rounded-xl border border-border/60 bg-card p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Режим онбординга</div>
                <div className="mt-3 flex flex-wrap gap-2">
                    <button
                        type="button"
                        className={`rounded-lg border px-3 py-2 text-sm ${
                            onboardingMode === "autopilot"
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border/60 bg-background"
                        }`}
                        onClick={() => setOnboardingMode("autopilot")}
                    >
                        Автопроцесс (Recommended)
                    </button>
                    <button
                        type="button"
                        className={`rounded-lg border px-3 py-2 text-sm ${
                            onboardingMode === "manual"
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border/60 bg-background"
                        }`}
                        onClick={() => setOnboardingMode("manual")}
                    >
                        Ручной по шагам
                    </button>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                    Автопроцесс: минимальные входы и авто-связка сущностей. Ручной режим: детальная настройка шага за шагом.
                </p>
            </div>

            {onboardingMode === "autopilot" && (
            <div className="mt-6 rounded-xl border border-border/60 bg-muted/10 p-4 space-y-4" data-testid="onboarding-autopilot">
                <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                        Single-Operator Autopilot
                    </h3>
                    <p className="text-sm text-muted-foreground mt-2">
                        Обязательные поля: `phone`, `instance_id`, `client_data_text`, минимум 1 услуга.
                        Для сущностей: `company_id` или `company_name`, `client_id` или `client_slug`.
                        Для нового филиала нужен `branch_name`.
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                        `webhook_secret` генерируется автоматически из `instance_id`.
                        Система создаёт/связывает Company/Client/Branch, contract/capabilities, reference pack и draft знаний.
                    </p>
                    <div className="mt-2 text-xs text-muted-foreground">
                        Связи: `phone` ↔ `branch.phone`; `instance_id` ↔ `branch.instance_id`; `webhook_secret` ↔ `branch.webhook_secret`.
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        Валидация перед запуском: {autopilotMissingInputs.length
                            ? `не готово (${autopilotMissingInputs.join(", ")})`
                            : "готово"}
                    </div>
                </div>

                <div className="rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
                        Field Contract
                    </div>
                    <div className="space-y-2">
                        {AUTOPILOT_FIELD_GUIDE.map((item) => (
                            <div key={item.field} className="rounded-lg border border-border/60 bg-muted/10 p-2 text-xs">
                                <div className="flex items-center justify-between">
                                    <span className="font-mono">{item.field}</span>
                                    <span>{item.required ? "required" : "optional"}</span>
                                </div>
                                <div className="mt-1 text-muted-foreground">
                                    Назначение: {item.purpose}
                                </div>
                                <div className="text-muted-foreground">
                                    Связь: {item.relation}
                                </div>
                                <div className="text-muted-foreground">
                                    Результат: {item.output}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Company name (если company_id пуст)"
                        value={autopilotForm.companyName}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, companyName: event.target.value }))}
                        disabled={!canEdit}
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Client slug (если client_id пуст)"
                        value={autopilotForm.clientSlug}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, clientSlug: event.target.value }))}
                        disabled={!canEdit}
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder={autopilotNeedsBranchName ? "Branch name *" : "Branch name (optional)"}
                        value={autopilotForm.branchName}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, branchName: event.target.value }))}
                        disabled={!canEdit}
                        required={autopilotNeedsBranchName}
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Branch slug (optional)"
                        value={autopilotForm.branchSlug}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, branchSlug: event.target.value }))}
                        disabled={!canEdit}
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Phone *"
                        value={autopilotForm.phone}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, phone: event.target.value }))}
                        disabled={!canEdit}
                        required
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="instance_id *"
                        value={autopilotForm.instanceId}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, instanceId: event.target.value }))}
                        disabled={!canEdit}
                        required
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="Timezone (например Asia/Almaty)"
                        value={autopilotForm.timezone}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, timezone: event.target.value }))}
                        disabled={!canEdit}
                    />
                    <input
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        placeholder="domain_slug (например beauty)"
                        value={autopilotForm.domainSlug}
                        onChange={(event) => setAutopilotForm((prev) => ({ ...prev, domainSlug: event.target.value }))}
                        disabled={!canEdit}
                    />
                    <select
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={autopilotForm.paymentStatus}
                        onChange={(event) => setAutopilotForm((prev) => ({
                            ...prev,
                            paymentStatus: event.target.value as "pending" | "confirmed" | "rejected",
                        }))}
                        disabled={!canEdit || !canManagePayment}
                    >
                        <option value="pending">payment: pending</option>
                        <option value="confirmed">payment: confirmed</option>
                        <option value="rejected">payment: rejected</option>
                    </select>
                </div>

                <div>
                    <div className="text-xs text-muted-foreground mb-2">Подключённые услуги</div>
                    <div className="flex flex-wrap gap-3">
                        {AUTOPILOT_SERVICE_OPTIONS.map((option) => (
                            <label key={option.id} className="inline-flex items-center gap-2 text-xs">
                                <input
                                    type="checkbox"
                                    checked={autopilotServices.includes(option.id)}
                                    onChange={() => handleToggleAutopilotService(option.id)}
                                    disabled={!canEdit}
                                />
                                {option.label}
                            </label>
                        ))}
                    </div>
                </div>

                <textarea
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                    rows={6}
                    placeholder="Данные клиента в свободной форме (адрес, часы, услуги, политики...) *"
                    value={autopilotForm.clientDataText}
                    onChange={(event) => setAutopilotForm((prev) => ({ ...prev, clientDataText: event.target.value }))}
                    disabled={!canEdit}
                    required
                />

                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={handleRunAutopilot}
                        disabled={!canRunAutopilot}
                    >
                        {runAutopilotMutation.isPending ? "Запуск..." : "Запустить автопроцесс"}
                    </button>
                    <span className="text-xs text-muted-foreground">
                        Payment статус: {canManagePayment ? "управляется в этом блоке" : "pending (не platform_admin)"}
                    </span>
                </div>

                {autopilotResult && (
                    <div className="rounded-lg border border-border/60 bg-background p-3 space-y-2 text-xs">
                        <div>
                            Company: <span className="font-mono">{autopilotResult.company.id}</span> | Client:{" "}
                            <span className="font-mono">{autopilotResult.client.id}</span> | Branch:{" "}
                            <span className="font-mono">{autopilotResult.branch.id}</span>
                        </div>
                        <div>
                            Go/No-Go missing:{" "}
                            {autopilotResult.go_no_go_missing.length
                                ? autopilotResult.go_no_go_missing.map((item) => formatMissingRequirement(item)).join(", ")
                                : "none"}
                        </div>
                        <div>
                            Webhook secret: <span className="font-mono">{autopilotResult.webhook_secret}</span>
                        </div>
                        <div className="break-all">
                            Webhook URL: <span className="font-mono">{autopilotResult.webhook_url}</span>
                        </div>
                        <div>
                            Intake missing fields:{" "}
                            {autopilotResult.intake.missing_fields.length
                                ? autopilotResult.intake.missing_fields.map((item) => formatMissingRequirement(item)).join(", ")
                                : "none"}
                        </div>
                        {autopilotResult.intake.missing_questions.length > 0 && (
                            <div>
                                Вопросы для дозаполнения: {autopilotResult.intake.missing_questions.join(" | ")}
                            </div>
                        )}
                        <div className="pt-1">
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => setOnboardingMode("manual")}
                            >
                                Перейти в ручной режим для донастройки
                            </button>
                        </div>
                    </div>
                )}
            </div>
            )}

            {onboardingMode === "manual" && (
            <>
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
                    <label className="mt-3 block text-xs text-muted-foreground">billing_info</label>
                    <div className="mt-2 space-y-3 rounded-lg border border-border/60 bg-muted/10 p-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <label className="text-xs text-muted-foreground">Договор</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={billingContract}
                                    onChange={(event) => setBillingContract(event.target.value)}
                                    placeholder="B2B"
                                    disabled={!canEdit}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Валюта</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={billingCurrency}
                                    onChange={(event) => setBillingCurrency(event.target.value)}
                                    placeholder="KZT"
                                    disabled={!canEdit}
                                />
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={applyBillingToJson}
                                disabled={!canEdit}
                            >
                                Применить в JSON
                            </button>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={loadBillingFromJson}
                                disabled={!canEdit}
                            >
                                Загрузить из JSON
                            </button>
                        </div>
                        <details className="rounded-lg border border-border/60 bg-background p-3">
                            <summary className="cursor-pointer text-xs text-muted-foreground">
                                billing_info JSON
                            </summary>
                            <textarea
                                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                rows={3}
                                value={billingInfo}
                                onChange={(event) => setBillingInfo(event.target.value)}
                                placeholder='{"contract":"B2B","currency":"KZT"}'
                                disabled={!canEdit}
                            />
                        </details>
                    </div>
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
                    <label className="mt-3 block text-xs text-muted-foreground">Company ID</label>
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
                        disabled={!canEdit || createClientMutation.isPending || !companyId.trim()}
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
                    const stepState = stepStateById[step.id];
                    const locked = stepState?.status === "locked";
                    const statusLabel = stepState?.status === "skipped"
                        ? "Пропущено"
                        : completed
                            ? "Готово"
                            : step.hint;
                    return (
                        <button
                            key={step.id}
                            type="button"
                            onClick={() => setStepIndex(index)}
                            disabled={locked}
                            className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                                active
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : locked
                                        ? "border-border/40 bg-muted text-muted-foreground cursor-not-allowed"
                                        : "border-border/60 bg-card hover:bg-muted"
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
                                    {statusLabel}
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

                {currentStepMissing.length > 0 && (
                    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        <div className="font-semibold">Нужно завершить перед продолжением:</div>
                        <div className="mt-1">{currentStepMissingLabels.join(", ")}</div>
                    </div>
                )}

                <div className="mb-4 rounded-lg border border-border/60 bg-muted/10 p-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
                        Field Contract
                    </div>
                    <div className="space-y-2">
                        {currentStepFieldGuide.map((item) => (
                            <div key={item.field} className="rounded-lg border border-border/60 bg-background p-2 text-xs">
                                <div className="flex items-center justify-between">
                                    <span className="font-mono">{item.field}</span>
                                    <span>{item.required ? "required" : "optional"}</span>
                                </div>
                                <div className="mt-1 text-muted-foreground">
                                    Назначение: {item.purpose}
                                </div>
                                <div className="text-muted-foreground">
                                    Связь: {item.relation}
                                </div>
                                <div className="text-muted-foreground">
                                    Результат: {item.output}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {currentStep.id === "branch_draft" && (
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
                        <div className="rounded-lg border border-border/60 bg-muted/20 p-3 space-y-3">
                            <label className="flex items-center gap-2 text-sm font-medium">
                                <input
                                    type="checkbox"
                                    checked={branchBootstrap.enabled}
                                    onChange={(event) =>
                                        setBranchBootstrap((prev) => ({ ...prev, enabled: event.target.checked }))
                                    }
                                    disabled={!canEdit}
                                />
                                Branch Account Factory (owner/admin/manager)
                            </label>
                            {branchBootstrap.enabled && (
                                <div className="space-y-3">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        <label className="text-xs text-muted-foreground">
                                            <span className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    checked={branchBootstrap.createOwner}
                                                    onChange={(event) =>
                                                        setBranchBootstrap((prev) => ({
                                                            ...prev,
                                                            createOwner: event.target.checked,
                                                        }))
                                                    }
                                                    disabled={!canEdit}
                                                />
                                                owner
                                            </span>
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.ownerName}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({ ...prev, ownerName: event.target.value }))
                                                }
                                                placeholder="Имя owner"
                                                disabled={!canEdit || !branchBootstrap.createOwner}
                                            />
                                        </label>
                                        <label className="text-xs text-muted-foreground">
                                            <span className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    checked={branchBootstrap.createAdmin}
                                                    onChange={(event) =>
                                                        setBranchBootstrap((prev) => ({
                                                            ...prev,
                                                            createAdmin: event.target.checked,
                                                        }))
                                                    }
                                                    disabled={!canEdit}
                                                />
                                                admin
                                            </span>
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.adminName}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({ ...prev, adminName: event.target.value }))
                                                }
                                                placeholder="Имя admin"
                                                disabled={!canEdit || !branchBootstrap.createAdmin}
                                            />
                                        </label>
                                        <label className="text-xs text-muted-foreground">
                                            <span className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    checked={branchBootstrap.createManager}
                                                    onChange={(event) =>
                                                        setBranchBootstrap((prev) => ({
                                                            ...prev,
                                                            createManager: event.target.checked,
                                                        }))
                                                    }
                                                    disabled={!canEdit}
                                                />
                                                manager
                                            </span>
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.managerName}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({ ...prev, managerName: event.target.value }))
                                                }
                                                placeholder="Имя manager"
                                                disabled={!canEdit || !branchBootstrap.createManager}
                                            />
                                        </label>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        <label className="text-xs text-muted-foreground">
                                            owner oidc_subject (optional)
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.ownerOidcSubject}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({
                                                        ...prev,
                                                        ownerOidcSubject: event.target.value,
                                                    }))
                                                }
                                                placeholder="oidc-sub-owner"
                                                disabled={!canEdit || !branchBootstrap.createOwner}
                                            />
                                        </label>
                                        <label className="text-xs text-muted-foreground">
                                            admin oidc_subject (optional)
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.adminOidcSubject}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({
                                                        ...prev,
                                                        adminOidcSubject: event.target.value,
                                                    }))
                                                }
                                                placeholder="oidc-sub-admin"
                                                disabled={!canEdit || !branchBootstrap.createAdmin}
                                            />
                                        </label>
                                        <label className="text-xs text-muted-foreground">
                                            manager oidc_subject (optional)
                                            <input
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={branchBootstrap.managerOidcSubject}
                                                onChange={(event) =>
                                                    setBranchBootstrap((prev) => ({
                                                        ...prev,
                                                        managerOidcSubject: event.target.value,
                                                    }))
                                                }
                                                placeholder="oidc-sub-manager"
                                                disabled={!canEdit || !branchBootstrap.createManager}
                                            />
                                        </label>
                                    </div>
                                </div>
                            )}
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
                            Для WA интеграции нужны оба поля: `instance_id` и `phone`. Без них филиал остаётся draft.
                        </p>
                        <div>
                            <label className="text-xs text-muted-foreground">phone (WA номер филиала)</label>
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={branchForm.phone}
                                onChange={(event) => setBranchForm((prev) => ({ ...prev, phone: event.target.value }))}
                                placeholder="+7 777 000 00 00"
                                disabled={!canEdit}
                            />
                        </div>
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
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => {
                                if (!branchData?.id) {
                                    toast.error("Сначала создайте филиал");
                                    return;
                                }
                                getWebhookSecretMutation.mutate({ branchId: branchData.id });
                            }}
                            disabled={!canEdit || !branchData?.id || getWebhookSecretMutation.isPending}
                        >
                            {getWebhookSecretMutation.isPending ? "Генерация..." : "Получить webhook secret"}
                        </button>
                        {integrationWebhookSecret && (
                            <div className="rounded-lg border border-border/60 bg-background p-3 text-xs space-y-2">
                                <div>
                                    Webhook secret: <span className="font-mono">{integrationWebhookSecret}</span>
                                </div>
                                {integrationWebhookUrl && (
                                    <div className="break-all">
                                        URL для ChatFlow: <span className="font-mono">{integrationWebhookUrl}</span>
                                    </div>
                                )}
                            </div>
                        )}
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
                            Создайте owner/admin пользователей для доступа в Console. Manager/Specialist требуют branch_id.
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
                                    <option value="specialist">specialist</option>
                                    <option value="support">support</option>
                                    <option value="viewer">viewer</option>
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
                                    disabled={!canEdit || !["manager", "specialist"].includes(agentForm.role)}
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
                            <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3">
                                <h4 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                                    Working hours
                                </h4>
                                <div>
                                    <label className="text-xs text-muted-foreground">Рабочие дни</label>
                                    <div className="mt-2 flex flex-wrap gap-3">
                                        {WORKING_DAYS.map((day) => (
                                            <label key={day.id} className="flex items-center gap-2 text-xs">
                                                <input
                                                    type="checkbox"
                                                    checked={workingHoursDays.includes(day.id)}
                                                    onChange={(event) => {
                                                        const checked = event.target.checked;
                                                        setWorkingHoursDays((prev) => {
                                                            const next = checked
                                                                ? [...prev, day.id]
                                                                : prev.filter((item) => item !== day.id);
                                                            const ordered = WORKING_DAYS.map((item) => item.id);
                                                            return ordered.filter((item) => next.includes(item));
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                />
                                                {day.label}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label className="text-xs text-muted-foreground">Открытие</label>
                                        <input
                                            type="time"
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={workingHoursStart}
                                            onChange={(event) => setWorkingHoursStart(event.target.value)}
                                            disabled={!canEdit}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">Закрытие</label>
                                        <input
                                            type="time"
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={workingHoursEnd}
                                            onChange={(event) => setWorkingHoursEnd(event.target.value)}
                                            disabled={!canEdit}
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2 text-xs">
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={applyWorkingHoursToJson}
                                        disabled={!canEdit}
                                    >
                                        Применить в JSON
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={loadWorkingHoursFromJson}
                                        disabled={!canEdit}
                                    >
                                        Загрузить из JSON
                                    </button>
                                </div>
                                <details className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                    <summary className="cursor-pointer text-xs text-muted-foreground">
                                        working_hours JSON
                                    </summary>
                                    <textarea
                                        className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                        rows={6}
                                        value={branchForm.workingHours}
                                        onChange={(event) => setBranchForm((prev) => ({ ...prev, workingHours: event.target.value }))}
                                        placeholder='{"mon":[{"start":"09:00","end":"20:00"}]}'
                                        disabled={!canEdit}
                                    />
                                </details>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3">
                                <h4 className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                                    Booking settings
                                </h4>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label className="text-xs text-muted-foreground">Длительность, мин</label>
                                        <input
                                            type="number"
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={bookingDefaultDuration}
                                            onChange={(event) => setBookingDefaultDuration(event.target.value)}
                                            placeholder="60"
                                            min={0}
                                            disabled={!canEdit}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">Буфер, мин</label>
                                        <input
                                            type="number"
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={bookingBufferMin}
                                            onChange={(event) => setBookingBufferMin(event.target.value)}
                                            placeholder="10"
                                            min={0}
                                            disabled={!canEdit}
                                        />
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2 text-xs">
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={applyBookingSettingsToJson}
                                        disabled={!canEdit}
                                    >
                                        Применить в JSON
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={loadBookingSettingsFromJson}
                                        disabled={!canEdit}
                                    >
                                        Загрузить из JSON
                                    </button>
                                </div>
                                <details className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                    <summary className="cursor-pointer text-xs text-muted-foreground">
                                        booking_settings JSON
                                    </summary>
                                    <textarea
                                        className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                        rows={6}
                                        value={branchForm.bookingSettings}
                                        onChange={(event) => setBranchForm((prev) => ({ ...prev, bookingSettings: event.target.value }))}
                                        placeholder='{"default_duration_min":60,"buffer_min":10}'
                                        disabled={!canEdit}
                                    />
                                </details>
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

                {currentStep.id === "go_no_go" && (
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
                                {capabilityMismatches.length > 0 && (
                                    <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                                        <div className="font-semibold">Несоответствие с договором:</div>
                                        <div className="mt-1">
                                            {capabilityMismatches
                                                .map((item) => CAPABILITY_FIELD_LABELS[item] ?? item)
                                                .join(", ")}
                                        </div>
                                    </div>
                                )}
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

                                <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-3">
                                    <h5 className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                        Onboarding Contract
                                    </h5>
                                    <div>
                                        <label className="text-xs text-muted-foreground">domain_slug (niche)</label>
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={onboardingContractDraft.domain_slug ?? ""}
                                            onChange={(event) => {
                                                setOnboardingContractTouched(true);
                                                setOnboardingContractDraft((prev) => ({
                                                    ...normalizeOnboardingContractPayload(prev),
                                                    domain_slug: event.target.value || null,
                                                }));
                                            }}
                                            placeholder="beauty"
                                            disabled={!canEdit}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">purchased (JSON)</label>
                                        <textarea
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                            rows={8}
                                            value={purchasedJsonDraft}
                                            onChange={(event) => {
                                                setOnboardingContractTouched(true);
                                                setPurchasedJsonDraft(event.target.value);
                                            }}
                                            placeholder='{"channels":{"whatsapp":true}}'
                                            disabled={!canEdit}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">payment_status</label>
                                        <select
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={paymentStatusDraft}
                                            onChange={(event) => {
                                                setPaymentStatusDraft(event.target.value as "pending" | "confirmed" | "rejected");
                                            }}
                                            disabled={!canManagePayment}
                                        >
                                            <option value="pending">pending</option>
                                            <option value="confirmed">confirmed</option>
                                            <option value="rejected">rejected</option>
                                        </select>
                                        {!canManagePayment && (
                                            <p className="mt-1 text-[11px] text-muted-foreground">
                                                Изменение payment_status доступно только platform_admin.
                                            </p>
                                        )}
                                    </div>
                                    <button
                                        type="button"
                                        className="btn-primary w-full"
                                        onClick={handleSaveOnboardingContract}
                                        disabled={!canEdit || patchOnboardingContractMutation.isPending}
                                    >
                                        {patchOnboardingContractMutation.isPending ? "Сохранение..." : "Сохранить onboarding contract"}
                                    </button>
                                    {onboardingContractSavedAt && (
                                        <p className="text-xs text-muted-foreground">
                                            Сохранено: {new Date(onboardingContractSavedAt).toLocaleString("ru-RU")}
                                        </p>
                                    )}
                                    {onboardingContractLoading && (
                                        <p className="text-xs text-muted-foreground">Загрузка onboarding contract...</p>
                                    )}
                                    {onboardingContractError && (
                                        <p className="text-xs text-destructive">Не удалось загрузить onboarding contract.</p>
                                    )}
                                </div>

                                <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-2">
                                    <h5 className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                        Reference Pack
                                    </h5>
                                    <p className="text-xs">
                                        domain_slug: <span className="font-mono">{referencePackDomainSlug || "—"}</span>
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {referencePackLoading
                                            ? "Проверка reference pack..."
                                            : referencePackError
                                                ? "Ошибка проверки reference pack."
                                                : hasActiveReferencePack
                                                    ? "active"
                                                    : "не найден"}
                                    </p>
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={referencePackTitle}
                                        onChange={(event) => setReferencePackTitle(event.target.value)}
                                        placeholder="Название эталона"
                                        disabled={!canManageReferencePacks}
                                    />
                                    <button
                                        type="button"
                                        className="btn-ghost w-full"
                                        onClick={handleUpsertReferencePack}
                                        disabled={!canManageReferencePacks || upsertReferencePackMutation.isPending}
                                    >
                                        {upsertReferencePackMutation.isPending ? "Сохранение..." : "Создать/обновить reference pack"}
                                    </button>
                                </div>

                                <button
                                    type="button"
                                    className="btn-primary w-full"
                                    onClick={handleSaveCapabilities}
                                    disabled={!canEdit || patchCapabilitiesMutation.isPending}
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
                            {effectiveCapabilities && (
                                <div className="space-y-3">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                        <div className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                                Domain
                                            </div>
                                            <div className="mt-2 flex items-center justify-between">
                                                <span>domain_slug</span>
                                                <span className="font-mono">
                                                    {formatEffectiveValue(effectiveCapabilities.domain_slug)}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                                Channels
                                            </div>
                                            <div className="mt-2 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span>whatsapp</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.channels?.whatsapp)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>telegram</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.channels?.telegram)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>instagram</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.channels?.instagram)}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                                Providers
                                            </div>
                                            <div className="mt-2 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span>availability</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.providers?.availability_provider)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>crm</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.providers?.crm_provider)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>calendar</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.providers?.calendar_provider)}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                            <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                                Features
                                            </div>
                                            <div className="mt-2 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span>booking_mode</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.features?.booking_mode)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>knowledge_upload</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.features?.knowledge_upload)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>analytics</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.features?.analytics)}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span>auto_learn</span>
                                                    <span>{formatEffectiveValue(effectiveCapabilities.features?.auto_learn)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <details className="rounded-lg border border-border/60 bg-background p-3">
                                        <summary className="cursor-pointer text-xs text-muted-foreground">
                                            Raw JSON
                                        </summary>
                                        <pre className="mt-2 text-xs bg-muted/40 border border-border/60 rounded-lg p-3 overflow-auto">
                                            {JSON.stringify(effectiveCapabilities, null, 2)}
                                        </pre>
                                    </details>
                                </div>
                            )}
                            {!capabilitiesLoading && !effectiveCapabilities && (
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
                        onClick={() => advanceOnboardingMutation.mutate(currentStep.id)}
                        disabled={
                            stepIndex === WIZARD_STEPS.length - 1
                            || (stepIndex === 0 && !branchData?.id)
                            || advanceBlocked
                            || advanceOnboardingMutation.isPending
                        }
                    >
                        {advanceOnboardingMutation.isPending ? "Проверка..." : "Далее"}
                    </button>
                </div>
            </div>
            </>
            )}
        </div>
    );
}

export default ProvisioningWizard;
