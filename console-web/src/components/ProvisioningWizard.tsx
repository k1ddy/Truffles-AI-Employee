"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import {
    adminApi,
    authApi,
    canAccessConsole,
    onboardingApi,
    type BranchGoLiveDecisionRequest,
    type BranchGoLiveWaiverRequest,
    type ConsoleRole,
    type ConsoleSection,
    type OnboardingBlueprintListResponse,
} from "@/lib/api-client";
import { writeConsoleContextScopeToStorage } from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";

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
type OnboardingScorecard = components["schemas"]["OnboardingScorecardResponse"];
type OnboardingScorecardCheck = components["schemas"]["OnboardingScorecardCheck"];
type OnboardingDocumentIngestion = components["schemas"]["OnboardingDocumentIngestion"];
type OnboardingIntakeFieldState = components["schemas"]["OnboardingIntakeFieldState"];
type OnboardingIntakeQuestion = components["schemas"]["OnboardingIntakeQuestion"];
type OnboardingIntakeQualityDimension = components["schemas"]["OnboardingIntakeQualityDimension"];

type OnboardingSlaControlLoop = {
    status: "pass" | "warn" | "fail";
    reminder_1_minutes: number;
    reminder_2_minutes: number;
    escalation_timeout_minutes: number;
    pending_total: number;
    warning_total: number;
    breached_total: number;
    provider_status: string;
    provider_paid_until?: string | null;
    provider_days_to_renewal?: number | null;
    provider_alert_state?: string | null;
    active_incidents?: string[];
    recommended_actions?: string[];
};

type OnboardingOperationalStage = {
    id: string;
    label: string;
    owner_lane: string;
    required: boolean;
    status: "pass" | "warn" | "fail" | "skip";
    blockers: string[];
    next_action?: string | null;
};

type OnboardingOperationalPipeline = {
    status: "pass" | "warn" | "fail";
    blocked: boolean;
    current_stage_id?: string | null;
    blockers?: string[];
    next_actions?: string[];
    stages?: OnboardingOperationalStage[];
};

type OnboardingScorecardEnterprise = OnboardingScorecard & {
    sla_control_loop?: OnboardingSlaControlLoop | null;
    operational_pipeline?: OnboardingOperationalPipeline | null;
};

type AgentRole = ConsoleRole;
type OnboardingMode = "autopilot" | "manual";

type DomainTemplatePreset = {
    id: string;
    label: string;
    summary: string;
    payload: CapabilitiesPayload;
};

const DEFAULT_TIMEZONE = "Asia/Almaty";
const PROVISIONING_ASSIGNABLE_AGENT_ROLES: AgentRole[] = ["owner", "admin", "manager", "viewer"];
const DOMAIN_SLUG_RE = /^[a-z0-9_]+$/;
const ISO_CURRENCY_RE = /^[A-Z]{3}$/;
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
    { id: "branch_draft", label: "Филиал", hint: "Черновик" },
    { id: "integrations", label: "Интеграции", hint: "instance_id" },
    { id: "team", label: "Команда", hint: "владелец/админ" },
    { id: "telegram", label: "Telegram", hint: "chat_id" },
    { id: "knowledge", label: "Знания", hint: "pack" },
    { id: "booking", label: "Бронирование", hint: "calendar" },
    { id: "go_no_go", label: "Go/No-Go", hint: "готовность" },
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
    reference_pack_integrity: "Reference pack integrity",
    reference_pack_schema_version: "Reference pack schema_version (v2)",
    reference_pack_metadata: "Reference pack metadata",
    reference_pack_integrity_version: "Reference pack integrity version",
    reference_pack_minimum_data_contract_version: "Reference pack min data contract version",
    reference_pack_required_fields: "Reference pack required fields snapshot",
    reference_pack_required_fields_checksum: "Reference pack required fields checksum",
    branch_active: "Филиал активен",
    "provider_binding.whatsapp": "Provider binding (WhatsApp)",
    "provider_binding.whatsapp.provider": "Provider binding: provider",
    "provider_binding.whatsapp.instance_id": "Provider binding: instance_id",
    "provider_binding.whatsapp.instance_id_mismatch": "Provider binding: instance_id не совпадает с branch",
    "provider_binding.whatsapp.webhook_status": "Provider binding: webhook_status=configured",
    "provider_binding.whatsapp.owner": "Provider binding: owner",
    "provider_binding.whatsapp.next_renewal_at": "Provider binding: next_renewal_at",
    "provider_binding.whatsapp.paid_until": "Provider binding: paid_until",
    "provider_binding.whatsapp.paid_until_expired": "Provider binding: paid_until истёк",
    "provider_binding.whatsapp.rebind_required": "Provider binding: rebind required",
    "provider_binding.whatsapp.alert_state": "Provider binding: capability check (alert_state)",
    "provider_binding.whatsapp.capability_check_failed": "Provider binding: capability check failed (alert_state=critical)",
    document_ingestion_invalid: "Document ingestion gate",
    "client_pack.business.name": "Профиль бизнеса: название",
    "client_pack.location.city": "Локация: город",
    "client_pack.location.address.full": "Локация: адрес",
    "client_pack.operations.hours.days": "График работы: дни",
    "client_pack.operations.hours.open": "График работы: открытие",
    "client_pack.operations.hours.close": "График работы: закрытие",
    "client_pack.catalog.summary": "Каталог: кратко об услугах",
    "client_pack.communication.languages": "Коммуникация: языки",
    "client_pack.salon.name": "Профиль бизнеса: название",
    "client_pack.salon.city": "Локация: город",
    "client_pack.salon.address.full": "Локация: адрес",
    "client_pack.salon.hours.days": "График работы: дни",
    "client_pack.salon.hours.open": "График работы: открытие",
    "client_pack.salon.hours.close": "График работы: закрытие",
    "client_pack.salon.services_summary": "Каталог: кратко об услугах",
    "client_pack.salon.communication.languages": "Коммуникация: языки",
    "client_pack.services_catalog.services": "Каталог: услуги",
    "client_pack.service_duration_estimates": "Каталог: длительности услуг",
    "client_pack.booking.collect_fields": "Booking: обязательные поля",
    "client_pack.booking.bot_can_confirm": "Booking: подтверждение",
    "client_pack.guest_policy": "Политика гостей",
    "client_pack.safety.medical_note": "Дисклеймер: противопоказания",
    "client_pack.pricing.price_from_reason": "Дисклеймер: цена \"от\"",
    "client_pack.quality.expectations_photo": "Дисклеймер: ожидания/референс",
    "client_pack.price_list": "Прайс-лист",
    "client_pack.policy.hard_law": "Политика: hard_law",
    "client_pack.policy.payment_info": "Политика: оплата",
    "client_pack.policy.reschedule": "Политика: перенос",
    "client_pack.policy.cancel": "Политика: отмена",
    "client_pack.policy.medical": "Политика: медицинские ограничения",
    "client_pack.policy.legal": "Политика: юридические ограничения",
    "client_pack.policy.complaint": "Политика: жалобы",
    "client_pack.policy.discounts": "Политика: скидки",
    "client_pack.policy.guard_topics.refund": "Политика: refund keywords",
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

const SLA_INCIDENT_LABELS: Record<string, string> = {
    handover_sla_breached: "Просроченные handover в очереди",
    handover_sla_warning: "Handover близко к SLA-нарушению",
    provider_binding_missing: "Не заполнен provider binding",
    provider_webhook_not_configured: "Webhook provider не сконфигурирован",
    provider_rebind_required: "Требуется rebind provider",
    provider_billing_expired: "Подписка provider истекла",
    provider_renewal_due: "Скоро продление provider",
    provider_capability_alert_critical: "Provider capability check: critical",
    provider_capability_alert_warn: "Provider capability check: warn",
};

const PIPELINE_ACTION_LABELS: Record<string, string> = {
    complete_contract_and_payment: "Закрыть договор и оплату",
    fix_channel_bindings: "Починить channel bindings",
    publish_knowledge_pack: "Опубликовать knowledge pack",
    configure_booking_runtime: "Настроить booking runtime",
    resolve_go_live_blockers: "Снять go-live блокеры",
    resolve_breached_handovers: "Разобрать просроченные handover",
    review_pending_handovers: "Проверить pending handover",
    fix_provider_binding: "Исправить provider binding",
    renew_provider_subscription_urgent: "Срочно продлить provider",
    renew_provider_subscription: "Продлить provider",
    run_provider_capability_check: "Проверить provider capability",
    monitor_sla_loop: "Мониторить SLA контрольный цикл",
    monitor_go_live_readiness: "Мониторить go-live readiness",
};

const SLA_PROVIDER_STATUS_LABELS: Record<string, string> = {
    configured: "configured",
    missing: "missing",
    webhook_not_configured: "webhook_not_configured",
    rebind_required: "rebind_required",
    billing_expired: "billing_expired",
    renewal_due: "renewal_due",
    not_required: "not_required",
    unknown: "unknown",
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

const FALLBACK_DOMAIN_TEMPLATE_PRESETS: DomainTemplatePreset[] = [
    {
        id: "beauty",
        label: "Beauty / Salon",
        summary: "WhatsApp+Telegram, запись, knowledge upload",
        payload: {
            domain_slug: "beauty",
            channels: { whatsapp: true, telegram: true, instagram: null },
            providers: { availability_provider: "google_calendar", crm_provider: "amocrm", calendar_provider: "google_calendar" },
            features: { booking_mode: "confirm_slots", knowledge_upload: true, analytics: true, auto_learn: false },
        },
    },
    {
        id: "clinic",
        label: "Clinic",
        summary: "WhatsApp, запись через календарь, строгий ручной контроль",
        payload: {
            domain_slug: "clinic",
            channels: { whatsapp: true, telegram: false, instagram: null },
            providers: { availability_provider: "google_calendar", crm_provider: "custom", calendar_provider: "google_calendar" },
            features: { booking_mode: "confirm_slots", knowledge_upload: true, analytics: true, auto_learn: false },
        },
    },
    {
        id: "legal",
        label: "Legal",
        summary: "Консультационный режим без слот-подтверждения",
        payload: {
            domain_slug: "legal",
            channels: { whatsapp: true, telegram: true, instagram: false },
            providers: { availability_provider: "manual", crm_provider: "none", calendar_provider: "local" },
            features: { booking_mode: "collect_preferences", knowledge_upload: true, analytics: true, auto_learn: false },
        },
    },
    {
        id: "ecom",
        label: "E-commerce",
        summary: "Мультиканал и аналитика, без confirm-slots по умолчанию",
        payload: {
            domain_slug: "ecom",
            channels: { whatsapp: true, telegram: true, instagram: true },
            providers: { availability_provider: "none", crm_provider: "bitrix", calendar_provider: "none" },
            features: { booking_mode: "collect_preferences", knowledge_upload: true, analytics: true, auto_learn: true },
        },
    },
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

function formatSlaIncident(code: string): string {
    return SLA_INCIDENT_LABELS[code] ?? code;
}

function formatPipelineAction(code: string): string {
    return PIPELINE_ACTION_LABELS[code] ?? code;
}

function formatSlaProviderStatus(status?: string): string {
    if (!status) {
        return "unknown";
    }
    return SLA_PROVIDER_STATUS_LABELS[status] ?? status;
}

function formatOperationalBlocker(code: string): string {
    if (
        code.startsWith("capability_mismatch:")
        || code.startsWith("provider_binding.whatsapp")
        || code.startsWith("client_pack.")
        || code.startsWith("reference_pack")
        || Object.prototype.hasOwnProperty.call(MISSING_LABELS, code)
    ) {
        return formatMissingRequirement(code);
    }
    return formatSlaIncident(code);
}

function onboardingStepStatusLabel(status: "complete" | "available" | "locked" | "skipped"): string {
    if (status === "complete") {
        return "выполнен";
    }
    if (status === "available") {
        return "доступен";
    }
    if (status === "locked") {
        return "заблокирован";
    }
    return "пропущен";
}

function onboardingStepStatusClass(status: "complete" | "available" | "locked" | "skipped"): string {
    if (status === "complete") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (status === "available") {
        return "border-blue-200 bg-blue-50 text-blue-800";
    }
    if (status === "locked") {
        return "border-border/60 bg-muted/40 text-muted-foreground";
    }
    return "border-amber-200 bg-amber-50 text-amber-800";
}

function intakePriorityLabel(value?: string): string {
    if (value === "critical") {
        return "critical";
    }
    if (value === "high") {
        return "high";
    }
    if (value === "medium") {
        return "medium";
    }
    return "low";
}

function intakePriorityClass(value?: string): string {
    if (value === "critical") {
        return "border-destructive/30 bg-destructive/10 text-destructive";
    }
    if (value === "high") {
        return "border-amber-300/60 bg-amber-50 text-amber-800";
    }
    if (value === "medium") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-border/60 bg-muted/40 text-muted-foreground";
}

function intakeStatusLabel(value?: string): string {
    if (value === "confirmed") {
        return "confirmed";
    }
    if (value === "assumed") {
        return "assumed";
    }
    return "unknown";
}

function intakeStatusClass(value?: string): string {
    if (value === "confirmed") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (value === "assumed") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-border/60 bg-muted/40 text-muted-foreground";
}

function qualityStatusLabel(value?: string): string {
    if (value === "pass") {
        return "pass";
    }
    if (value === "warn") {
        return "warn";
    }
    if (value === "skip") {
        return "skip";
    }
    return "fail";
}

function qualityStatusClass(value?: string): string {
    if (value === "pass") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (value === "warn") {
        return "border-amber-300/60 bg-amber-50 text-amber-800";
    }
    if (value === "skip") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-destructive/30 bg-destructive/10 text-destructive";
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
        provider_binding: {
            whatsapp: {
                provider: payload?.provider_binding?.whatsapp?.provider ?? null,
                instance_id: payload?.provider_binding?.whatsapp?.instance_id ?? null,
                webhook_status: payload?.provider_binding?.whatsapp?.webhook_status ?? null,
                paid_until: payload?.provider_binding?.whatsapp?.paid_until ?? null,
                owner: payload?.provider_binding?.whatsapp?.owner ?? null,
                next_renewal_at: payload?.provider_binding?.whatsapp?.next_renewal_at ?? null,
                last_rebind_at: payload?.provider_binding?.whatsapp?.last_rebind_at ?? null,
                rebind_required: payload?.provider_binding?.whatsapp?.rebind_required ?? null,
                alert_state: payload?.provider_binding?.whatsapp?.alert_state ?? null,
                notes: payload?.provider_binding?.whatsapp?.notes ?? null,
            },
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

function hasCapabilityValue(value: boolean | string | null | undefined): boolean {
    return value !== null && value !== undefined && value !== "";
}

function hasPurchasedSignal(payload: CapabilitiesPayload): boolean {
    return [
        payload.domain_slug,
        payload.channels.whatsapp,
        payload.channels.telegram,
        payload.channels.instagram,
        payload.providers.availability_provider,
        payload.providers.crm_provider,
        payload.providers.calendar_provider,
        payload.features.booking_mode,
        payload.features.knowledge_upload,
        payload.features.analytics,
        payload.features.auto_learn,
    ].some((value) => hasCapabilityValue(value));
}

type ProvisioningWizardProps = {
    session: SessionData;
    accessSection?: ConsoleSection;
};

function ProvisioningWizard({ session, accessSection = "settings" }: ProvisioningWizardProps) {
    const router = useRouter();
    const queryClient = useQueryClient();
    const {
        errors: inlineErrors,
        reportError,
        reportInlineError,
        clearErrors,
    } = useInlineErrorSummary();

    const reportValidationError = (message: string, code = "VALIDATION_ERROR") => {
        toast.error(message);
        reportInlineError({ code, message });
    };

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
    const [purchasedCapabilitiesDraft, setPurchasedCapabilitiesDraft] = useState<CapabilitiesPayload>(() => normalizeCapabilities());
    const [purchasedJsonDraft, setPurchasedJsonDraft] = useState("{}");
    const [purchasedJsonDirty, setPurchasedJsonDirty] = useState(false);
    const [selectedDomainTemplate, setSelectedDomainTemplate] = useState("beauty");
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
        providerBindingProvider: "chatflow",
        providerBindingWebhookStatus: "pending" as "configured" | "pending" | "rebind_required",
        providerBindingPaidUntil: "",
        providerBindingOwner: "",
        providerBindingNextRenewalAt: "",
        providerBindingLastRebindAt: "",
        providerBindingRebindRequired: false,
        providerBindingAlertState: "warn" as "ok" | "warn" | "critical",
        providerBindingNotes: "",
        clientDataText: "",
    });
    const [autopilotServices, setAutopilotServices] = useState<OnboardingPurchasedService[]>(["whatsapp"]);
    const [autopilotResult, setAutopilotResult] = useState<OnboardingAutopilotResponse | null>(null);
    const [goLiveDecisionReason, setGoLiveDecisionReason] = useState("");
    const [goLiveWaiverHours, setGoLiveWaiverHours] = useState("24");

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

    const buildBillingInfoPayload = (): { value?: Record<string, unknown>; error?: string } => {
        const payload: Record<string, unknown> = {};
        const contract = billingContract.trim();
        const currency = billingCurrency.trim().toUpperCase();
        if (contract && contract.length < 2) {
            return { error: "billing_info.contract: минимум 2 символа" };
        }
        if (currency && !ISO_CURRENCY_RE.test(currency)) {
            return { error: "billing_info.currency: используйте ISO-код (например KZT)" };
        }
        if (contract) {
            payload.contract = contract;
        }
        if (currency) {
            payload.currency = currency;
        }
        return { value: Object.keys(payload).length ? payload : undefined };
    };

    const applyBillingToJson = () => {
        const built = buildBillingInfoPayload();
        if (built.error) {
            reportValidationError(built.error);
            return;
        }
        setBillingInfo(built.value ? JSON.stringify(built.value, null, 2) : "");
    };

    const loadBillingFromJson = () => {
        const parsed = parseOptionalJson(billingInfo, "billing_info");
        if (parsed.error) {
            reportValidationError(parsed.error);
            return;
        }
        const payload = (parsed.value ?? {}) as Record<string, unknown>;
        const contract = payload.contract;
        const currency = payload.currency;
        setBillingContract(typeof contract === "string" ? contract : "");
        setBillingCurrency(typeof currency === "string" ? currency.toUpperCase() : "");
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
        if (start >= end) {
            return { error: "working_hours: время закрытия должно быть позже открытия" };
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
            reportValidationError(built.error);
            return;
        }
        const nextValue = built.value ? JSON.stringify(built.value, null, 2) : "";
        setBranchForm((prev) => ({ ...prev, workingHours: nextValue }));
    };

    const loadWorkingHoursFromJson = () => {
        const parsed = parseOptionalJson(branchForm.workingHours, "working_hours");
        if (parsed.error) {
            reportValidationError(parsed.error);
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
            if (!Number.isInteger(parsed)) {
                return { error: "default_duration_min: укажите целое число" };
            }
            if (parsed < 5 || parsed > 480) {
                return { error: "default_duration_min: допустимо от 5 до 480" };
            }
            payload.default_duration_min = parsed;
        }
        if (bufferMinRaw) {
            const parsed = Number(bufferMinRaw);
            if (!Number.isInteger(parsed)) {
                return { error: "buffer_min: укажите целое число" };
            }
            if (parsed < 0 || parsed > 240) {
                return { error: "buffer_min: допустимо от 0 до 240" };
            }
            payload.buffer_min = parsed;
        }
        return { value: payload };
    };

    const applyBookingSettingsToJson = () => {
        const built = buildBookingSettingsPayload();
        if (built.error) {
            reportValidationError(built.error);
            return;
        }
        const nextValue = built.value ? JSON.stringify(built.value, null, 2) : "";
        setBranchForm((prev) => ({ ...prev, bookingSettings: nextValue }));
    };

    const loadBookingSettingsFromJson = () => {
        const parsed = parseOptionalJson(branchForm.bookingSettings, "booking_settings");
        if (parsed.error) {
            reportValidationError(parsed.error);
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

    const validatePurchasedPayload = (payload: CapabilitiesPayload): string | null => {
        if (payload.domain_slug && !DOMAIN_SLUG_RE.test(payload.domain_slug)) {
            return "purchased.domain_slug: допустимы a-z, 0-9, _";
        }
        if (
            payload.features.booking_mode === "confirm_slots"
            && (!payload.providers.availability_provider || payload.providers.availability_provider === "none")
        ) {
            return "purchased.providers.availability_provider обязателен при booking_mode=confirm_slots";
        }
        if (!hasPurchasedSignal(payload)) {
            return "Добавьте минимум один purchased capability или domain_slug";
        }
        return null;
    };

    const buildPurchasedPayload = (): { value?: CapabilitiesPayload; error?: string } => {
        const normalized = normalizeCapabilities(purchasedCapabilitiesDraft);
        normalized.domain_slug = normalized.domain_slug?.trim() || null;
        const validationError = validatePurchasedPayload(normalized);
        if (validationError) {
            return { error: validationError };
        }
        return { value: normalized };
    };

    const applyPurchasedToJson = () => {
        const built = buildPurchasedPayload();
        if (built.error) {
            reportValidationError(built.error);
            return;
        }
        setPurchasedJsonDraft(built.value ? JSON.stringify(built.value, null, 2) : "{}");
        setPurchasedJsonDirty(false);
    };

    const loadPurchasedFromJson = () => {
        const parsed = parseOptionalJson(purchasedJsonDraft, "purchased");
        if (parsed.error) {
            reportValidationError(parsed.error);
            return;
        }
        const normalized = normalizeCapabilities((parsed.value as CapabilitiesPayload | undefined) ?? null);
        const validationError = validatePurchasedPayload(normalized);
        if (validationError) {
            reportValidationError(validationError);
            return;
        }
        setOnboardingContractTouched(true);
        setPurchasedCapabilitiesDraft(normalized);
        setPurchasedJsonDirty(false);
    };

    const {
        data: onboardingBlueprintsData,
        error: onboardingBlueprintsError,
    } = useQuery({
        queryKey: ["admin-onboarding-blueprints"],
        queryFn: async () => {
            const response = await adminApi.listOnboardingBlueprints();
            return response.data as OnboardingBlueprintListResponse;
        },
        enabled: !!session,
    });

    const domainTemplatePresets = useMemo<DomainTemplatePreset[]>(() => {
        const items = onboardingBlueprintsData?.items ?? [];
        if (items.length > 0) {
            return items.map((item) => ({
                id: item.id,
                label: item.label,
                summary: item.summary,
                payload: normalizeCapabilities(item.payload),
            }));
        }
        return FALLBACK_DOMAIN_TEMPLATE_PRESETS.map((item) => ({
            id: item.id,
            label: item.label,
            summary: item.summary,
            payload: normalizeCapabilities(item.payload),
        }));
    }, [onboardingBlueprintsData]);

    useEffect(() => {
        if (!domainTemplatePresets.length) {
            return;
        }
        if (domainTemplatePresets.some((template) => template.id === selectedDomainTemplate)) {
            return;
        }
        setSelectedDomainTemplate(domainTemplatePresets[0].id);
    }, [domainTemplatePresets, selectedDomainTemplate]);

    const handleApplyDomainTemplate = () => {
        const selected = domainTemplatePresets.find((template) => template.id === selectedDomainTemplate);
        if (!selected) {
            reportValidationError("Выберите валидный template");
            return;
        }
        const normalized = normalizeCapabilities(selected.payload);
        const validationError = validatePurchasedPayload(normalized);
        if (validationError) {
            reportValidationError(validationError);
            return;
        }
        setOnboardingContractTouched(true);
        setOnboardingContractDraft((prev) => ({
            ...normalizeOnboardingContractPayload(prev),
            domain_slug: normalized.domain_slug,
        }));
        setPurchasedCapabilitiesDraft(normalized);
        setPurchasedJsonDraft(JSON.stringify(normalized, null, 2));
        setPurchasedJsonDirty(false);
        toast.success(`Template применён: ${selected.label}`);
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

    const { data: onboardingScorecard, refetch: refetchOnboardingScorecard } = useQuery({
        queryKey: ["onboarding-scorecard", branchData?.id],
        queryFn: async () => {
            if (!branchData?.id) {
                return null;
            }
            const response = await onboardingApi.scorecard(branchData.id);
            return response.data as OnboardingScorecard;
        },
        enabled: !!session && !!branchData?.id,
    });

    useEffect(() => {
        if (capabilitiesError) {
            reportError(capabilitiesError);
        }
    }, [capabilitiesError, reportError]);

    useEffect(() => {
        if (onboardingContractError) {
            reportError(onboardingContractError);
        }
    }, [onboardingContractError, reportError]);

    useEffect(() => {
        if (referencePackError) {
            reportError(referencePackError);
        }
    }, [referencePackError, reportError]);

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
        const normalizedPurchased = normalizeCapabilities(normalized.purchased);
        setOnboardingContractDraft(normalized);
        setPurchasedCapabilitiesDraft(normalizedPurchased);
        setPurchasedJsonDraft(JSON.stringify(normalizedPurchased, null, 2));
        setPurchasedJsonDirty(false);
        setPaymentStatusDraft(onboardingContractData.payment_status ?? "pending");
    }, [onboardingContractData, onboardingContractTouched]);

    useEffect(() => {
        if (purchasedJsonDirty) {
            return;
        }
        const normalized = normalizeCapabilities(purchasedCapabilitiesDraft);
        setPurchasedJsonDraft(JSON.stringify(normalized, null, 2));
    }, [purchasedCapabilitiesDraft, purchasedJsonDirty]);

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
            reportError(error);
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
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success(
                bootstrapAgents.length > 0
                    ? `Филиал создан, добавлено аккаунтов: ${bootstrapAgents.length}`
                    : "Филиал создан"
            );
        },
        onError: (error) => {
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success("Филиал обновлён");
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                reportValidationError("Сначала создайте филиал");
                return;
            }
            reportError(error);
        },
    });

    const approveGoLiveMutation = useMutation({
        mutationFn: async (payload: BranchGoLiveDecisionRequest) => {
            if (!branchData?.id) {
                throw new Error("BRANCH_REQUIRED");
            }
            const response = await adminApi.approveBranchGoLive(branchData.id, payload);
            return response.data;
        },
        onSuccess: (data) => {
            setBranchData(data as ProvisioningBranch);
            refetchOnboarding();
            refetchOnboardingScorecard();
            toast.success("Go-live одобрен");
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                reportValidationError("Сначала создайте филиал");
                return;
            }
            reportError(error);
        },
    });

    const rejectGoLiveMutation = useMutation({
        mutationFn: async (payload: BranchGoLiveDecisionRequest) => {
            if (!branchData?.id) {
                throw new Error("BRANCH_REQUIRED");
            }
            const response = await adminApi.rejectBranchGoLive(branchData.id, payload);
            return response.data;
        },
        onSuccess: (data) => {
            setBranchData(data as ProvisioningBranch);
            refetchOnboarding();
            refetchOnboardingScorecard();
            toast.success("Go-live отклонен");
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                reportValidationError("Сначала создайте филиал");
                return;
            }
            reportError(error);
        },
    });

    const waiveGoLiveMutation = useMutation({
        mutationFn: async (payload: BranchGoLiveWaiverRequest) => {
            if (!branchData?.id) {
                throw new Error("BRANCH_REQUIRED");
            }
            const response = await adminApi.waiveBranchGoLive(branchData.id, payload);
            return response.data;
        },
        onSuccess: (data) => {
            setBranchData(data as ProvisioningBranch);
            refetchOnboarding();
            refetchOnboardingScorecard();
            toast.success("Go-live waiver сохранен");
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                reportValidationError("Сначала создайте филиал");
                return;
            }
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success("Пользователь добавлен");
        },
        onError: (error) => {
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success("Capabilities сохранены");
        },
        onError: (error) => {
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success("Onboarding contract сохранён");
        },
        onError: (error) => {
            reportError(error);
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
            refetchOnboardingScorecard();
            toast.success("Reference pack обновлён");
        },
        onError: (error) => {
            reportError(error);
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
                const normalizedContract = normalizeOnboardingContractPayload(data.onboarding_contract.payload);
                const normalizedPurchased = normalizeCapabilities(normalizedContract.purchased);
                setOnboardingContractDraft(normalizedContract);
                setPurchasedCapabilitiesDraft(normalizedPurchased);
                setOnboardingContractTouched(false);
                setPurchasedJsonDraft(JSON.stringify(normalizedPurchased, null, 2));
                setPurchasedJsonDirty(false);
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
            queryClient.invalidateQueries({ queryKey: ["onboarding-scorecard"] });
            queryClient.invalidateQueries({ queryKey: ["admin-capabilities"] });
            queryClient.invalidateQueries({ queryKey: ["admin-onboarding-contract"] });
            refetchCapabilities();
            refetchOnboardingContract();
            refetchReferencePacks();
            refetchOnboarding();
            refetchOnboardingScorecard();
            toast.success("Авто-онбординг выполнен");
        },
        onError: (error) => {
            reportError(error);
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
            reportError(error);
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
            refetchOnboardingScorecard();
        },
        onError: (error) => {
            if (error instanceof Error && error.message === "BRANCH_REQUIRED") {
                reportValidationError("Сначала создайте филиал");
                return;
            }
            reportError(error);
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
    const onboardingTimeline = useMemo(() => {
        return WIZARD_STEPS.map((step, index) => {
            const stepState = stepStateById[step.id];
            const status = stepState?.status
                ?? (stepStatus[step.id] ? "complete" : "locked");
            return {
                id: step.id,
                index: index + 1,
                label: step.label,
                hint: step.hint,
                status,
                required: stepState?.required ?? true,
                missing: stepState?.missing ?? [],
            };
        });
    }, [stepStateById, stepStatus]);

    const capabilitiesPreview = useMemo(() => {
        const clientPayload = capabilitiesData?.client_capabilities?.payload ?? null;
        return mergeCapabilities(clientPayload, capabilitiesDraft);
    }, [capabilitiesData, capabilitiesDraft]);

    const canManagePayment = role === "platform_admin";
    const canManageReferencePacks = role === "platform_admin";
    const hasOnboardingContractRecord = !!onboardingContractData?.client_contract || !!onboardingContractData?.branch_contract;
    const paymentStatusEffective = onboardingContractData?.payment_status ?? "pending";
    const capabilityMismatches = useMemo(
        () => onboardingContractData?.capability_mismatches ?? [],
        [onboardingContractData?.capability_mismatches],
    );
    const referencePacks = referencePackData?.items ?? [];
    const hasActiveReferencePack = referencePacks.some((item) => item.status === "active");

    const effectiveCapabilities = capabilitiesData?.effective ?? null;
    const hasWorkingHours = isNonEmptyRecord(branchData?.working_hours);
    const hasBookingSettings = isNonEmptyRecord(branchData?.booking_settings);
    const bookingEnabled = capabilitiesPreview.features?.booking_mode != null;
    const knowledgeUploadEnabled = capabilitiesPreview.features?.knowledge_upload === true;
    const onboardingScorecardEnterprise = onboardingScorecard as OnboardingScorecardEnterprise | undefined;
    const documentIngestionGate: OnboardingDocumentIngestion | null = onboardingScorecard?.document_ingestion ?? null;
    const onboardingSlaControlLoop: OnboardingSlaControlLoop | null = onboardingScorecardEnterprise?.sla_control_loop ?? null;
    const onboardingOperationalPipeline: OnboardingOperationalPipeline | null = onboardingScorecardEnterprise?.operational_pipeline ?? null;

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
                required: knowledgeUploadEnabled,
                ok: !!branchData?.knowledge_tag,
            },
            {
                id: "document_ingestion",
                label: "Document ingestion gate",
                required: knowledgeUploadEnabled,
                ok: knowledgeUploadEnabled ? Boolean(documentIngestionGate?.valid) : true,
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
        knowledgeUploadEnabled,
        documentIngestionGate?.valid,
        hasOnboardingContractRecord,
        paymentStatusEffective,
        referencePackDomainSlug,
        hasActiveReferencePack,
        hasBookingSettings,
        hasWorkingHours,
        specialistsConfirmed,
    ]);

    const missingRequirements = readinessItems.filter((item) => item.required && !item.ok);
    const scorecardStatus = onboardingScorecard?.status ?? null;
    const scorecardFailed = scorecardStatus === "fail";
    const scorecardMissing = useMemo(
        () => onboardingScorecard?.missing ?? [],
        [onboardingScorecard?.missing],
    );
    const scorecardFailedChecks = useMemo(
        () => (
            onboardingScorecard?.checks?.filter(
                (check: OnboardingScorecardCheck) => check.required && !check.passed,
            ) ?? []
        ),
        [onboardingScorecard?.checks],
    );
    const documentIngestionMissing = useMemo(
        () => documentIngestionGate?.missing_fields ?? [],
        [documentIngestionGate?.missing_fields],
    );
    const documentIngestionCriticalMissing = useMemo(
        () => documentIngestionGate?.critical_missing_fields ?? [],
        [documentIngestionGate?.critical_missing_fields],
    );
    const onboardingSlaIncidents = useMemo(
        () => onboardingSlaControlLoop?.active_incidents ?? [],
        [onboardingSlaControlLoop?.active_incidents],
    );
    const onboardingSlaActions = useMemo(
        () => onboardingSlaControlLoop?.recommended_actions ?? [],
        [onboardingSlaControlLoop?.recommended_actions],
    );
    const operationalPipelineStages = useMemo(
        () => onboardingOperationalPipeline?.stages ?? [],
        [onboardingOperationalPipeline?.stages],
    );
    const operationalPipelineBlockers = useMemo(
        () => onboardingOperationalPipeline?.blockers ?? [],
        [onboardingOperationalPipeline?.blockers],
    );
    const operationalPipelineActions = useMemo(
        () => onboardingOperationalPipeline?.next_actions ?? [],
        [onboardingOperationalPipeline?.next_actions],
    );
    const goNoGoMissing = useMemo(
        () => (scorecardMissing.length > 0 ? scorecardMissing : (stepStateById.go_no_go?.missing ?? [])),
        [scorecardMissing, stepStateById.go_no_go?.missing],
    );
    const goNoGoReady = missingRequirements.length === 0 && goNoGoMissing.length === 0 && !scorecardFailed;
    const requiredReadinessItems = readinessItems.filter((item) => item.required);
    const readinessCompletedCount = requiredReadinessItems.filter((item) => item.ok).length;
    const readinessScore = requiredReadinessItems.length > 0
        ? Math.round((readinessCompletedCount / requiredReadinessItems.length) * 100)
        : 100;
    const readinessLevel: "high" | "medium" | "low" = readinessScore >= 85
        ? "high"
        : readinessScore >= 60
            ? "medium"
            : "low";
    const readinessStatusLabel = readinessLevel === "high"
        ? "Готово к Go/No-Go"
        : readinessLevel === "medium"
            ? "Есть блокеры"
            : "Критические блокеры";
    const readinessToneClass = readinessLevel === "high"
        ? "border-green-200 bg-green-50 text-green-800"
        : readinessLevel === "medium"
            ? "border-amber-200 bg-amber-50 text-amber-800"
            : "border-destructive/30 bg-destructive/10 text-destructive";
    const readinessBlockers = useMemo(() => {
        const blockers: string[] = [];
        missingRequirements.forEach((item) => blockers.push(item.label));
        goNoGoMissing.forEach((item) => blockers.push(formatMissingRequirement(item)));
        scorecardFailedChecks.forEach((check) => blockers.push(`Scorecard step: ${check.id}`));
        capabilityMismatches.forEach((item) => blockers.push(`Договор: ${CAPABILITY_FIELD_LABELS[item] ?? item}`));
        operationalPipelineBlockers.forEach((item) => blockers.push(formatOperationalBlocker(item)));
        onboardingSlaIncidents.forEach((item) => blockers.push(formatSlaIncident(item)));
        return Array.from(new Set(blockers));
    }, [
        missingRequirements,
        goNoGoMissing,
        scorecardFailedChecks,
        capabilityMismatches,
        operationalPipelineBlockers,
        onboardingSlaIncidents,
    ]);
    const branchGoLiveStateRaw = (branchData as Record<string, unknown> | null)?.go_live_state;
    const branchGoLiveState: "pending" | "approved" | "rejected" = (
        branchGoLiveStateRaw === "pending" || branchGoLiveStateRaw === "approved" || branchGoLiveStateRaw === "rejected"
    )
        ? branchGoLiveStateRaw
        : "pending";
    const branchGoLiveReasonRaw = (branchData as Record<string, unknown> | null)?.go_live_reason;
    const branchGoLiveReason = typeof branchGoLiveReasonRaw === "string" && branchGoLiveReasonRaw.trim().length > 0
        ? branchGoLiveReasonRaw
        : null;
    const branchGoLiveAllowed = Boolean((branchData as Record<string, unknown> | null)?.go_live_allowed);
    const branchGoLiveWaiverActive = Boolean((branchData as Record<string, unknown> | null)?.go_live_waiver_active);
    const branchGoLiveWaiverUntilRaw = (branchData as Record<string, unknown> | null)?.go_live_waiver_until;
    const branchGoLiveWaiverUntil = typeof branchGoLiveWaiverUntilRaw === "string" && branchGoLiveWaiverUntilRaw.length > 0
        ? branchGoLiveWaiverUntilRaw
        : null;
    const autopilotPhone = autopilotForm.phone.trim();
    const autopilotInstanceId = autopilotForm.instanceId.trim();
    const autopilotCompanyRef = companyId.trim() || autopilotForm.companyName.trim();
    const autopilotClientRef = clientId.trim() || autopilotForm.clientSlug.trim();
    const autopilotNeedsBranchName = !branchData?.id;
    const autopilotBranchName = autopilotForm.branchName.trim();
    const autopilotClientDataText = autopilotForm.clientDataText.trim();
    const autopilotProviderBindingProvider = autopilotForm.providerBindingProvider.trim();
    const autopilotProviderBindingPaidUntil = autopilotForm.providerBindingPaidUntil.trim();
    const autopilotProviderBindingOwner = autopilotForm.providerBindingOwner.trim();
    const autopilotProviderBindingNextRenewalAt = autopilotForm.providerBindingNextRenewalAt.trim();
    const autopilotProviderBindingLastRebindAt = autopilotForm.providerBindingLastRebindAt.trim();
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
    if (autopilotServices.includes("whatsapp")) {
        if (!autopilotProviderBindingProvider) {
            autopilotMissingInputs.push("provider_binding.provider");
        }
        if (!autopilotForm.providerBindingWebhookStatus) {
            autopilotMissingInputs.push("provider_binding.webhook_status");
        }
        if (!autopilotProviderBindingOwner) {
            autopilotMissingInputs.push("provider_binding.owner");
        }
        if (!autopilotProviderBindingPaidUntil && !autopilotProviderBindingNextRenewalAt) {
            autopilotMissingInputs.push("provider_binding.next_renewal_at | paid_until");
        }
    }
    const autopilotBlockedByScorecard = Boolean(branchData?.id && scorecardFailed);
    const canRunAutopilot = (
        canEdit
        && !runAutopilotMutation.isPending
        && autopilotMissingInputs.length === 0
        && !autopilotBlockedByScorecard
    );

    const handleToggleAutopilotService = (serviceId: OnboardingPurchasedService) => {
        setAutopilotServices((prev) => (
            prev.includes(serviceId)
                ? prev.filter((item) => item !== serviceId)
                : [...prev, serviceId]
        ));
    };

    const handleApproveGoLive = () => {
        const reason = goLiveDecisionReason.trim();
        if (!branchData?.id) {
            reportValidationError("Сначала создайте филиал");
            return;
        }
        if (scorecardFailed) {
            const missing = goNoGoMissing.map((item) => formatMissingRequirement(item));
            reportValidationError(`Go-live заблокирован scorecard: ${missing.join(", ") || "есть незавершенные проверки"}`);
            return;
        }
        if (!reason) {
            reportValidationError("Укажите reason для approve");
            return;
        }
        approveGoLiveMutation.mutate(
            { reason },
            {
                onSuccess: () => {
                    setGoLiveDecisionReason("");
                },
            },
        );
    };

    const handleRejectGoLive = () => {
        const reason = goLiveDecisionReason.trim();
        if (!branchData?.id) {
            reportValidationError("Сначала создайте филиал");
            return;
        }
        if (!reason) {
            reportValidationError("Укажите reason для reject");
            return;
        }
        rejectGoLiveMutation.mutate(
            { reason },
            {
                onSuccess: () => {
                    setGoLiveDecisionReason("");
                },
            },
        );
    };

    const handleWaiveGoLive = () => {
        const reason = goLiveDecisionReason.trim();
        const ttlHours = Number.parseInt(goLiveWaiverHours, 10);
        if (!branchData?.id) {
            reportValidationError("Сначала создайте филиал");
            return;
        }
        if (scorecardFailed) {
            const missing = goNoGoMissing.map((item) => formatMissingRequirement(item));
            reportValidationError(`Go-live заблокирован scorecard: ${missing.join(", ") || "есть незавершенные проверки"}`);
            return;
        }
        if (!reason) {
            reportValidationError("Укажите reason для waiver");
            return;
        }
        if (!Number.isFinite(ttlHours) || ttlHours <= 0) {
            reportValidationError("ttl_hours должен быть положительным числом");
            return;
        }
        waiveGoLiveMutation.mutate(
            { reason, ttl_hours: ttlHours },
            {
                onSuccess: () => {
                    setGoLiveDecisionReason("");
                },
            },
        );
    };

    const handleRunAutopilot = () => {
        if (autopilotMissingInputs.length > 0) {
            reportValidationError(`Не хватает данных: ${autopilotMissingInputs.join(", ")}`);
            return;
        }
        if (autopilotBlockedByScorecard) {
            const missing = goNoGoMissing.map((item) => formatMissingRequirement(item));
            reportValidationError(`Автопроцесс заблокирован scorecard: ${missing.join(", ") || "есть незавершенные проверки"}`);
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
            provider_binding: autopilotServices.includes("whatsapp")
                ? {
                    whatsapp: {
                        provider: autopilotProviderBindingProvider || null,
                        instance_id: autopilotInstanceId,
                        webhook_status: autopilotForm.providerBindingWebhookStatus || null,
                        paid_until: autopilotProviderBindingPaidUntil || null,
                        owner: autopilotProviderBindingOwner || null,
                        next_renewal_at: autopilotProviderBindingNextRenewalAt || null,
                        last_rebind_at: autopilotProviderBindingLastRebindAt || null,
                        rebind_required: autopilotForm.providerBindingRebindRequired,
                        alert_state: autopilotForm.providerBindingAlertState || null,
                        notes: autopilotForm.providerBindingNotes.trim() || null,
                    },
                }
                : undefined,
            client_data_text: autopilotClientDataText || undefined,
            activate_branch: false,
            auto_create_reference_pack: true,
            auto_publish_knowledge: false,
        };
        runAutopilotMutation.mutate(payload);
    };

    const handleCreateCompany = () => {
        const name = companyName.trim();
        if (!name) {
            reportValidationError("Укажите название компании");
            return;
        }
        const builtBilling = buildBillingInfoPayload();
        if (builtBilling.error) {
            reportValidationError(builtBilling.error);
            return;
        }
        const billing = parseOptionalJson(billingInfo, "billing_info");
        if (billing.error) {
            reportValidationError(billing.error);
            return;
        }
        let billingPayload = billing.value;
        if (!billingPayload) {
            billingPayload = builtBilling.value;
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
            reportValidationError("Укажите slug клиента");
            return;
        }
        if (!companyId.trim()) {
            reportValidationError("Укажите company_id компании");
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
            reportValidationError("Укажите client_id");
            return;
        }
        const name = branchForm.name.trim();
        const slug = branchForm.slug.trim();
        if (!name || !slug) {
            reportValidationError("Заполните название и slug");
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
            reportValidationError("Сначала создайте филиал");
            return;
        }
        const name = branchForm.name.trim();
        const slug = branchForm.slug.trim();
        if (!name || !slug) {
            reportValidationError("Заполните название и slug");
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
            reportValidationError("Сначала создайте филиал");
            return;
        }
        const instanceId = branchForm.instanceId.trim();
        if (!instanceId) {
            reportValidationError("Укажите instance_id");
            return;
        }
        const phone = branchForm.phone.trim();
        if (!phone) {
            reportValidationError("Укажите phone филиала");
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
            reportValidationError("Сначала создайте филиал");
            return;
        }
        const chatId = branchForm.telegramChatId.trim();
        if (!chatId) {
            reportValidationError("Укажите telegram_chat_id");
            return;
        }
        patchBranchMutation.mutate({
            telegram_chat_id: chatId,
        });
    };

    const handleSaveKnowledge = () => {
        if (!branchData?.id) {
            reportValidationError("Сначала создайте филиал");
            return;
        }
        const tag = branchForm.knowledgeTag.trim();
        if (!tag) {
            reportValidationError("Укажите knowledge_tag");
            return;
        }
        patchBranchMutation.mutate({
            knowledge_tag: tag,
        });
    };

    const handleSaveBooking = () => {
        if (!branchData?.id) {
            reportValidationError("Сначала создайте филиал");
            return;
        }
        const workingHours = parseOptionalJson(branchForm.workingHours, "working_hours");
        if (workingHours.error) {
            reportValidationError(workingHours.error);
            return;
        }
        const bookingSettings = parseOptionalJson(branchForm.bookingSettings, "booking_settings");
        if (bookingSettings.error) {
            reportValidationError(bookingSettings.error);
            return;
        }
        let workingPayload = workingHours.value;
        let bookingPayload = bookingSettings.value;
        let nextWorkingJson: string | null = null;
        let nextBookingJson: string | null = null;
        if (!workingPayload) {
            const built = buildWorkingHoursPayload();
            if (built.error) {
                reportValidationError(built.error);
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
                reportValidationError(built.error);
                return;
            }
            bookingPayload = built.value;
            if (built.value) {
                nextBookingJson = JSON.stringify(built.value, null, 2);
            }
        }
        if (!workingPayload && !bookingPayload) {
            reportValidationError("Заполните working_hours или booking_settings");
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
            reportValidationError("Укажите client_id");
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
                reportValidationError("branch_id обязателен для manager");
                return;
            }
            payload.branch_id = branchId;
        }
        createAgentMutation.mutate(payload);
    };

    const handleSaveCapabilities = () => {
        if (!branchData?.id || !clientId) {
            reportValidationError("Нужны client_id и branch_id");
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
            reportValidationError("Нужны client_id и branch_id");
            return;
        }
        const builtPurchased = buildPurchasedPayload();
        if (builtPurchased.error || !builtPurchased.value) {
            reportValidationError(builtPurchased.error ?? "purchased: добавьте данные");
            return;
        }
        let purchasedPayload = builtPurchased.value;
        if (purchasedJsonDirty) {
            const parsedPurchased = parseOptionalJson(purchasedJsonDraft, "purchased");
            if (parsedPurchased.error) {
                reportValidationError(parsedPurchased.error);
                return;
            }
            if (parsedPurchased.value) {
                const normalizedFromJson = normalizeCapabilities(parsedPurchased.value as CapabilitiesPayload);
                const validationError = validatePurchasedPayload(normalizedFromJson);
                if (validationError) {
                    reportValidationError(validationError);
                    return;
                }
                purchasedPayload = normalizedFromJson;
                setPurchasedCapabilitiesDraft(normalizedFromJson);
            } else {
                setPurchasedJsonDraft(JSON.stringify(purchasedPayload, null, 2));
            }
            setPurchasedJsonDirty(false);
        } else {
            setPurchasedJsonDraft(JSON.stringify(purchasedPayload, null, 2));
        }
        const providerBindingWhatsApp = onboardingContractDraft.provider_binding?.whatsapp;
        const payload: OnboardingContractPayload = {
            domain_slug: onboardingContractDraft.domain_slug?.trim() || null,
            purchased: purchasedPayload,
            provider_binding: {
                whatsapp: {
                    provider: providerBindingWhatsApp?.provider?.trim() || null,
                    instance_id: providerBindingWhatsApp?.instance_id?.trim() || null,
                    webhook_status: providerBindingWhatsApp?.webhook_status ?? null,
                    paid_until: providerBindingWhatsApp?.paid_until?.trim() || null,
                    owner: providerBindingWhatsApp?.owner?.trim() || null,
                    next_renewal_at: providerBindingWhatsApp?.next_renewal_at?.trim() || null,
                    last_rebind_at: providerBindingWhatsApp?.last_rebind_at?.trim() || null,
                    rebind_required: providerBindingWhatsApp?.rebind_required ?? null,
                    alert_state: providerBindingWhatsApp?.alert_state ?? null,
                    notes: providerBindingWhatsApp?.notes?.trim() || null,
                },
            },
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
            reportValidationError("Только platform_admin может управлять reference packs");
            return;
        }
        const domainSlug = referencePackDomainSlug.trim();
        if (!domainSlug) {
            reportValidationError("Укажите domain_slug");
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
        setPurchasedCapabilitiesDraft(normalizeCapabilities());
        setPurchasedJsonDraft("{}");
        setPurchasedJsonDirty(false);
        setSelectedDomainTemplate("beauty");
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
            providerBindingProvider: "chatflow",
            providerBindingWebhookStatus: "pending",
            providerBindingPaidUntil: "",
            providerBindingOwner: "",
            providerBindingNextRenewalAt: "",
            providerBindingLastRebindAt: "",
            providerBindingRebindRequired: false,
            providerBindingAlertState: "warn",
            providerBindingNotes: "",
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
    const workspaceScope = useMemo(() => ({
        companyId: companyId.trim(),
        clientId: clientId.trim(),
        branchId: branchData?.id?.trim() ?? "",
    }), [branchData?.id, clientId, companyId]);
    const workspaceScopeReady = Boolean(
        workspaceScope.companyId && workspaceScope.clientId && workspaceScope.branchId,
    );

    const openExecutionHub = () => {
        writeConsoleContextScopeToStorage(workspaceScope);
        if (!workspaceScopeReady) {
            toast("Открою Workspace: завершите выбор company/client/branch в контексте.");
        }
        router.push("/company-workspace");
    };

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

            {inlineErrors.length > 0 && (
                <section className="mt-6 rounded-xl border border-red-300/60 bg-red-50 p-4" data-testid="provisioning-error-summary">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-red-900">Ошибки последних операций</h3>
                        <button type="button" className="btn-ghost" onClick={clearErrors}>
                            Очистить
                        </button>
                    </div>
                    <div className="mt-2 space-y-2">
                        {inlineErrors.map((error) => (
                            <div key={error.id} className="rounded-lg border border-red-200/80 bg-background/90 p-3 text-xs">
                                <div className="font-mono text-red-900">{error.code}</div>
                                <div className="mt-1 text-foreground">{error.message}</div>
                                <div className="mt-1 text-muted-foreground">
                                    {new Date(error.capturedAt).toLocaleString("ru-RU")}
                                    {error.traceId ? ` · trace: ${error.traceId}` : ""}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
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

            <div className="mt-4 rounded-xl border border-blue-300/60 bg-blue-50 p-4" data-testid="onboarding-execution-hub">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-900">
                            Execution Hub
                        </div>
                        <div className="mt-1 text-sm text-blue-900">
                            Рабочий поток выполнения: используйте Company Workspace для remediation/go-live.
                        </div>
                        <div className="mt-1 text-xs text-blue-900/80">
                            scope: company={workspaceScope.companyId || "—"} · client={workspaceScope.clientId || "—"} · branch={workspaceScope.branchId || "—"}
                        </div>
                    </div>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={openExecutionHub}
                        data-testid="onboarding-open-workspace"
                    >
                        Продолжить в Workspace
                    </button>
                </div>
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
                    {branchData?.id && (
                        <div className="mt-1 text-xs text-muted-foreground">
                            Server scorecard: {scorecardStatus ?? "—"}
                            {scorecardFailed && goNoGoMissing.length > 0
                                ? ` (${goNoGoMissing.map((item) => formatMissingRequirement(item)).join(", ")})`
                                : ""}
                        </div>
                    )}
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

                <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3">
                    <div className="text-xs text-muted-foreground">
                        Provider binding (WhatsApp contract для autopilot).
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <input
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="provider (chatflow)"
                            value={autopilotForm.providerBindingProvider}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingProvider: event.target.value,
                            }))}
                            disabled={!canEdit}
                        />
                        <select
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={autopilotForm.providerBindingWebhookStatus}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingWebhookStatus: event.target.value as "configured" | "pending" | "rebind_required",
                            }))}
                            disabled={!canEdit}
                        >
                            <option value="configured">webhook: configured</option>
                            <option value="pending">webhook: pending</option>
                            <option value="rebind_required">webhook: rebind_required</option>
                        </select>
                        <input
                            type="date"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={autopilotForm.providerBindingPaidUntil}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingPaidUntil: event.target.value,
                            }))}
                            disabled={!canEdit}
                        />
                        <input
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="owner (Platform admin)"
                            value={autopilotForm.providerBindingOwner}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingOwner: event.target.value,
                            }))}
                            disabled={!canEdit}
                        />
                        <input
                            type="date"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={autopilotForm.providerBindingNextRenewalAt}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingNextRenewalAt: event.target.value,
                            }))}
                            disabled={!canEdit}
                        />
                        <input
                            type="date"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={autopilotForm.providerBindingLastRebindAt}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingLastRebindAt: event.target.value,
                            }))}
                            disabled={!canEdit}
                        />
                        <select
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={autopilotForm.providerBindingAlertState}
                            onChange={(event) => setAutopilotForm((prev) => ({
                                ...prev,
                                providerBindingAlertState: event.target.value as "ok" | "warn" | "critical",
                            }))}
                            disabled={!canEdit}
                        >
                            <option value="ok">alert: ok</option>
                            <option value="warn">alert: warn</option>
                            <option value="critical">alert: critical</option>
                        </select>
                        <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                            <input
                                type="checkbox"
                                checked={autopilotForm.providerBindingRebindRequired}
                                onChange={(event) => setAutopilotForm((prev) => ({
                                    ...prev,
                                    providerBindingRebindRequired: event.target.checked,
                                }))}
                                disabled={!canEdit}
                            />
                            rebind_required
                        </label>
                    </div>
                    <textarea
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                        rows={2}
                        placeholder="provider binding notes"
                        value={autopilotForm.providerBindingNotes}
                        onChange={(event) => setAutopilotForm((prev) => ({
                            ...prev,
                            providerBindingNotes: event.target.value,
                        }))}
                        disabled={!canEdit}
                    />
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
                {autopilotBlockedByScorecard && (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                        Автопроцесс заблокирован: scorecard=fail.
                        {goNoGoMissing.length > 0
                            ? ` Missing: ${goNoGoMissing.map((item) => formatMissingRequirement(item)).join(", ")}`
                            : ""}
                    </div>
                )}

                {autopilotResult && (
                    <div className="rounded-lg border border-border/60 bg-background p-3 space-y-2 text-xs">
                        <div>
                            Компания: <span className="font-mono">{autopilotResult.company.id}</span> | Клиент:{" "}
                            <span className="font-mono">{autopilotResult.client.id}</span> | Филиал:{" "}
                            <span className="font-mono">{autopilotResult.branch.id}</span>
                        </div>
                        <div>
                            Не выполнены критерии Go/No-Go:{" "}
                            {autopilotResult.go_no_go_missing.length
                                ? autopilotResult.go_no_go_missing.map((item) => formatMissingRequirement(item)).join(", ")
                                : "нет"}
                        </div>
                        <div>
                            Webhook secret: <span className="font-mono">{autopilotResult.webhook_secret}</span>
                        </div>
                        <div className="break-all">
                            Webhook URL: <span className="font-mono">{autopilotResult.webhook_url}</span>
                        </div>
                        <div>
                            Не заполнены поля intake:{" "}
                            {autopilotResult.intake.missing_fields.length
                                ? autopilotResult.intake.missing_fields.map((item) => formatMissingRequirement(item)).join(", ")
                                : "нет"}
                        </div>
                        {autopilotResult.intake.missing_questions.length > 0 && (
                            <div>
                                Вопросы для дозаполнения: {autopilotResult.intake.missing_questions.join(" | ")}
                            </div>
                        )}
                        {(autopilotResult.intake.field_states?.length ?? 0) > 0 && (
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-2">
                                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Intake field states
                                </div>
                                <div className="mt-2 space-y-1">
                                    {(autopilotResult.intake.field_states ?? []).map((item: OnboardingIntakeFieldState) => (
                                        <div
                                            key={`${item.field}-${item.status}`}
                                            className="grid grid-cols-1 gap-1 rounded-md border border-border/60 bg-background px-2 py-2 md:grid-cols-[1fr_auto_auto]"
                                        >
                                            <div className="font-mono text-[11px]">
                                                {formatMissingRequirement(item.field)}
                                            </div>
                                            <div className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${intakeStatusClass(item.status)}`}>
                                                {intakeStatusLabel(item.status)}
                                            </div>
                                            <div className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${intakePriorityClass(item.priority)}`}>
                                                {intakePriorityLabel(item.priority)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {(autopilotResult.intake.question_queue?.length ?? 0) > 0 && (
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-2">
                                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Prioritized question queue
                                </div>
                                <div className="mt-2 space-y-1">
                                    {(autopilotResult.intake.question_queue ?? []).map((item: OnboardingIntakeQuestion, index: number) => (
                                        <div
                                            key={`${item.field}-${index}`}
                                            className="rounded-md border border-border/60 bg-background px-2 py-2"
                                        >
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="font-mono text-[11px]">{formatMissingRequirement(item.field)}</span>
                                                <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${intakePriorityClass(item.priority)}`}>
                                                    {intakePriorityLabel(item.priority)}
                                                </span>
                                                {item.blocking_go_live && (
                                                    <span className="inline-flex rounded bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive">
                                                        blocking go-live
                                                    </span>
                                                )}
                                            </div>
                                            <div className="mt-1 text-[11px] text-muted-foreground">{item.question}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {autopilotResult.intake.compile && (
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-2">
                                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Pack compile
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${qualityStatusClass(autopilotResult.intake.compile.status)}`}>
                                        {qualityStatusLabel(autopilotResult.intake.compile.status)}
                                    </span>
                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${autopilotResult.intake.compile.infra_valid ? "border-green-200 bg-green-50 text-green-800" : "border-destructive/30 bg-destructive/10 text-destructive"}`}>
                                        infra_valid={String(autopilotResult.intake.compile.infra_valid)}
                                    </span>
                                    {autopilotResult.intake.compile.schema_version && (
                                        <span className="font-mono text-[11px]">{autopilotResult.intake.compile.schema_version}</span>
                                    )}
                                </div>
                                <div className="mt-1 text-[11px] text-muted-foreground">
                                    hash: <span className="font-mono">{autopilotResult.intake.compile.hash ?? "n/a"}</span>
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                    pack_index_hash: <span className="font-mono">{autopilotResult.intake.compile.pack_index_hash ?? "n/a"}</span>
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                    signal_graph: <span className="font-mono">{String(autopilotResult.intake.compile.signal_graph_present)}</span>, policy_bundle:{" "}
                                    <span className="font-mono">{String(autopilotResult.intake.compile.policy_bundle_present)}</span>
                                </div>
                                {(autopilotResult.intake.compile.errors?.length ?? 0) > 0 && (
                                    <div className="mt-2 space-y-1">
                                        {(autopilotResult.intake.compile.errors ?? []).map((item: string, index: number) => (
                                            <div key={`${item}-${index}`} className="font-mono text-[11px] text-destructive">
                                                {item}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                        {autopilotResult.intake.quality_matrix && (
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-2">
                                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                    Quality matrix (P4+P5)
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${qualityStatusClass(autopilotResult.intake.quality_matrix.status)}`}>
                                        {qualityStatusLabel(autopilotResult.intake.quality_matrix.status)}
                                    </span>
                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${autopilotResult.intake.quality_matrix.infra_valid ? "border-green-200 bg-green-50 text-green-800" : "border-destructive/30 bg-destructive/10 text-destructive"}`}>
                                        infra_valid={String(autopilotResult.intake.quality_matrix.infra_valid)}
                                    </span>
                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${autopilotResult.intake.quality_matrix.semantic_valid ? "border-green-200 bg-green-50 text-green-800" : "border-destructive/30 bg-destructive/10 text-destructive"}`}>
                                        semantic_valid={String(autopilotResult.intake.quality_matrix.semantic_valid)}
                                    </span>
                                </div>
                                <div className="mt-1 text-[11px] text-muted-foreground">
                                    required={autopilotResult.intake.quality_matrix.required_fields_count}, missing={autopilotResult.intake.quality_matrix.missing_fields_count}, critical_missing={autopilotResult.intake.quality_matrix.critical_missing_fields_count}, integrity_missing={autopilotResult.intake.quality_matrix.integrity_missing_count}
                                </div>
                                {(autopilotResult.intake.quality_matrix.dimensions?.length ?? 0) > 0 && (
                                    <div className="mt-2 space-y-1">
                                        {(autopilotResult.intake.quality_matrix.dimensions ?? []).map((item: OnboardingIntakeQualityDimension) => (
                                            <div key={item.id} className="rounded-md border border-border/60 bg-background px-2 py-2">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <span className="font-mono text-[11px]">{item.id}</span>
                                                    <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-semibold ${qualityStatusClass(item.status)}`}>
                                                        {qualityStatusLabel(item.status)}
                                                    </span>
                                                    {!item.required && (
                                                        <span className="inline-flex rounded border border-border/60 bg-muted/40 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                                                            optional
                                                        </span>
                                                    )}
                                                </div>
                                                {(item.details?.length ?? 0) > 0 && (
                                                    <div className="mt-1 text-[11px] text-muted-foreground">
                                                        {item.details?.join(" | ")}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {(autopilotResult.intake.quality_matrix.regressions?.length ?? 0) > 0 && (
                                    <div className="mt-2 rounded border border-destructive/30 bg-destructive/10 px-2 py-1 text-[11px] text-destructive">
                                        regressions: {(autopilotResult.intake.quality_matrix.regressions ?? []).join(", ")}
                                    </div>
                                )}
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
                        Компания
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
                                    list="billing-contract-options"
                                    placeholder="B2B"
                                    maxLength={32}
                                    disabled={!canEdit}
                                    data-testid="onboarding-billing-contract"
                                />
                                <datalist id="billing-contract-options">
                                    <option value="B2B" />
                                    <option value="B2C" />
                                    <option value="Enterprise" />
                                    <option value="Partner" />
                                </datalist>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Валюта</label>
                                <input
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    value={billingCurrency}
                                    onChange={(event) => {
                                        const next = event.target.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
                                        setBillingCurrency(next);
                                    }}
                                    placeholder="KZT"
                                    maxLength={3}
                                    disabled={!canEdit}
                                    data-testid="onboarding-billing-currency"
                                />
                            </div>
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                            Ожидаемые форматы: `contract` = короткий тип договора, `currency` = ISO 4217 (например KZT/USD/EUR).
                        </p>
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
                        Клиент
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
                                    reportValidationError("Сначала создайте филиал");
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
                            Создайте owner/admin пользователей для доступа в Console. Для manager обязателен branch_id.
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
                                    {PROVISIONING_ASSIGNABLE_AGENT_ROLES.map((roleValue) => (
                                        <option key={roleValue} value={roleValue}>{roleValue}</option>
                                    ))}
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
                            <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3" data-testid="onboarding-working-hours-form">
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
                                <p className="text-[11px] text-muted-foreground">
                                    Формат времени: `HH:MM`, закрытие должно быть позже открытия.
                                </p>
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
                            <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3" data-testid="onboarding-booking-settings-form">
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
                                            placeholder="60 (5..480)"
                                            min={5}
                                            max={480}
                                            disabled={!canEdit}
                                            data-testid="onboarding-booking-default-duration"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">Буфер, мин</label>
                                        <input
                                            type="number"
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={bookingBufferMin}
                                            onChange={(event) => setBookingBufferMin(event.target.value)}
                                            placeholder="10 (0..240)"
                                            min={0}
                                            max={240}
                                            disabled={!canEdit}
                                            data-testid="onboarding-booking-buffer-min"
                                        />
                                    </div>
                                </div>
                                <p className="text-[11px] text-muted-foreground">
                                    `default_duration_min`: 5-480, `buffer_min`: 0-240, только целые числа.
                                </p>
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
                                    Проверки Go/No-Go
                                </h4>
                                <div className="rounded-lg border border-border/60 bg-background p-3 space-y-2" data-testid="onboarding-readiness-timeline">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                                            Readiness Timeline
                                        </div>
                                        <div className="text-[11px] text-muted-foreground">
                                            updated_at: {onboardingStatus?.updated_at ? new Date(onboardingStatus.updated_at).toLocaleString("ru-RU") : "—"}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {onboardingTimeline.map((item) => (
                                            <div
                                                key={item.id}
                                                className={`rounded-lg border px-3 py-2 text-xs ${onboardingStepStatusClass(item.status)}`}
                                            >
                                                <div className="flex flex-wrap items-center justify-between gap-2">
                                                    <div className="font-medium">
                                                        {item.index}. {item.label}
                                                    </div>
                                                    <div>{onboardingStepStatusLabel(item.status)}</div>
                                                </div>
                                                <div className="mt-1 text-[11px]">
                                                    hint: {item.hint} · required: {item.required ? "yes" : "no"}
                                                </div>
                                                {item.missing.length > 0 ? (
                                                    <div className="mt-1 text-[11px]">
                                                        missing: {item.missing.map((code) => formatMissingRequirement(code)).join(", ")}
                                                    </div>
                                                ) : null}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className={`rounded-lg border px-3 py-3 text-xs ${
                                    scorecardFailed
                                        ? "border-destructive/30 bg-destructive/10 text-destructive"
                                        : "border-green-200 bg-green-50 text-green-800"
                                }`} data-testid="onboarding-scorecard">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="font-semibold">Server Scorecard</span>
                                        <span className="font-mono">{scorecardStatus ?? "—"}</span>
                                    </div>
                                    <div className="mt-1">
                                        generated_at: {onboardingScorecard?.generated_at
                                            ? new Date(onboardingScorecard.generated_at).toLocaleString("ru-RU")
                                            : "—"}
                                    </div>
                                    {scorecardMissing.length > 0 && (
                                        <div className="mt-2">
                                            missing: {scorecardMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                                        </div>
                                    )}
                                    {scorecardFailedChecks.length > 0 && (
                                        <div className="mt-2">
                                            failed checks: {scorecardFailedChecks.map((item) => item.id).join(", ")}
                                        </div>
                                    )}
                                    {documentIngestionGate && (
                                        <div
                                            className={`mt-2 rounded-md border px-2 py-2 ${
                                                documentIngestionGate.status === "pass"
                                                    ? "border-green-200 bg-green-50 text-green-800"
                                                    : documentIngestionGate.status === "fail"
                                                        ? "border-destructive/30 bg-destructive/10 text-destructive"
                                                        : "border-border/60 bg-muted/40 text-muted-foreground"
                                            }`}
                                            data-testid="onboarding-document-ingestion"
                                        >
                                            <div className="font-semibold">
                                                Document ingestion: {documentIngestionGate.status}
                                            </div>
                                            <div className="mt-1 text-[11px]">
                                                source: <span className="font-mono">{documentIngestionGate.source}</span> · valid:{" "}
                                                <span className="font-mono">{documentIngestionGate.valid ? "true" : "false"}</span>
                                            </div>
                                            {documentIngestionMissing.length > 0 && (
                                                <div className="mt-1 text-[11px]">
                                                    missing_fields: {documentIngestionMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                                                </div>
                                            )}
                                            {documentIngestionCriticalMissing.length > 0 && (
                                                <div className="mt-1 text-[11px] font-semibold">
                                                    critical_missing: {documentIngestionCriticalMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {onboardingSlaControlLoop && (
                                    <div className={`rounded-lg border px-3 py-3 text-xs ${qualityStatusClass(onboardingSlaControlLoop.status)}`} data-testid="onboarding-sla-control-loop">
                                        <div className="flex items-center justify-between gap-3">
                                            <span className="font-semibold">SLA / Escalation Control Loop</span>
                                            <span className="font-mono">{qualityStatusLabel(onboardingSlaControlLoop.status)}</span>
                                        </div>
                                        <div className="mt-1">
                                            thresholds: r1={onboardingSlaControlLoop.reminder_1_minutes}m · r2={onboardingSlaControlLoop.reminder_2_minutes}m · escalation={onboardingSlaControlLoop.escalation_timeout_minutes}m
                                        </div>
                                        <div className="mt-1">
                                            queue: pending={onboardingSlaControlLoop.pending_total} · warning={onboardingSlaControlLoop.warning_total} · breached={onboardingSlaControlLoop.breached_total}
                                        </div>
                                        <div className="mt-1">
                                            provider: <span className="font-mono">{formatSlaProviderStatus(onboardingSlaControlLoop.provider_status)}</span>
                                            {" · "}alert_state: <span className="font-mono">{onboardingSlaControlLoop.provider_alert_state || "unknown"}</span>
                                            {onboardingSlaControlLoop.provider_paid_until ? (
                                                <>
                                                    {" · "}paid_until: <span className="font-mono">{onboardingSlaControlLoop.provider_paid_until}</span>
                                                </>
                                            ) : null}
                                            {typeof onboardingSlaControlLoop.provider_days_to_renewal === "number" ? (
                                                <>
                                                    {" · "}days_to_renewal: <span className="font-mono">{onboardingSlaControlLoop.provider_days_to_renewal}</span>
                                                </>
                                            ) : null}
                                        </div>
                                        {onboardingSlaIncidents.length > 0 && (
                                            <div className="mt-2">
                                                incidents: {onboardingSlaIncidents.map((item) => formatSlaIncident(item)).join(", ")}
                                            </div>
                                        )}
                                        {onboardingSlaActions.length > 0 && (
                                            <div className="mt-2">
                                                actions: {onboardingSlaActions.map((item) => formatPipelineAction(item)).join(", ")}
                                            </div>
                                        )}
                                    </div>
                                )}
                                {onboardingOperationalPipeline && (
                                    <div className={`rounded-lg border px-3 py-3 text-xs ${qualityStatusClass(onboardingOperationalPipeline.status)}`} data-testid="onboarding-operational-pipeline">
                                        <div className="flex items-center justify-between gap-3">
                                            <span className="font-semibold">Operational Onboarding Pipeline</span>
                                            <span className="font-mono">{qualityStatusLabel(onboardingOperationalPipeline.status)}</span>
                                        </div>
                                        <div className="mt-1">
                                            current_stage: <span className="font-mono">{onboardingOperationalPipeline.current_stage_id ?? "n/a"}</span>
                                            {" · "}blocked: <span className="font-mono">{onboardingOperationalPipeline.blocked ? "true" : "false"}</span>
                                        </div>
                                        {operationalPipelineBlockers.length > 0 && (
                                            <div className="mt-2">
                                                blockers: {operationalPipelineBlockers.map((item) => formatOperationalBlocker(item)).join(", ")}
                                            </div>
                                        )}
                                        {operationalPipelineActions.length > 0 && (
                                            <div className="mt-2">
                                                next_actions: {operationalPipelineActions.map((item) => formatPipelineAction(item)).join(", ")}
                                            </div>
                                        )}
                                        <div className="mt-2 space-y-2">
                                            {operationalPipelineStages.map((stage: OnboardingOperationalStage) => (
                                                <div
                                                    key={stage.id}
                                                    className={`rounded-md border px-2 py-2 ${qualityStatusClass(stage.status)}`}
                                                >
                                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                                        <span className="font-medium">{stage.label}</span>
                                                        <span className="font-mono">{qualityStatusLabel(stage.status)}</span>
                                                    </div>
                                                    <div className="mt-1 text-[11px]">
                                                        id: <span className="font-mono">{stage.id}</span>
                                                        {" · "}owner: <span className="font-mono">{stage.owner_lane}</span>
                                                        {" · "}required: <span className="font-mono">{stage.required ? "true" : "false"}</span>
                                                    </div>
                                                    {stage.blockers.length > 0 && (
                                                        <div className="mt-1 text-[11px]">
                                                            blockers: {stage.blockers.map((item) => formatOperationalBlocker(item)).join(", ")}
                                                        </div>
                                                    )}
                                                    {stage.next_action && (
                                                        <div className="mt-1 text-[11px]">
                                                            next_action: {formatPipelineAction(stage.next_action)}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className={`rounded-lg border px-3 py-3 text-xs ${readinessToneClass}`} data-testid="onboarding-readiness-score">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="font-semibold">Индекс готовности</span>
                                        <span className="font-mono">{readinessScore}%</span>
                                    </div>
                                    <div className="mt-1">
                                        {readinessStatusLabel} · {readinessCompletedCount}/{requiredReadinessItems.length} обязательных критериев.
                                    </div>
                                    {readinessBlockers.length > 0 && (
                                        <div className="mt-2 rounded-md border border-current/30 bg-white/50 px-2 py-2" data-testid="onboarding-readiness-blockers">
                                            <div className="font-semibold mb-1">Блокеры:</div>
                                            <div className="space-y-1">
                                                {readinessBlockers.slice(0, 8).map((item) => (
                                                    <div key={item}>- {item}</div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
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
                                            <span>{item.required ? (item.ok ? "OK" : "Не заполнено") : "N/A"}</span>
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
                                <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-2">
                                    <h5 className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                        Гейт запуска
                                    </h5>
                                    <p className="text-xs">
                                        статус: <span className="font-mono">{branchGoLiveState}</span> · разрешено:{" "}
                                        <span className={branchGoLiveAllowed ? "text-green-700" : "text-destructive"}>
                                            {branchGoLiveAllowed ? "да" : "нет"}
                                        </span>
                                    </p>
                                    {branchGoLiveReason && (
                                        <p className="text-xs text-muted-foreground">
                                            причина: <span className="font-mono">{String(branchGoLiveReason)}</span>
                                        </p>
                                    )}
                                    {branchGoLiveWaiverUntil && (
                                        <p className="text-xs text-muted-foreground">
                                            waiver_until: <span className="font-mono">{String(branchGoLiveWaiverUntil)}</span>
                                            {" · "}
                                            {branchGoLiveWaiverActive ? "активен" : "истек"}
                                        </p>
                                    )}
                                    {scorecardFailed && (
                                        <p className="text-xs text-destructive">
                                            Go-live заблокирован: scorecard=fail
                                            {goNoGoMissing.length > 0
                                                ? ` (${goNoGoMissing.map((item) => formatMissingRequirement(item)).join(", ")})`
                                                : ""}
                                        </p>
                                    )}
                                    <textarea
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                        rows={2}
                                        value={goLiveDecisionReason}
                                        onChange={(event) => setGoLiveDecisionReason(event.target.value)}
                                        placeholder="причина для approve/reject/waiver (обязательно для действий)"
                                        disabled={!canEdit}
                                    />
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        <input
                                            type="number"
                                            min={1}
                                            max={720}
                                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                            value={goLiveWaiverHours}
                                            onChange={(event) => setGoLiveWaiverHours(event.target.value)}
                                            placeholder="waiver ttl_hours (часы)"
                                            disabled={!canEdit}
                                        />
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={handleWaiveGoLive}
                                            disabled={!canEdit || waiveGoLiveMutation.isPending || scorecardFailed}
                                        >
                                            {waiveGoLiveMutation.isPending ? "Сохранение..." : "Выдать временный waiver"}
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        <button
                                            type="button"
                                            className="btn-primary"
                                            onClick={handleApproveGoLive}
                                            disabled={!canEdit || approveGoLiveMutation.isPending || scorecardFailed}
                                        >
                                            {approveGoLiveMutation.isPending ? "Сохранение..." : "Подтвердить Go-Live"}
                                        </button>
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={handleRejectGoLive}
                                            disabled={!canEdit || rejectGoLiveMutation.isPending}
                                        >
                                            {rejectGoLiveMutation.isPending ? "Сохранение..." : "Отклонить Go-Live"}
                                        </button>
                                    </div>
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

                                <div className="rounded-lg border border-border/60 bg-muted/10 p-3 space-y-3">
                                    <h5 className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                                        Договор онбординга
                                    </h5>
                                    <div className="rounded-lg border border-border/60 bg-background p-3 space-y-2" data-testid="onboarding-domain-template">
                                        <div className="text-xs text-muted-foreground">
                                            Domain template preset: применяет стартовый контракт под выбранный тип бизнеса.
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2">
                                            <select
                                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                value={selectedDomainTemplate}
                                                onChange={(event) => setSelectedDomainTemplate(event.target.value)}
                                                disabled={!canEdit}
                                                data-testid="onboarding-domain-template-select"
                                            >
                                                {domainTemplatePresets.map((template) => (
                                                    <option key={template.id} value={template.id}>
                                                        {template.label}
                                                    </option>
                                                ))}
                                            </select>
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={handleApplyDomainTemplate}
                                                disabled={!canEdit}
                                                data-testid="onboarding-domain-template-apply"
                                            >
                                                Применить шаблон
                                            </button>
                                        </div>
                                        <p className="text-[11px] text-muted-foreground">
                                            {domainTemplatePresets.find((item) => item.id === selectedDomainTemplate)?.summary ?? "—"}
                                        </p>
                                        {onboardingBlueprintsError ? (
                                            <p className="text-[11px] text-warning">
                                                Используется fallback шаблонов: backend blueprints временно недоступны.
                                            </p>
                                        ) : null}
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted-foreground">domain_slug (ниша)</label>
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
                                    <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3">
                                        <div className="text-xs text-muted-foreground">
                                            Provider binding (manual proof для ChatFlow/WhatsApp).
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div>
                                                <label className="text-xs text-muted-foreground">provider</label>
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.provider ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        provider: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    placeholder="chatflow"
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">instance_id (provider side)</label>
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.instance_id ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        instance_id: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    placeholder="instance-xxxxxxxx"
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">webhook_status</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.webhook_status ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        webhook_status: event.target.value
                                                                            ? event.target.value as "configured" | "pending" | "rebind_required"
                                                                            : null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
                                                    <option value="configured">configured</option>
                                                    <option value="pending">pending</option>
                                                    <option value="rebind_required">rebind_required</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">paid_until</label>
                                                <input
                                                    type="date"
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.paid_until ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        paid_until: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">owner</label>
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.owner ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        owner: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    placeholder="Platform admin"
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">next_renewal_at</label>
                                                <input
                                                    type="date"
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.next_renewal_at ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        next_renewal_at: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">last_rebind_at</label>
                                                <input
                                                    type="date"
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.last_rebind_at ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        last_rebind_at: event.target.value || null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">alert_state</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={onboardingContractDraft.provider_binding?.whatsapp?.alert_state ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        alert_state: event.target.value
                                                                            ? event.target.value as "ok" | "warn" | "critical"
                                                                            : null,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
                                                    <option value="ok">ok</option>
                                                    <option value="warn">warn</option>
                                                    <option value="critical">critical</option>
                                                </select>
                                            </div>
                                            <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                                                <input
                                                    type="checkbox"
                                                    checked={Boolean(onboardingContractDraft.provider_binding?.whatsapp?.rebind_required)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setOnboardingContractDraft((prev) => {
                                                            const normalized = normalizeOnboardingContractPayload(prev);
                                                            return {
                                                                ...normalized,
                                                                provider_binding: {
                                                                    ...normalized.provider_binding,
                                                                    whatsapp: {
                                                                        ...normalized.provider_binding?.whatsapp,
                                                                        rebind_required: event.target.checked,
                                                                    },
                                                                },
                                                            };
                                                        });
                                                    }}
                                                    disabled={!canEdit}
                                                />
                                                rebind_required
                                            </label>
                                        </div>
                                        <div>
                                            <label className="text-xs text-muted-foreground">notes</label>
                                            <textarea
                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                                rows={2}
                                                value={onboardingContractDraft.provider_binding?.whatsapp?.notes ?? ""}
                                                onChange={(event) => {
                                                    setOnboardingContractTouched(true);
                                                    setOnboardingContractDraft((prev) => {
                                                        const normalized = normalizeOnboardingContractPayload(prev);
                                                        return {
                                                            ...normalized,
                                                            provider_binding: {
                                                                ...normalized.provider_binding,
                                                                whatsapp: {
                                                                    ...normalized.provider_binding?.whatsapp,
                                                                    notes: event.target.value || null,
                                                                },
                                                            },
                                                        };
                                                    });
                                                }}
                                                placeholder="Manual ops comment"
                                                disabled={!canEdit}
                                            />
                                        </div>
                                    </div>
                                    <div className="rounded-lg border border-border/60 bg-background p-3 space-y-3" data-testid="onboarding-purchased-form">
                                        <div className="text-xs text-muted-foreground">
                                            Purchased capabilities (schema form). JSON остаётся как fallback в expert-режиме.
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div>
                                                <label className="text-xs text-muted-foreground">WhatsApp</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.channels?.whatsapp)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            channels: {
                                                                ...normalizeCapabilities(prev).channels,
                                                                whatsapp: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">Telegram</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.channels?.telegram)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            channels: {
                                                                ...normalizeCapabilities(prev).channels,
                                                                telegram: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">Instagram</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.channels?.instagram)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            channels: {
                                                                ...normalizeCapabilities(prev).channels,
                                                                instagram: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div>
                                                <label className="text-xs text-muted-foreground">availability_provider</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={purchasedCapabilitiesDraft.providers?.availability_provider ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            providers: {
                                                                ...normalizeCapabilities(prev).providers,
                                                                availability_provider: event.target.value
                                                                    ? event.target.value as CapabilitiesPayload["providers"]["availability_provider"]
                                                                    : null,
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
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
                                                    value={purchasedCapabilitiesDraft.providers?.crm_provider ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            providers: {
                                                                ...normalizeCapabilities(prev).providers,
                                                                crm_provider: event.target.value
                                                                    ? event.target.value as CapabilitiesPayload["providers"]["crm_provider"]
                                                                    : null,
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
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
                                                    value={purchasedCapabilitiesDraft.providers?.calendar_provider ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            providers: {
                                                                ...normalizeCapabilities(prev).providers,
                                                                calendar_provider: event.target.value
                                                                    ? event.target.value as CapabilitiesPayload["providers"]["calendar_provider"]
                                                                    : null,
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
                                                    <option value="none">none</option>
                                                    <option value="google_calendar">google_calendar</option>
                                                    <option value="local">local</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div>
                                                <label className="text-xs text-muted-foreground">booking_mode</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={purchasedCapabilitiesDraft.features?.booking_mode ?? ""}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            features: {
                                                                ...normalizeCapabilities(prev).features,
                                                                booking_mode: event.target.value
                                                                    ? event.target.value as CapabilitiesPayload["features"]["booking_mode"]
                                                                    : null,
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="">Не указано</option>
                                                    <option value="collect_preferences">collect_preferences</option>
                                                    <option value="confirm_slots">confirm_slots</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">knowledge_upload</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.features?.knowledge_upload)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            features: {
                                                                ...normalizeCapabilities(prev).features,
                                                                knowledge_upload: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">analytics</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.features?.analytics)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            features: {
                                                                ...normalizeCapabilities(prev).features,
                                                                analytics: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-muted-foreground">auto_learn</label>
                                                <select
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={toTriState(purchasedCapabilitiesDraft.features?.auto_learn)}
                                                    onChange={(event) => {
                                                        setOnboardingContractTouched(true);
                                                        setPurchasedCapabilitiesDraft((prev) => ({
                                                            ...normalizeCapabilities(prev),
                                                            features: {
                                                                ...normalizeCapabilities(prev).features,
                                                                auto_learn: fromTriState(event.target.value),
                                                            },
                                                        }));
                                                    }}
                                                    disabled={!canEdit}
                                                >
                                                    <option value="inherit">Не указано</option>
                                                    <option value="true">Включено</option>
                                                    <option value="false">Выключено</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div className="flex flex-wrap gap-2 text-xs">
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={applyPurchasedToJson}
                                                disabled={!canEdit}
                                                data-testid="onboarding-purchased-apply-json"
                                            >
                                                Применить в JSON
                                            </button>
                                            <button
                                                type="button"
                                                className="btn-ghost"
                                                onClick={loadPurchasedFromJson}
                                                disabled={!canEdit}
                                                data-testid="onboarding-purchased-load-json"
                                            >
                                                Загрузить из JSON
                                            </button>
                                        </div>
                                        <p className="text-[11px] text-muted-foreground">
                                            Валидация: `domain_slug` в snake_case; при `confirm_slots` обязателен `availability_provider`.
                                        </p>
                                        <details className="rounded-lg border border-border/60 bg-muted/10 p-3">
                                            <summary className="cursor-pointer text-xs text-muted-foreground">
                                                Advanced JSON (expert)
                                            </summary>
                                            <textarea
                                                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                                rows={8}
                                                value={purchasedJsonDraft}
                                                onChange={(event) => {
                                                    setOnboardingContractTouched(true);
                                                    setPurchasedJsonDraft(event.target.value);
                                                    setPurchasedJsonDirty(true);
                                                }}
                                                placeholder='{"channels":{"whatsapp":true}}'
                                                disabled={!canEdit}
                                                data-testid="onboarding-purchased-json"
                                            />
                                        </details>
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
                                            <option value="pending">pending (ожидает)</option>
                                            <option value="confirmed">confirmed (подтверждено)</option>
                                            <option value="rejected">rejected (отклонено)</option>
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
