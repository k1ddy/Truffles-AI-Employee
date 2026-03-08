import type { components } from "@/types/api.generated";

type RawCapabilitiesPayload = components["schemas"]["CapabilitiesPayload-Output"];

type OnboardingAutopilotRequest = components["schemas"]["ConsoleOnboardingAutopilotRequest"];

type OnboardingPurchasedService = NonNullable<OnboardingAutopilotRequest["purchased_services"]>[number];

export type CapabilitiesPayload = RawCapabilitiesPayload & {
    channels: NonNullable<RawCapabilitiesPayload["channels"]>;
    providers: NonNullable<RawCapabilitiesPayload["providers"]>;
    features: NonNullable<RawCapabilitiesPayload["features"]>;
};

export type DomainTemplatePreset = {
    id: string;
    label: string;
    summary: string;
    payload: CapabilitiesPayload;
};

export const WORKING_DAYS = [
    { id: "mon", label: "Пн" },
    { id: "tue", label: "Вт" },
    { id: "wed", label: "Ср" },
    { id: "thu", label: "Чт" },
    { id: "fri", label: "Пт" },
    { id: "sat", label: "Сб" },
    { id: "sun", label: "Вс" },
] as const;

export const WIZARD_STEPS = [
    { id: "branch_draft", label: "Филиал", hint: "Черновик" },
    { id: "integrations", label: "Интеграции", hint: "instance_id" },
    { id: "team", label: "Команда", hint: "владелец/админ" },
    { id: "telegram", label: "Telegram", hint: "chat_id" },
    { id: "knowledge", label: "Знания", hint: "pack" },
    { id: "booking", label: "Бронирование", hint: "calendar" },
    { id: "go_no_go", label: "Go/No-Go", hint: "готовность" },
] as const;

export const MISSING_LABELS: Record<string, string> = {
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

export const CAPABILITY_FIELD_LABELS: Record<string, string> = {
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

export const AUTOPILOT_SERVICE_OPTIONS: Array<{
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

export const FALLBACK_DOMAIN_TEMPLATE_PRESETS: DomainTemplatePreset[] = [
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

export type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

export type FieldGuideItem = {
    field: string;
    required: boolean;
    purpose: string;
    relation: string;
    output: string;
};

export const AUTOPILOT_FIELD_GUIDE: FieldGuideItem[] = [
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

export const MANUAL_STEP_FIELD_GUIDE: Record<WizardStepId, FieldGuideItem[]> = {
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

export function formatMissingRequirement(code: string): string {
    if (code.startsWith("capability_mismatch:")) {
        const key = code.slice("capability_mismatch:".length);
        return `Несоответствие договору: ${CAPABILITY_FIELD_LABELS[key] ?? key}`;
    }
    return MISSING_LABELS[code] ?? code;
}

export function formatSlaIncident(code: string): string {
    return SLA_INCIDENT_LABELS[code] ?? code;
}

export function formatPipelineAction(code: string): string {
    return PIPELINE_ACTION_LABELS[code] ?? code;
}

export function formatSlaProviderStatus(status?: string): string {
    if (!status) {
        return "unknown";
    }
    return SLA_PROVIDER_STATUS_LABELS[status] ?? status;
}

export function formatOperationalBlocker(code: string): string {
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
