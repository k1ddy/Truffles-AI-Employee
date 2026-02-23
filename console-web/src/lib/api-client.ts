/**
 * Truffles Console API Client
 * 
 * Type-safe API client with error handling based on contracts.
 * Generated types from OpenAPI spec with runtime error handling from errors.v1.json.
 */

import axios, { AxiosError, AxiosInstance } from "axios";
import type { components, operations } from "@/types/api.generated";
import { readConsoleContextScopeFromStorage } from "@/lib/console-context-storage";

function getSelectedClientId(): string | undefined {
    const stored = readConsoleContextScopeFromStorage().clientId;
    return stored || undefined;
}

function getSelectedCompanyId(): string | undefined {
    const stored = readConsoleContextScopeFromStorage().companyId;
    return stored || undefined;
}

function getSelectedBranchId(): string | undefined {
    const stored = readConsoleContextScopeFromStorage().branchId;
    return stored || undefined;
}

// ═══════════════════════════════════════════════════════════════════
// ERROR TYPES & HANDLING
// ═══════════════════════════════════════════════════════════════════

/** API Error from server */
export type ApiError = components["schemas"]["ConsoleError"];
export type ApiErrorResponse = components["schemas"]["ConsoleErrorResponse"];

/** Error codes as const for type safety */
export const ErrorCodes = {
    AUTH_REQUIRED: "AUTH_REQUIRED",
    TOKEN_EXPIRED: "TOKEN_EXPIRED",
    ACCESS_DENIED: "ACCESS_DENIED",
    CLIENT_SELECTION_REQUIRED: "CLIENT_SELECTION_REQUIRED",
    COMPANY_SELECTION_REQUIRED: "COMPANY_SELECTION_REQUIRED",
    BRANCH_SELECTION_REQUIRED: "BRANCH_SELECTION_REQUIRED",
    CONVERSATION_REQUIRED: "CONVERSATION_REQUIRED",
    TENANT_MISMATCH: "TENANT_MISMATCH",
    BRANCH_ACCESS_DENIED: "BRANCH_ACCESS_DENIED",
    NOT_FOUND: "NOT_FOUND",
    CASE_ALREADY_TAKEN: "CASE_ALREADY_TAKEN",
    CASE_ALREADY_RESOLVED: "CASE_ALREADY_RESOLVED",
    NOT_ASSIGNED: "NOT_ASSIGNED",
    CASE_NOT_ACTIVE: "CASE_NOT_ACTIVE",
    ONBOARDING_STEP_REQUIRED: "ONBOARDING_STEP_REQUIRED",
    GO_LIVE_GATE_REQUIRED: "GO_LIVE_GATE_REQUIRED",
    CONFIRMATION_REQUIRED: "CONFIRMATION_REQUIRED",
    VALIDATION_ERROR: "VALIDATION_ERROR",
    MESSAGE_TOO_LONG: "MESSAGE_TOO_LONG",
    OUTBOX_FAILED: "OUTBOX_FAILED",
    INTEGRATION_UNAVAILABLE: "INTEGRATION_UNAVAILABLE",
    TELEGRAM_CONFIG_MISSING: "TELEGRAM_CONFIG_MISSING",
    TELEGRAM_LINK_INVALID: "TELEGRAM_LINK_INVALID",
    TELEGRAM_LINK_EXPIRED: "TELEGRAM_LINK_EXPIRED",
    TELEGRAM_LINK_USED: "TELEGRAM_LINK_USED",
    TELEGRAM_LINK_CONFLICT: "TELEGRAM_LINK_CONFLICT",
    RATE_LIMITED: "RATE_LIMITED",
    SERVER_ERROR: "SERVER_ERROR",
    DATABASE_ERROR: "DATABASE_ERROR",
    IDEMPOTENCY_CONFLICT: "IDEMPOTENCY_CONFLICT",
    OIDC_NOT_CONFIGURED: "OIDC_NOT_CONFIGURED",
    IDENTITY_NOT_LINKED: "IDENTITY_NOT_LINKED",
    KNOWLEDGE_PREFLIGHT_REQUIRED: "KNOWLEDGE_PREFLIGHT_REQUIRED",
} as const;

export type ErrorCode = keyof typeof ErrorCodes;

export type ConsoleRole = "platform_admin" | "owner" | "admin" | "manager" | "support" | "specialist" | "viewer";
export type ConsoleSection =
    | "inbox"
    | "outreach"
    | "knowledge"
    | "team"
    | "calendar"
    | "marketing"
    | "insights"
    | "business"
    | "subscription"
    | "settings"
    | "ops"
    | "audit"
    | "integrations"
    | "tenants"
    | "provisioning";
export type ConsoleAction = "read" | "write";

export const ConsoleRBAC: Record<ConsoleSection, Record<ConsoleAction, ConsoleRole[]>> = {
    inbox: {
        read: ["platform_admin", "owner", "admin", "manager", "viewer"],
        write: ["platform_admin", "owner", "admin", "manager"],
    },
    outreach: {
        read: ["platform_admin", "owner", "admin", "manager", "support", "viewer", "specialist"],
        write: ["platform_admin", "owner", "admin", "manager"],
    },
    knowledge: {
        read: ["platform_admin", "owner", "admin", "manager", "viewer"],
        write: ["platform_admin", "owner", "admin"],
    },
    team: {
        read: ["platform_admin", "owner", "admin", "manager"],
        write: ["platform_admin", "owner", "admin"],
    },
    calendar: {
        read: ["platform_admin", "owner", "admin", "manager", "viewer"],
        write: ["platform_admin", "owner", "admin", "manager"],
    },
    marketing: {
        read: ["platform_admin", "owner", "admin"],
        write: ["platform_admin", "owner", "admin"],
    },
    insights: {
        read: ["platform_admin", "owner", "admin"],
        write: [],
    },
    business: {
        read: ["platform_admin", "owner", "admin"],
        write: [],
    },
    subscription: {
        read: ["platform_admin", "owner", "admin"],
        write: [],
    },
    settings: {
        read: ["platform_admin", "owner", "admin"],
        write: ["platform_admin", "owner", "admin"],
    },
    ops: {
        read: ["platform_admin", "owner", "admin"],
        write: ["platform_admin", "owner", "admin"],
    },
    audit: {
        read: ["platform_admin", "owner", "admin", "viewer"],
        write: [],
    },
    integrations: {
        read: ["platform_admin"],
        write: ["platform_admin"],
    },
    tenants: {
        read: ["platform_admin"],
        write: ["platform_admin"],
    },
    provisioning: {
        read: ["platform_admin", "owner", "admin"],
        write: ["platform_admin", "owner", "admin"],
    },
};

const ConsoleRoleSet = new Set<ConsoleRole>([
    "platform_admin",
    "owner",
    "admin",
    "manager",
    "support",
    "specialist",
    "viewer",
]);

export function isConsoleRole(role: string): role is ConsoleRole {
    return ConsoleRoleSet.has(role as ConsoleRole);
}

export function canAccessConsole(
    role: string | null | undefined,
    section: ConsoleSection,
    action: ConsoleAction,
): boolean {
    if (!role) {
        return false;
    }
    if (!isConsoleRole(role)) {
        return false;
    }
    return ConsoleRBAC[section][action].includes(role);
}

/** UI action types from errors.v1.json */
export type UIAction =
    | "redirect_login"
    | "toast"
    | "navigate_back"
    | "refresh_item"
    | "prompt_take"
    | "show_field_errors"
    | "show_pending_state"
    | "disable_actions"
    | "error_modal"
    | "error_page"
    | "maintenance_mode"
    | "ignore";

/** Error config from errors.v1.json (embedded for runtime) */
interface ErrorConfig {
    http_status: number;
    ui_behavior: {
        action: UIAction;
        toast?: boolean;
        toast_type?: "info" | "warning" | "error";
    };
    retryable: boolean;
    retry_after_seconds?: number;
}

const errorConfigs: Record<ErrorCode, ErrorConfig> = {
    AUTH_REQUIRED: {
        http_status: 401,
        ui_behavior: { action: "redirect_login", toast: false },
        retryable: false,
    },
    TOKEN_EXPIRED: {
        http_status: 401,
        ui_behavior: { action: "redirect_login", toast: true, toast_type: "warning" },
        retryable: false,
    },
    ACCESS_DENIED: {
        http_status: 403,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    CLIENT_SELECTION_REQUIRED: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    COMPANY_SELECTION_REQUIRED: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    BRANCH_SELECTION_REQUIRED: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    CONVERSATION_REQUIRED: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    TENANT_MISMATCH: {
        http_status: 403,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    BRANCH_ACCESS_DENIED: {
        http_status: 403,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    NOT_FOUND: {
        http_status: 404,
        ui_behavior: { action: "navigate_back", toast: true, toast_type: "warning" },
        retryable: false,
    },
    CASE_ALREADY_TAKEN: {
        http_status: 409,
        ui_behavior: { action: "refresh_item", toast: true, toast_type: "info" },
        retryable: false,
    },
    CASE_ALREADY_RESOLVED: {
        http_status: 409,
        ui_behavior: { action: "refresh_item", toast: true, toast_type: "info" },
        retryable: false,
    },
    NOT_ASSIGNED: {
        http_status: 403,
        ui_behavior: { action: "prompt_take", toast: true, toast_type: "warning" },
        retryable: false,
    },
    CASE_NOT_ACTIVE: {
        http_status: 400,
        ui_behavior: { action: "refresh_item", toast: true, toast_type: "warning" },
        retryable: false,
    },
    ONBOARDING_STEP_REQUIRED: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    GO_LIVE_GATE_REQUIRED: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    CONFIRMATION_REQUIRED: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    VALIDATION_ERROR: {
        http_status: 422,
        ui_behavior: { action: "show_field_errors", toast: false },
        retryable: false,
    },
    MESSAGE_TOO_LONG: {
        http_status: 422,
        ui_behavior: { action: "show_field_errors", toast: true, toast_type: "warning" },
        retryable: false,
    },
    OUTBOX_FAILED: {
        http_status: 502,
        ui_behavior: { action: "show_pending_state", toast: true, toast_type: "warning" },
        retryable: true,
    },
    INTEGRATION_UNAVAILABLE: {
        http_status: 503,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: true,
        retry_after_seconds: 30,
    },
    TELEGRAM_CONFIG_MISSING: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    TELEGRAM_LINK_INVALID: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    TELEGRAM_LINK_EXPIRED: {
        http_status: 400,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    TELEGRAM_LINK_USED: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
    TELEGRAM_LINK_CONFLICT: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "error" },
        retryable: false,
    },
    RATE_LIMITED: {
        http_status: 429,
        ui_behavior: { action: "disable_actions", toast: true, toast_type: "warning" },
        retryable: true,
    },
    SERVER_ERROR: {
        http_status: 500,
        ui_behavior: { action: "error_modal", toast: false },
        retryable: true,
    },
    DATABASE_ERROR: {
        http_status: 503,
        ui_behavior: { action: "maintenance_mode", toast: true, toast_type: "error" },
        retryable: true,
        retry_after_seconds: 10,
    },
    IDEMPOTENCY_CONFLICT: {
        http_status: 409,
        ui_behavior: { action: "ignore", toast: false },
        retryable: false,
    },
    OIDC_NOT_CONFIGURED: {
        http_status: 503,
        ui_behavior: { action: "error_page", toast: false },
        retryable: false,
    },
    IDENTITY_NOT_LINKED: {
        http_status: 403,
        ui_behavior: { action: "error_page", toast: false },
        retryable: false,
    },
    KNOWLEDGE_PREFLIGHT_REQUIRED: {
        http_status: 409,
        ui_behavior: { action: "toast", toast: true, toast_type: "warning" },
        retryable: false,
    },
};

/** Get error config for handling */
export function getErrorConfig(code: string): ErrorConfig | undefined {
    return errorConfigs[code as ErrorCode];
}

/** Check if error is retryable */
export function isRetryable(code: string): boolean {
    return getErrorConfig(code)?.retryable ?? false;
}

/** Parsed API error with config */
export interface ParsedApiError {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    trace_id: string;
    config?: ErrorConfig;
}

/** Parse axios error into structured error */
export function parseApiError(error: unknown): ParsedApiError {
    if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ApiErrorResponse>;
        const apiError = axiosError.response?.data?.error;

        if (apiError) {
            return {
                code: apiError.code,
                message: apiError.message,
                details: apiError.details ?? undefined,
                trace_id: apiError.trace_id,
                config: getErrorConfig(apiError.code),
            };
        }

        // Fallback for network/timeout errors
        if (axiosError.code === "ECONNABORTED" || axiosError.code === "ERR_NETWORK") {
            return {
                code: "NETWORK_ERROR",
                message: "Network connection failed. Please check your connection.",
                trace_id: Date.now().toString(36),
                config: {
                    http_status: 0,
                    ui_behavior: { action: "toast", toast: true, toast_type: "error" },
                    retryable: true,
                },
            };
        }
    }

    // Unknown error
    return {
        code: "UNKNOWN_ERROR",
        message: error instanceof Error ? error.message : "An unexpected error occurred",
        trace_id: Date.now().toString(36),
        config: {
            http_status: 500,
            ui_behavior: { action: "error_modal", toast: false },
            retryable: false,
        },
    };
}

// ═══════════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════════

const BASE_URL = "/api/proxy";

/** Create typed API client instance */
export function createApiClient(): AxiosInstance {
    const client = axios.create({
        baseURL: BASE_URL,
        headers: {
            "Content-Type": "application/json",
        },
        timeout: 30000,
    });

    // Request interceptor for idempotency key
    client.interceptors.request.use((config) => {
        const headers = config.headers ?? {};
        config.headers = headers;
        const selectedCompanyId = getSelectedCompanyId();
        if (selectedCompanyId && !headers["X-Company-Id"]) {
            headers["X-Company-Id"] = selectedCompanyId;
        }
        const selectedClientId = getSelectedClientId();
        if (selectedClientId && !headers["X-Client-Id"]) {
            headers["X-Client-Id"] = selectedClientId;
        }
        const selectedBranchId = getSelectedBranchId();
        if (selectedBranchId && !headers["X-Branch-Id"]) {
            headers["X-Branch-Id"] = selectedBranchId;
        }
        // Add idempotency key for mutations
        if (config.method && ["post", "put", "patch", "delete"].includes(config.method)) {
            if (!headers["Idempotency-Key"]) {
                headers["Idempotency-Key"] = crypto.randomUUID();
            }
        }
        return config;
    });

    return client;
}

// Default client instance
const apiClient = createApiClient();

// ═══════════════════════════════════════════════════════════════════
// TYPE ALIASES (convenience)
// ═══════════════════════════════════════════════════════════════════

// Schemas
export type Case = components["schemas"]["ConsoleCase"];
export type CaseListResponse = components["schemas"]["ConsoleCaseListResponse"];
export type CaseActionResponse = components["schemas"]["ConsoleCaseActionResponse"];
export type Message = components["schemas"]["ConsoleMessage"];
export type MessageListResponse = components["schemas"]["ConsoleMessageListResponse"];
export type OutreachDeliveryStatus = "queued" | "delivered" | "failed";
export type OutreachMessageRequest = {
    destination: string;
    content: string;
    conversation_id?: string | null;
    branch_id?: string | null;
    pause_bot_minutes?: number | null;
    pause_reason?: string | null;
};
export type OutreachMessageResponse = {
    success: boolean;
    delivery_status: OutreachDeliveryStatus;
    remote_jid?: string | null;
    conversation_id?: string | null;
    case_id?: string | null;
    case_created?: boolean | null;
    outbox_enqueued?: boolean | null;
    lock_until?: string | null;
    message?: Message | null;
    error_code?: string | null;
};
export type HumanLockPauseRequest = {
    minutes?: number;
    reason?: string | null;
};
export type HumanLockStatus = {
    active: boolean;
    remote_jid?: string | null;
    lock_until?: string | null;
    remaining_seconds?: number | null;
    source?: string | null;
    reason?: string | null;
};
export type HumanLockStatusResponse = {
    success: boolean;
    status: HumanLockStatus;
};
export type InboxMacro = components["schemas"]["ConsoleMacro"];
export type InboxMacroListResponse = components["schemas"]["ConsoleMacroListResponse"];
export type InboxMacroCreateRequest = components["schemas"]["ConsoleMacroCreateRequest"];
export type InboxMacroCreateResponse = components["schemas"]["ConsoleMacroCreateResponse"];
export type InboxMacroUpdateRequest = components["schemas"]["ConsoleMacroUpdateRequest"];
export type Client = components["schemas"]["ConsoleClient"];
export type MeResponse = components["schemas"]["ConsoleMeResponse"];
export type Agent = components["schemas"]["ConsoleAgent"];
export type Branch = components["schemas"]["ConsoleBranch"];
export type HealthResponse = components["schemas"]["ConsoleHealthResponse"];
export type MetricsDailyResponse = components["schemas"]["ConsoleMetricsDailyResponse"];
export type BusinessSummaryAction = {
    id: string;
    title: string;
    description: string;
    href: string;
    severity: "critical" | "warn" | "info";
};
export type IncidentAction = {
    id: string;
    title: string;
    description: string;
    href?: string | null;
    job_type?: "outbox_process" | "integration_reconcile" | "heal" | "metrics_snapshot" | "incident_state" | null;
    mode?: "dry_run" | "execute" | null;
    params?: Record<string, unknown> | null;
    dry_run_first: boolean;
    requires_confirmation: boolean;
};
export type IncidentItem = {
    id: string;
    scope: "fleet" | "client" | "branch";
    severity: "critical" | "warn" | "info";
    title: string;
    summary: string;
    reason_code:
        | "outbox_backlog"
        | "provider_billing_blocked"
        | "provider_invalid_recipient"
        | "provider_unavailable"
        | "provider_auth"
        | "provider_rate_limited"
        | "integration_degraded"
        | "handover_backlog"
        | "unknown";
    reason_label: string;
    source: string;
    detected_at: string;
    client_id?: string | null;
    client_slug?: string | null;
    branch_id?: string | null;
    incident_state: "open" | "in_progress" | "resolved";
    incident_state_updated_at?: string | null;
    incident_state_owner?: string | null;
    incident_state_due_at?: string | null;
    incident_state_note?: string | null;
    metrics: Record<string, string | number | boolean | null>;
    actions: IncidentAction[];
};
export type IncidentSummary = {
    total: number;
    critical: number;
    warn: number;
    info: number;
};
export type IncidentListResponse = {
    generated_at: string;
    scope: "fleet" | "client" | "branch";
    summary: IncidentSummary;
    items: IncidentItem[];
};
export type MetricFactMeta = {
    kind: "fact" | "estimate" | "missing";
    source: string;
    as_of?: string | null;
    scope: "system" | "client" | "branch";
    sample_size?: number | null;
    note?: string | null;
};
export type BusinessSummaryResponse = {
    generated_at: string;
    status: "healthy" | "degraded" | "unhealthy";
    status_label: string;
    scheduled_visits_today: number;
    arrived_visits_today: number;
    no_show_visits_today: number;
    cancelled_visits_today: number;
    arrival_rate_percent?: number | null;
    reminder_delivery_failures_today: number;
    no_show_followup_pending: number;
    outbox_backlog: number;
    outbox_failed_24h: number;
    pending_cases: number;
    active_cases: number;
    unresolved_cases: number;
    oldest_unresolved_minutes?: number | null;
    first_response_p90_seconds?: number | null;
    actions: BusinessSummaryAction[];
    metric_meta: Record<string, MetricFactMeta>;
};
export type SubscriptionEvidenceItem = {
    outbox_id: string;
    conversation_id?: string | null;
    inbound_message_id: string;
    created_at: string;
    status: string;
    provider_status?: string | null;
    provider_message_id?: string | null;
};
export type SubscriptionPlanDefaults = {
    plan_name: string;
    included_messages: number;
    included_whatsapp_channels: number;
    source: string;
    reference_only: boolean;
};
export type SubscriptionContractGap = {
    code: string;
    message: string;
    severity: "critical" | "warn" | "info";
};
export type SubscriptionContractHealth = {
    status: "ok" | "partial" | "missing";
    summary: string;
    gaps: SubscriptionContractGap[];
    quota_source: "company_billing_info" | "client_config" | "unknown";
    whatsapp_source: "company_billing_info" | "client_config" | "onboarding_contract" | "unknown";
    payment_status_source: "onboarding_contract" | "unknown";
    has_active_onboarding_contract: boolean;
};
export type SubscriptionMeterItem = {
    key: string;
    label: string;
    meter_type: "messages" | "channels" | "addon";
    included?: number | null;
    used?: number | null;
    remaining?: number | null;
    status: "ok" | "warning" | "limit_reached" | "over_limit" | "not_included" | "included_not_configured" | "unknown";
    source: string;
    note?: string | null;
};
export type SubscriptionSummaryResponse = {
    generated_at: string;
    period_start: string;
    period_end: string;
    next_billing_date: string;
    plan_name?: string | null;
    contract_label?: string | null;
    currency?: string | null;
    monthly_quota?: number | null;
    quota_source: "company_billing_info" | "client_config" | "unknown";
    billable_messages: number;
    remaining_quota?: number | null;
    projected_month_total?: number | null;
    usage_percent?: number | null;
    projected_remaining_quota?: number | null;
    projected_over_quota: boolean;
    projected_overage_messages?: number | null;
    quota_alert_level: "normal" | "warning_80" | "limit_100";
    quota_alert_message: string;
    overage_policy_message: string;
    over_quota: boolean;
    payment_status: "pending" | "confirmed" | "rejected" | "unknown";
    payment_confirmed_at?: string | null;
    payment_status_source: "onboarding_contract" | "unknown";
    payment_status_message?: string | null;
    contract_health: SubscriptionContractHealth;
    plan_defaults: SubscriptionPlanDefaults;
    meters: SubscriptionMeterItem[];
    recommended_actions: BusinessSummaryAction[];
    evidence: SubscriptionEvidenceItem[];
    metric_meta: Record<string, MetricFactMeta>;
};
export type DataTrustSummaryResponse = {
    generated_at: string;
    status: "healthy" | "degraded" | "unhealthy";
    status_label: string;
    metric_date?: string | null;
    analytics_scope_limited: boolean;
    first_response_missing_total?: number | null;
    escalation_meta_missing_total?: number | null;
    intent_missing_total?: number | null;
    knowledge_last_published_at?: string | null;
    knowledge_stale_hours?: number | null;
    audit_events_24h: number;
    critical_audit_events_24h: number;
    actions: BusinessSummaryAction[];
    metric_meta: Record<string, MetricFactMeta>;
};
export type TeamManagerPerformanceItem = {
    manager_name: string;
    unresolved_cases: number;
    pending_cases: number;
    active_cases: number;
    oldest_unresolved_minutes?: number | null;
    avg_first_response_seconds_30d?: number | null;
};
export type TeamPerformanceSummaryResponse = {
    generated_at: string;
    status: "healthy" | "degraded" | "unhealthy";
    status_label: string;
    metric_date?: string | null;
    analytics_scope_limited: boolean;
    manager_median_response_seconds?: number | null;
    first_response_p90_seconds?: number | null;
    unresolved_cases: number;
    unresolved_older_than_60m: number;
    managers: TeamManagerPerformanceItem[];
    actions: BusinessSummaryAction[];
    metric_meta: Record<string, MetricFactMeta>;
};
export type OwnerOperationMode = "capture_leads" | "stable_quality" | "team_protection";
export type OwnerOperationSettingsPatch = {
    reminder_1_minutes: number;
    reminder_2_minutes: number;
    escalation_timeout_minutes: number;
};
export type OwnerOperationMetricSnapshot = {
    outbox_backlog: number;
    unresolved_older_than_60m: number;
    manager_median_response_seconds?: number | null;
};
export type OwnerOperationMetricDelta = {
    baseline?: number | null;
    current?: number | null;
    delta?: number | null;
    trend: "up" | "down" | "stable" | "unknown";
};
export type OwnerOperationPreviewResponse = {
    generated_at: string;
    mode: OwnerOperationMode;
    mode_label: string;
    settings_patch: OwnerOperationSettingsPatch;
    current_settings: OwnerOperationSettingsPatch;
    baseline: OwnerOperationMetricSnapshot;
    warnings: string[];
    metric_meta: Record<string, MetricFactMeta>;
};
export type OwnerOperationApplyResponse = {
    success: boolean;
    operation_id: string;
    mode: OwnerOperationMode;
    mode_label: string;
    applied_settings: OwnerOperationSettingsPatch;
    previous_settings: OwnerOperationSettingsPatch;
    baseline: OwnerOperationMetricSnapshot;
    applied_at: string;
    impact_check_due_at: string;
    metric_meta: Record<string, MetricFactMeta>;
};
export type OwnerOperationRollbackResponse = {
    success: boolean;
    operation_id: string;
    restored_settings: OwnerOperationSettingsPatch;
    rolled_back_at: string;
    message: string;
};
export type OwnerOperationImpactResponse = {
    operation_id: string;
    mode: OwnerOperationMode;
    checked_at: string;
    due_at: string;
    summary: "improved" | "regressed" | "mixed_or_stable";
    baseline: OwnerOperationMetricSnapshot;
    current: OwnerOperationMetricSnapshot;
    metrics: Record<string, OwnerOperationMetricDelta>;
    metric_meta: Record<string, MetricFactMeta>;
};
export type SettingsResponse = components["schemas"]["ConsoleSettingsResponse"];
export type AuditEvent = components["schemas"]["ConsoleAuditEvent"];
export type AuditListResponse = components["schemas"]["ConsoleAuditListResponse"];
export type AgentListResponse = components["schemas"]["ConsoleAgentListResponse"];
export type BranchIntegrationStatus = components["schemas"]["ConsoleBranchIntegrationStatus"];
export type IntegrationsListResponse = components["schemas"]["ConsoleIntegrationsListResponse"];
export type IntegrationBranchActionRequest = components["schemas"]["ConsoleIntegrationBranchActionRequest"];
export type IntegrationBranchActionResponse = components["schemas"]["ConsoleIntegrationBranchActionResponse"];
export type ProviderOpsAction = components["schemas"]["ConsoleProviderOpsQueueItem"]["recommended_action"];
export type ProviderOpsQueueItem = components["schemas"]["ConsoleProviderOpsQueueItem"];
export type OpsJobDefinition = components["schemas"]["ConsoleOpsJobDefinition"];
export type OpsJobCatalogResponse = components["schemas"]["ConsoleOpsJobCatalogResponse"];
export type OpsJobRunRequest = components["schemas"]["ConsoleOpsJobRunRequest"];
export type OpsJobRecord = components["schemas"]["ConsoleOpsJobRecord"];
export type OpsJobRunResponse = components["schemas"]["ConsoleOpsJobRunResponse"];
export type OpsJobListResponse = components["schemas"]["ConsoleOpsJobListResponse"];
export type TelegramVerifyRequest = components["schemas"]["ConsoleTelegramVerifyRequest"];
export type TelegramVerifyResponse = components["schemas"]["ConsoleTelegramVerifyResponse"];
export type TelegramTestRequest = components["schemas"]["ConsoleTelegramTestRequest"];
export type TelegramTestResponse = components["schemas"]["ConsoleTelegramTestResponse"];
export type TelegramLinkResponse = components["schemas"]["ConsoleTelegramLinkResponse"];
export type KnowledgeCurrentResponse = {
    version_id?: string | null;
    payload?: unknown;
    content?: string | null;
};
export type KnowledgeValidationResponse = {
    valid?: boolean;
    errors?: string[];
    warnings?: string[];
    diff?: string | null;
};
export type KnowledgePublishResponse = {
    success?: boolean;
    version_id?: string | null;
    published_at?: string | null;
    message?: string | null;
};
export type KnowledgeHistoryItem = {
    id?: string | null;
    status?: string | null;
    created_at?: string | null;
    published_at?: string | null;
    summary?: string | null;
};
export type KnowledgeHistoryResponse = {
    items?: KnowledgeHistoryItem[];
};
export type KnowledgeRollbackResponse = {
    success?: boolean;
    version_id?: string | null;
};
export type LearningCandidate = components["schemas"]["ConsoleLearningCandidate"];
export type LearningCandidateListResponse = components["schemas"]["ConsoleLearningCandidateListResponse"];
export type LearningCandidateActionResponse = components["schemas"]["ConsoleLearningCandidateActionResponse"];
export type MarketingCampaignStatus =
    | "draft"
    | "ready"
    | "executed"
    | "paused"
    | "in_review"
    | "approved"
    | "scheduled"
    | "running"
    | "completed"
    | "cancelled"
    | "failed";
export type MarketingCampaignStatusV2 =
    | "draft"
    | "in_review"
    | "approved"
    | "scheduled"
    | "running"
    | "paused"
    | "completed"
    | "cancelled"
    | "failed";
export type MarketingDeliveryStatus = "queued" | "sent" | "failed" | "replied";
export type MarketingAudienceMode = "branch_active_conversations";
export type MarketingSegmentCode = "reactivation_30_120" | "no_show_recovery_14d" | "engaged_no_booking_7d";
export type MarketingCampaign = {
    id: string;
    client_id: string;
    branch_id: string;
    name: string;
    message_text: string;
    status: MarketingCampaignStatus;
    status_v2: MarketingCampaignStatusV2;
    segment_code: MarketingSegmentCode;
    segment_params: Record<string, unknown>;
    segment_summary?: string | null;
    audience_mode: MarketingAudienceMode;
    preview_total: number;
    preflight_valid: boolean;
    preflight_snapshot?: Record<string, unknown> | null;
    approved_by?: string | null;
    approved_at?: string | null;
    requested_review_at?: string | null;
    run_started_at?: string | null;
    run_completed_at?: string | null;
    last_preview_at?: string | null;
    executed_at?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
};
export type MarketingCampaignListResponse = { items: MarketingCampaign[] };
export type MarketingCampaignCreateRequest = {
    branch_id: string;
    name: string;
    message_text: string;
    segment_code?: MarketingSegmentCode;
    segment_params?: Record<string, unknown> | null;
    audience_mode?: MarketingAudienceMode;
};
export type MarketingCampaignCreateResponse = { campaign: MarketingCampaign };
export type MarketingCampaignUpdateRequest = {
    name?: string;
    message_text?: string;
    segment_code?: MarketingSegmentCode;
    segment_params?: Record<string, unknown> | null;
    reason?: string | null;
};
export type MarketingCampaignPreviewRequest = { sample_limit?: number };
export type MarketingAudienceFunnel = {
    candidate_count: number;
    matched_count: number;
    segment_excluded_count: number;
    eligible_count: number;
    suppressed_count: number;
    suppression_reason_counts: Record<string, number>;
};
export type MarketingCampaignPreviewResponse = {
    campaign_id: string;
    branch_id: string;
    audience_mode: MarketingAudienceMode;
    estimated_recipients: number;
    eligible_count: number;
    suppressed_count: number;
    segment_params: Record<string, unknown>;
    segment_summary?: string | null;
    sample_conversation_ids: string[];
    sample_recipient_jids: string[];
    funnel: MarketingAudienceFunnel;
};
export type MarketingSegmentEditableField = {
    key: string;
    label: string;
    type: "int" | "bool";
    min?: number | null;
    max?: number | null;
    step?: number | null;
};
export type MarketingSegmentDefinition = {
    code: MarketingSegmentCode;
    label: string;
    short_label: string;
    description: string;
    defaults: Record<string, unknown>;
    summary: string;
    editable_fields: MarketingSegmentEditableField[];
};
export type MarketingSegmentCatalogResponse = {
    items: MarketingSegmentDefinition[];
};
export type MarketingCampaignExecuteRequest = { confirm_send: boolean; max_recipients?: number | null };
export type MarketingCampaignExecuteResponse = {
    campaign_id: string;
    queued_count: number;
    skipped_count: number;
    status: "queued" | "skipped";
};
export type MarketingDeliverySample = {
    delivery_id: string;
    conversation_id?: string | null;
    recipient_jid?: string | null;
    status: MarketingDeliveryStatus;
    outbox_status?: string | null;
    last_error?: string | null;
    updated_at?: string | null;
};
export type MarketingCampaignDiagnosticsResponse = {
    campaign_id: string;
    queued_count: number;
    sent_count: number;
    failed_count: number;
    replied_count: number;
    total_count: number;
    failure_classes: Record<string, number>;
    retryable_failed_count: number;
    permanent_failed_count: number;
    sample_failed: MarketingDeliverySample[];
};
export type MarketingCampaignRetryRequest = { confirm_retry: boolean; limit?: number | null };
export type MarketingCampaignRetryResponse = {
    campaign_id: string;
    retried_count: number;
    skipped_count: number;
    skipped_permanent: number;
};
export type MarketingCampaignLifecycleActionRequest = { reason?: string | null };
export type MarketingCampaignAudienceResponse = {
    campaign_id: string;
    total_count: number;
    eligible_count: number;
    suppressed_count: number;
    items: MarketingCampaignRecipient[];
};
export type MarketingCampaignRecipient = {
    id: string;
    campaign_id: string;
    recipient_jid: string;
    user_id?: string | null;
    conversation_id?: string | null;
    segment_code: MarketingSegmentCode;
    reason_codes: string[];
    reason_hints: string[];
    suppressed: boolean;
    suppression_reasons: string[];
    suppression_hints: string[];
    updated_at?: string | null;
};
export type MarketingCampaignPreflightResponse = {
    campaign_id: string;
    generated_at: string;
    preflight_valid: boolean;
    blocked_reasons: string[];
    outbox_health_status: string;
    outbox_pending: number;
    outbox_failed_24h: number;
    provider_billing_blocked: boolean;
    provider_billing_blocked_count: number;
    audience_total: number;
    eligible_count: number;
    suppressed_count: number;
    segment_params: Record<string, unknown>;
    segment_summary?: string | null;
    preview_stats?: MarketingAudienceFunnel | null;
    template_gate_enabled: boolean;
    template_state?: string | null;
    template_ok: boolean;
};
export type TenantsOperationalSnapshotWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";
export type TenantsOperationalSnapshotLifecycleMode = "active" | "archived" | "all";
export type TenantsOperationalSnapshotKpiId =
    | "onboardingCoverage"
    | "goLiveReadiness"
    | "serviceStability"
    | "decommissionShare"
    | "changeFailure"
    | "rollbackShare"
    | "blockedSignals";
export type TenantsOperationalSnapshotKpiStatus = "ok" | "warn" | "critical";
export type TenantsOperationalSnapshotKpi = {
    onboardingCoverage: number;
    goLiveReadiness: number;
    serviceStability: number;
    decommissionShare: number;
    changeFailure: number;
    rollbackShare: number;
    blockedSignals: number;
};
export type TenantsOperationalSnapshotDrilldownItem = {
    id: TenantsOperationalSnapshotKpiId;
    status: TenantsOperationalSnapshotKpiStatus;
    value: number;
    reason: string;
};
export type TenantsOperationalSnapshotAttentionSummary = {
    activeClientsTotal: number;
    highRiskClients: number;
    mediumRiskClients: number;
    outboxFailed24hTotal: number;
    pendingHandoversTotal: number;
};
export type TenantsOperationalSnapshotPayload = {
    generatedAt: string;
    sourceWindow: number;
    workspaceMode: TenantsOperationalSnapshotWorkspaceMode;
    lifecycleMode: TenantsOperationalSnapshotLifecycleMode;
    kpi: TenantsOperationalSnapshotKpi;
    drilldown: TenantsOperationalSnapshotDrilldownItem[];
    attentionSummary: TenantsOperationalSnapshotAttentionSummary;
};
export type TenantsWeeklySnapshotRecord = {
    id: string;
    created_at: string;
    client_id: string;
    week_key: string;
    snapshot: TenantsOperationalSnapshotPayload;
    actor_name?: string | null;
};
export type TenantsWeeklySnapshotListResponse = {
    items: TenantsWeeklySnapshotRecord[];
    cursor?: string | null;
    has_more: boolean;
};
export type CreateTenantsWeeklySnapshotRequest = {
    client_id: string;
    week_key: string;
    snapshot: TenantsOperationalSnapshotPayload;
};
export type CreateTenantsWeeklySnapshotResponse = {
    item: TenantsWeeklySnapshotRecord;
};
export type GetTenantsPortfolioParams = {
    cursor?: string;
    limit?: number;
    q?: string;
    company_id?: string;
    lifecycle?: "active" | "archived" | "all";
    attention_limit?: number;
    stale_after_minutes?: number;
    include_low?: "true" | "false";
};
export type TenantsPortfolioResponse = {
    generated_at: string;
    clients: components["schemas"]["ConsoleClientListResponse"];
    fleet_attention: components["schemas"]["ConsoleFleetAttentionResponse"];
};
export type GetTenantsCompanyCockpitParams = {
    company_id: string;
    client_id?: string;
    lifecycle?: "active" | "archived" | "all";
    client_limit?: number;
    branch_limit?: number;
    client_cursor?: string;
    branch_cursor?: string;
    client_q?: string;
    branch_q?: string;
};
export type TenantsCompanyCockpitResponse = {
    generated_at: string;
    company_id: string;
    selected_client_id?: string | null;
    clients: components["schemas"]["ConsoleClientListResponse"];
    branches: components["schemas"]["ConsoleBranchListResponse"];
};
export type AuditTenantsSensitiveAccessRequest = {
    branch_id: string;
    field: "instance_id";
    action: "reveal" | "copy";
    context?: string;
};
export type AuditTenantsSensitiveAccessResponse = {
    ok: boolean;
    audit_id: string;
};

// Query params
export type ListCasesParams = operations["list_cases_console_v1_cases_get"]["parameters"]["query"];
export type ListInboxMacrosParams = operations["list_inbox_macros_console_v1_inbox_macros_get"]["parameters"]["query"];
export type ListAuditParams = operations["list_audit_events_console_v1_audit_get"]["parameters"]["query"];
export type ListLearningCandidatesParams = operations["list_learning_candidates_console_v1_learning_candidates_get"]["parameters"]["query"];
export type ListCompaniesParams = operations["list_companies_console_v1_admin_companies_get"]["parameters"]["query"];
export type ListClientsParams = operations["list_clients_console_v1_admin_clients_get"]["parameters"]["query"];
export type ListBranchesParams = operations["list_branches_console_v1_admin_branches_get"]["parameters"]["query"];
export type ListTenantsWeeklySnapshotsParams = {
    client_id: string;
    week_key?: string;
    cursor?: string;
    limit?: number;
};
export type ListFleetAttentionParams = operations["list_fleet_attention_console_v1_admin_fleet_attention_get"]["parameters"]["query"];
export type ListIntegrationsParams = operations["list_integrations_console_v1_admin_integrations_get"]["parameters"]["query"];
export type ListProviderLifecycleParams = operations["list_provider_lifecycle_console_v1_admin_provider_lifecycle_get"]["parameters"]["query"];
export type ListMembershipsParams = operations["list_memberships_console_v1_admin_memberships_get"]["parameters"]["query"];
export type ListReferencePacksParams = operations["list_reference_packs_console_v1_admin_reference_packs_get"]["parameters"]["query"];
export type ListOnboardingBlueprintsParams = { domain_slug?: string };
export type ListOpsJobsParams = operations["list_ops_jobs_console_v1_ops_jobs_get"]["parameters"]["query"];
export type ListBranchChangesParams = operations["list_branch_changes_console_v1_admin_branch_changes_get"]["parameters"]["query"];
export type ListMarketingCampaignsParams = { branch_id?: string; status?: MarketingCampaignStatus };
export type BranchGoLiveDecisionRequest = { reason: string };
export type BranchGoLiveWaiverRequest = { reason: string; ttl_hours: number };
export type OnboardingBlueprintQuestionTemplate = {
    code: string;
    question: string;
    blocking_go_live: boolean;
};
export type OnboardingBlueprintRequiredFieldsProfile = {
    fields: string[];
    checksum: string;
};
export type OnboardingBlueprint = {
    id: string;
    domain_slug: string;
    label: string;
    summary: string;
    payload: components["schemas"]["CapabilitiesPayload"];
    go_live_blockers_profile: string[];
    question_templates: OnboardingBlueprintQuestionTemplate[];
    required_fields_profile: OnboardingBlueprintRequiredFieldsProfile;
    readiness_weights: Record<string, number>;
};
export type OnboardingBlueprintListResponse = {
    items: OnboardingBlueprint[];
};

// ═══════════════════════════════════════════════════════════════════
// API METHODS (typed)
// ═══════════════════════════════════════════════════════════════════

/** Auth endpoints */
export const authApi = {
    getMe: () => apiClient.get<MeResponse>("/me"),
};

/** Case endpoints */
export const casesApi = {
    list: (params?: ListCasesParams) =>
        apiClient.get<CaseListResponse>("/cases", { params }),

    get: (caseId: string) =>
        apiClient.get<Case>(`/cases/${caseId}`),

    take: (caseId: string) =>
        apiClient.post<CaseActionResponse>(`/cases/${caseId}/take`),

    resolve: (caseId: string) =>
        apiClient.post<CaseActionResponse>(`/cases/${caseId}/resolve`),

    returnToBot: (caseId: string) =>
        apiClient.post<CaseActionResponse>(`/cases/${caseId}/return`),

    getMessages: (caseId: string, params?: { cursor?: string; limit?: number }) =>
        apiClient.get<MessageListResponse>(`/cases/${caseId}/messages`, { params }),
};

/** Inbox macros endpoints */
export const inboxApi = {
    listMacros: (params?: ListInboxMacrosParams, branchId?: string | null) =>
        apiClient.get<InboxMacroListResponse>("/inbox/macros", {
            params,
            headers: branchId ? { "X-Branch-Id": branchId } : undefined,
        }),
    createMacro: (data: InboxMacroCreateRequest, branchId?: string | null) =>
        apiClient.post<InboxMacroCreateResponse>("/inbox/macros", data, {
            headers: branchId ? { "X-Branch-Id": branchId } : undefined,
        }),
    updateMacro: (macroId: string, data: InboxMacroUpdateRequest, branchId?: string | null) =>
        apiClient.patch<InboxMacro>(`/inbox/macros/${macroId}`, data, {
            headers: branchId ? { "X-Branch-Id": branchId } : undefined,
        }),
};

/** Message endpoints */
export const messagesApi = {
    send: (conversationId: string, content: string, idempotencyKey?: string) =>
        apiClient.post<components["schemas"]["ConsoleManagerMessageResponse"]>(
            `/conversations/${conversationId}/messages`,
            { content },
            idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined
        ),
};

export const outreachApi = {
    sendMessage: (data: OutreachMessageRequest, idempotencyKey?: string) =>
        apiClient.post<OutreachMessageResponse>(
            "/outreach/messages",
            data,
            idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined,
        ),
    getHumanLockStatus: (conversationId: string) =>
        apiClient.get<HumanLockStatusResponse>(`/conversations/${conversationId}/human-lock`),
    pauseHumanLock: (conversationId: string, data: HumanLockPauseRequest) =>
        apiClient.post<HumanLockStatusResponse>(`/conversations/${conversationId}/human-lock/pause`, data),
    releaseHumanLock: (conversationId: string) =>
        apiClient.delete<HumanLockStatusResponse>(`/conversations/${conversationId}/human-lock`),
};

/** Ops endpoints */
export const opsApi = {
    getHealth: () => apiClient.get<HealthResponse>("/health"),
    getMetricsDaily: (date?: string) =>
        apiClient.get<MetricsDailyResponse>("/metrics/daily", { params: { date } }),
    getJobsCatalog: () => apiClient.get<OpsJobCatalogResponse>("/ops/jobs/catalog"),
    listJobs: (params?: ListOpsJobsParams) =>
        apiClient.get<OpsJobListResponse>("/ops/jobs", { params }),
    getJob: (jobId: string) =>
        apiClient.get<OpsJobRunResponse>(`/ops/jobs/${jobId}`),
    runJob: (data: OpsJobRunRequest) =>
        apiClient.post<OpsJobRunResponse>("/ops/jobs/run", data),
};

/** Owner/Admin business control endpoints */
export const businessApi = {
    getSummary: () => apiClient.get<BusinessSummaryResponse>("/business/summary"),
    getIncidents: () => apiClient.get<IncidentListResponse>("/business/incidents"),
    getSubscriptionSummary: () => apiClient.get<SubscriptionSummaryResponse>("/subscription/summary"),
    getDataTrustSummary: () => apiClient.get<DataTrustSummaryResponse>("/business/data-trust"),
    getTeamPerformanceSummary: () => apiClient.get<TeamPerformanceSummaryResponse>("/business/team-performance"),
    previewOwnerModeOperation: (data: { mode: OwnerOperationMode }) =>
        apiClient.post<OwnerOperationPreviewResponse>("/business/operations/owner-mode/preview", data),
    applyOwnerModeOperation: (data: { mode: OwnerOperationMode }) =>
        apiClient.post<OwnerOperationApplyResponse>("/business/operations/owner-mode/apply", data),
    rollbackOwnerModeOperation: (data?: { operation_id?: string }) =>
        apiClient.post<OwnerOperationRollbackResponse>("/business/operations/owner-mode/rollback", data ?? {}),
    getOwnerOperationImpact: (operationId: string) =>
        apiClient.get<OwnerOperationImpactResponse>(`/business/operations/${operationId}/impact`),
};

/** Telegram connector endpoints */
export const telegramApi = {
    verify: (data: TelegramVerifyRequest) =>
        apiClient.post<TelegramVerifyResponse>("/telegram/verify", data),
    test: (data: TelegramTestRequest) =>
        apiClient.post<TelegramTestResponse>("/telegram/test", data),
};

/** Agent endpoints */
export const agentsApi = {
    list: () => apiClient.get<AgentListResponse>("/agents"),
    linkTelegram: (agentId: string) =>
        apiClient.post<TelegramLinkResponse>(`/agents/${agentId}/telegram/link`),
};

/** Settings endpoints */
export const settingsApi = {
    get: () => apiClient.get<SettingsResponse>("/settings"),
    update: (data: components["schemas"]["ConsoleSettingsUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["ConsoleSettingsUpdateResponse"]>("/settings", data),
};

function buildClientHeader(clientId?: string): Record<string, string> | undefined {
    if (!clientId) {
        return undefined;
    }
    return { "X-Client-Id": clientId };
}

/** Admin provisioning endpoints */
export const adminApi = {
    listCompanies: (params?: ListCompaniesParams) =>
        apiClient.get<components["schemas"]["ConsoleCompanyListResponse"]>("/admin/companies", { params }),
    listClients: (params?: ListClientsParams) =>
        apiClient.get<components["schemas"]["ConsoleClientListResponse"]>("/admin/clients", { params }),
    listBranches: (params?: ListBranchesParams) =>
        apiClient.get<components["schemas"]["ConsoleBranchListResponse"]>("/admin/branches", { params }),
    getTenantsPortfolio: (params?: GetTenantsPortfolioParams) =>
        apiClient.get<TenantsPortfolioResponse>("/admin/tenants/portfolio", { params }),
    getTenantsCompanyCockpit: (params: GetTenantsCompanyCockpitParams) =>
        apiClient.get<TenantsCompanyCockpitResponse>("/admin/tenants/company-cockpit", { params }),
    listTenantsWeeklySnapshots: (params: ListTenantsWeeklySnapshotsParams) =>
        apiClient.get<TenantsWeeklySnapshotListResponse>("/admin/tenants/weekly-snapshots", { params }),
    saveTenantsWeeklySnapshot: (data: CreateTenantsWeeklySnapshotRequest) =>
        apiClient.post<CreateTenantsWeeklySnapshotResponse>("/admin/tenants/weekly-snapshots", data),
    auditTenantsSensitiveAccess: (data: AuditTenantsSensitiveAccessRequest) =>
        apiClient.post<AuditTenantsSensitiveAccessResponse>("/admin/tenants/sensitive-access", data),
    listFleetAttention: (params?: ListFleetAttentionParams) =>
        apiClient.get<components["schemas"]["ConsoleFleetAttentionResponse"]>("/admin/fleet/attention", { params }),
    listIncidents: (params?: { limit?: number }) =>
        apiClient.get<IncidentListResponse>("/admin/incidents", { params }),
    listIntegrations: (params?: ListIntegrationsParams) =>
        apiClient.get<components["schemas"]["ConsoleIntegrationsListResponse"]>("/admin/integrations", { params }),
    listProviderLifecycle: (params?: ListProviderLifecycleParams) =>
        apiClient.get<components["schemas"]["ConsoleProviderLifecycleListResponse"]>("/admin/provider-lifecycle", { params }),
    getMarketingSegmentsCatalog: () =>
        apiClient.get<MarketingSegmentCatalogResponse>("/admin/marketing/segments"),
    listMarketingCampaigns: (params?: ListMarketingCampaignsParams) =>
        apiClient.get<MarketingCampaignListResponse>("/admin/marketing/campaigns", { params }),
    createMarketingCampaign: (data: MarketingCampaignCreateRequest) =>
        apiClient.post<MarketingCampaignCreateResponse>("/admin/marketing/campaigns", data),
    updateMarketingCampaign: (campaignId: string, data: MarketingCampaignUpdateRequest) =>
        apiClient.patch<MarketingCampaignCreateResponse>(`/admin/marketing/campaigns/${campaignId}`, data),
    previewMarketingCampaign: (campaignId: string, data?: MarketingCampaignPreviewRequest) =>
        apiClient.post<MarketingCampaignPreviewResponse>(`/admin/marketing/campaigns/${campaignId}/preview`, data ?? {}),
    getMarketingCampaignAudience: (
        campaignId: string,
        params?: { include_suppressed?: boolean; limit?: number },
    ) =>
        apiClient.get<MarketingCampaignAudienceResponse>(`/admin/marketing/campaigns/${campaignId}/audience`, { params }),
    requestMarketingCampaignApproval: (campaignId: string, data?: MarketingCampaignLifecycleActionRequest) =>
        apiClient.post<MarketingCampaignCreateResponse>(
            `/admin/marketing/campaigns/${campaignId}/request-approval`,
            data ?? {},
        ),
    approveMarketingCampaign: (campaignId: string, data?: MarketingCampaignLifecycleActionRequest) =>
        apiClient.post<MarketingCampaignCreateResponse>(`/admin/marketing/campaigns/${campaignId}/approve`, data ?? {}),
    pauseMarketingCampaign: (campaignId: string, data?: MarketingCampaignLifecycleActionRequest) =>
        apiClient.post<MarketingCampaignCreateResponse>(`/admin/marketing/campaigns/${campaignId}/pause`, data ?? {}),
    resumeMarketingCampaign: (campaignId: string, data?: MarketingCampaignLifecycleActionRequest) =>
        apiClient.post<MarketingCampaignCreateResponse>(`/admin/marketing/campaigns/${campaignId}/resume`, data ?? {}),
    getMarketingCampaignPreflight: (campaignId: string) =>
        apiClient.get<MarketingCampaignPreflightResponse>(`/admin/marketing/campaigns/${campaignId}/preflight`),
    executeMarketingCampaign: (campaignId: string, data: MarketingCampaignExecuteRequest) =>
        apiClient.post<MarketingCampaignExecuteResponse>(`/admin/marketing/campaigns/${campaignId}/execute`, data),
    getMarketingCampaignDiagnostics: (campaignId: string, params?: { sample_limit?: number }) =>
        apiClient.get<MarketingCampaignDiagnosticsResponse>(
            `/admin/marketing/campaigns/${campaignId}/diagnostics`,
            { params },
        ),
    retryFailedMarketingCampaignDeliveries: (campaignId: string, data: MarketingCampaignRetryRequest) =>
        apiClient.post<MarketingCampaignRetryResponse>(`/admin/marketing/campaigns/${campaignId}/retry-failed`, data),
    reconcileIntegrationBranch: (branchId: string, data: IntegrationBranchActionRequest) =>
        apiClient.post<IntegrationBranchActionResponse>(`/admin/integrations/${branchId}/reconcile`, data),
    listMemberships: (params?: ListMembershipsParams) =>
        apiClient.get<components["schemas"]["ConsoleMembershipListResponse"]>("/admin/memberships", { params }),
    createCompany: (data: components["schemas"]["ConsoleCompanyCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleCompanyCreateResponse"]>("/admin/companies", data),
    patchCompany: (companyId: string, data: components["schemas"]["ConsoleCompanyUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["ConsoleCompany"]>(`/admin/companies/${companyId}`, data),
    createClient: (data: components["schemas"]["ConsoleClientCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleClientCreateResponse"]>("/admin/clients", data),
    patchClient: (clientId: string, data: components["schemas"]["ConsoleClientUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["ConsoleClient"]>(`/admin/clients/${clientId}`, data),
    archiveClient: (clientId: string, data: components["schemas"]["ConsoleClientLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleClient"]>(`/admin/clients/${clientId}/archive`, data),
    restoreClient: (clientId: string, data: components["schemas"]["ConsoleClientLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleClient"]>(`/admin/clients/${clientId}/restore`, data),
    createBranch: (data: components["schemas"]["ConsoleBranchCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleBranchCreateResponse"]>("/admin/branches", data),
    patchBranch: (branchId: string, data: components["schemas"]["ConsoleBranchUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["ConsoleBranch"]>(`/admin/branches/${branchId}`, data),
    listBranchChanges: (params?: ListBranchChangesParams) =>
        apiClient.get<components["schemas"]["ConsoleBranchChangeListResponse"]>("/admin/branch-changes", { params }),
    getBranchChange: (changeId: string) =>
        apiClient.get<components["schemas"]["ConsoleBranchChangeResponse"]>(`/admin/branch-changes/${changeId}`),
    draftBranchChange: (data: components["schemas"]["ConsoleBranchChangeDraftRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleBranchChangeResponse"]>("/admin/branch-changes/draft", data),
    validateBranchChange: (changeId: string) =>
        apiClient.post<components["schemas"]["ConsoleBranchChangeResponse"]>(`/admin/branch-changes/${changeId}/validate`),
    publishBranchChange: (changeId: string, data: components["schemas"]["ConsoleBranchChangePublishRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleBranchChangeResponse"]>(`/admin/branch-changes/${changeId}/publish`, data),
    rollbackBranchChange: (changeId: string, data: components["schemas"]["ConsoleBranchChangeRollbackRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleBranchChangeResponse"]>(`/admin/branch-changes/${changeId}/rollback`, data),
    approveBranchGoLive: (branchId: string, data: BranchGoLiveDecisionRequest) =>
        apiClient.post<components["schemas"]["ConsoleBranch"]>(`/admin/branches/${branchId}/go-live/approve`, data),
    rejectBranchGoLive: (branchId: string, data: BranchGoLiveDecisionRequest) =>
        apiClient.post<components["schemas"]["ConsoleBranch"]>(`/admin/branches/${branchId}/go-live/reject`, data),
    waiveBranchGoLive: (branchId: string, data: BranchGoLiveWaiverRequest) =>
        apiClient.post<components["schemas"]["ConsoleBranch"]>(`/admin/branches/${branchId}/go-live/waive`, data),
    createAgent: (data: components["schemas"]["ConsoleAgentCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleAgentCreateResponse"]>("/admin/agents", data),
    disableAgent: (agentId: string, data: components["schemas"]["ConsoleAgentLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleAgent"]>(`/admin/agents/${agentId}/disable`, data),
    enableAgent: (agentId: string, data: components["schemas"]["ConsoleAgentLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleAgent"]>(`/admin/agents/${agentId}/enable`, data),
    rebindAgentOidc: (agentId: string, data: components["schemas"]["ConsoleAgentOidcRebindRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleAgentOidcRebindResponse"]>(`/admin/agents/${agentId}/oidc/rebind`, data),
    createMembership: (data: components["schemas"]["ConsoleMembershipCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleAgentMembership"]>("/admin/memberships", data),
    patchMembership: (membershipId: string, data: components["schemas"]["ConsoleMembershipUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["ConsoleAgentMembership"]>(`/admin/memberships/${membershipId}`, data),
    getCapabilities: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["ConsoleCapabilitiesResponse"]>("/admin/capabilities", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    patchCapabilities: (data: components["schemas"]["ConsoleCapabilitiesPatchRequest"], clientId?: string) =>
        apiClient.patch<components["schemas"]["ConsoleCapabilitiesRecord"]>("/admin/capabilities", data, {
            headers: buildClientHeader(clientId),
        }),
    getOnboardingContract: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["ConsoleOnboardingContractResponse"]>("/admin/onboarding-contract", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    patchOnboardingContract: (
        data: components["schemas"]["ConsoleOnboardingContractPatchRequest"],
        clientId?: string,
    ) =>
        apiClient.patch<components["schemas"]["ConsoleOnboardingContractRecord"]>("/admin/onboarding-contract", data, {
            headers: buildClientHeader(clientId),
        }),
    getWebhookSecret: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["ConsoleWebhookSecretResponse"]>("/admin/webhook-secret", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    runOnboardingAutopilot: (
        data: components["schemas"]["ConsoleOnboardingAutopilotRequest"],
        clientId?: string,
    ) =>
        apiClient.post<components["schemas"]["ConsoleOnboardingAutopilotResponse"]>("/admin/onboarding/autopilot", data, {
            headers: buildClientHeader(clientId),
        }),
    listOnboardingBlueprints: (params?: ListOnboardingBlueprintsParams) =>
        apiClient.get<OnboardingBlueprintListResponse>("/admin/onboarding-blueprints", { params }),
    listReferencePacks: (params?: ListReferencePacksParams) =>
        apiClient.get<components["schemas"]["ConsoleReferencePackListResponse"]>("/admin/reference-packs", { params }),
    upsertReferencePack: (domainSlug: string, data: components["schemas"]["ConsoleReferencePackUpsertRequest"]) =>
        apiClient.put<components["schemas"]["ConsoleReferencePack"]>(`/admin/reference-packs/${domainSlug}`, data),
};

/** Onboarding endpoints */
export const onboardingApi = {
    status: (branchId?: string) =>
        apiClient.get<components["schemas"]["ConsoleOnboardingStatusResponse"]>("/onboarding/status", {
            params: branchId ? { branch_id: branchId } : undefined,
        }),
    scorecard: (branchId?: string) =>
        apiClient.get<components["schemas"]["ConsoleOnboardingScorecardResponse"]>("/onboarding/scorecard", {
            params: branchId ? { branch_id: branchId } : undefined,
        }),
    advance: (data: components["schemas"]["ConsoleOnboardingAdvanceRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleOnboardingStatusResponse"]>("/onboarding/advance", data),
};

/** Confirmation endpoints */
export const confirmationsApi = {
    create: (data: components["schemas"]["ConsoleConfirmationCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConsoleConfirmationResponse"]>("/confirmations", data),
};

/** Audit endpoints */
export const auditApi = {
    list: (params?: ListAuditParams) =>
        apiClient.get<AuditListResponse>("/audit", { params }),
};

/** Knowledge endpoints */
export const knowledgeApi = {
    getCurrent: () =>
        apiClient.get<KnowledgeCurrentResponse>("/knowledge/current"),
    validate: (draftText: string) =>
        apiClient.post<KnowledgeValidationResponse>("/knowledge/validate", { draft_text: draftText }),
    publish: (draftText: string, options?: { skipPreflightCheck?: boolean }) =>
        apiClient.post<KnowledgePublishResponse>("/knowledge/publish", {
            draft_text: draftText,
            skip_preflight_check: options?.skipPreflightCheck ?? false,
        }),
    history: () =>
        apiClient.get<KnowledgeHistoryResponse>("/knowledge/history"),
    rollback: (versionId: string, confirmationId?: string) =>
        apiClient.post<KnowledgeRollbackResponse>("/knowledge/rollback", {
            version_id: versionId,
            confirmation_id: confirmationId,
        }),
};

/** Learning candidates endpoints */
export const learningApi = {
    list: (params?: ListLearningCandidatesParams) =>
        apiClient.get<LearningCandidateListResponse>("/learning/candidates", { params }),
    approve: (candidateId: string) =>
        apiClient.post<LearningCandidateActionResponse>(`/learning/candidates/${candidateId}/approve`),
    reject: (candidateId: string) =>
        apiClient.post<LearningCandidateActionResponse>(`/learning/candidates/${candidateId}/reject`),
};

// Export default client
export default apiClient;
