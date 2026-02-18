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
export type ApiError = components["schemas"]["Error"];
export type ApiErrorResponse = components["schemas"]["ErrorResponse"];

/** Error codes as const for type safety */
export const ErrorCodes = {
    AUTH_REQUIRED: "AUTH_REQUIRED",
    TOKEN_EXPIRED: "TOKEN_EXPIRED",
    ACCESS_DENIED: "ACCESS_DENIED",
    CLIENT_SELECTION_REQUIRED: "CLIENT_SELECTION_REQUIRED",
    COMPANY_SELECTION_REQUIRED: "COMPANY_SELECTION_REQUIRED",
    BRANCH_SELECTION_REQUIRED: "BRANCH_SELECTION_REQUIRED",
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
    | "knowledge"
    | "team"
    | "calendar"
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

export function canAccessConsole(
    role: ConsoleRole | null | undefined,
    section: ConsoleSection,
    action: ConsoleAction,
): boolean {
    if (!role) {
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
export type Case = components["schemas"]["Case"];
export type CaseListResponse = components["schemas"]["CaseListResponse"];
export type CaseActionResponse = components["schemas"]["CaseActionResponse"];
export type Message = components["schemas"]["Message"];
export type MessageListResponse = components["schemas"]["MessageListResponse"];
export type InboxMacro = components["schemas"]["InboxMacro"];
export type InboxMacroListResponse = components["schemas"]["InboxMacroListResponse"];
export type InboxMacroCreateRequest = components["schemas"]["InboxMacroCreateRequest"];
export type InboxMacroCreateResponse = components["schemas"]["InboxMacroCreateResponse"];
export type InboxMacroUpdateRequest = components["schemas"]["InboxMacroUpdateRequest"];
export type Client = components["schemas"]["Client"];
export type MeResponse = components["schemas"]["MeResponse"];
export type Agent = components["schemas"]["Agent"];
export type Branch = components["schemas"]["Branch"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type MetricsDailyResponse = components["schemas"]["MetricsDailyResponse"];
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
    job_type?: "outbox_process" | "integration_reconcile" | "heal" | "metrics_snapshot" | null;
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
export type SettingsResponse = components["schemas"]["SettingsResponse"];
export type AuditEvent = components["schemas"]["AuditEvent"];
export type AuditListResponse = components["schemas"]["AuditListResponse"];
export type AgentListResponse = components["schemas"]["AgentListResponse"];
export type BranchIntegrationStatus = components["schemas"]["BranchIntegrationStatus"];
export type IntegrationsListResponse = components["schemas"]["IntegrationsListResponse"];
export type IntegrationBranchActionRequest = components["schemas"]["IntegrationBranchActionRequest"];
export type IntegrationBranchActionResponse = components["schemas"]["IntegrationBranchActionResponse"];
export type ProviderOpsAction = components["schemas"]["ProviderOpsAction"];
export type ProviderOpsQueueItem = components["schemas"]["ProviderOpsQueueItem"];
export type OpsJobDefinition = components["schemas"]["OpsJobDefinition"];
export type OpsJobCatalogResponse = components["schemas"]["OpsJobCatalogResponse"];
export type OpsJobRunRequest = components["schemas"]["OpsJobRunRequest"];
export type OpsJobRecord = components["schemas"]["OpsJobRecord"];
export type OpsJobRunResponse = components["schemas"]["OpsJobRunResponse"];
export type OpsJobListResponse = components["schemas"]["OpsJobListResponse"];
export type TelegramVerifyRequest = components["schemas"]["TelegramVerifyRequest"];
export type TelegramVerifyResponse = components["schemas"]["TelegramVerifyResponse"];
export type TelegramTestRequest = components["schemas"]["TelegramTestRequest"];
export type TelegramTestResponse = components["schemas"]["TelegramTestResponse"];
export type TelegramLinkResponse = components["schemas"]["TelegramLinkResponse"];
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
export type LearningCandidate = components["schemas"]["LearningCandidate"];
export type LearningCandidateListResponse = components["schemas"]["LearningCandidateListResponse"];
export type LearningCandidateActionResponse = components["schemas"]["LearningCandidateActionResponse"];

// Query params
export type ListCasesParams = operations["listCases"]["parameters"]["query"];
export type ListInboxMacrosParams = operations["listInboxMacros"]["parameters"]["query"];
export type ListAuditParams = operations["listAuditEvents"]["parameters"]["query"];
export type ListLearningCandidatesParams = operations["listLearningCandidates"]["parameters"]["query"];
export type ListCompaniesParams = operations["listAdminCompanies"]["parameters"]["query"];
export type ListClientsParams = operations["listAdminClients"]["parameters"]["query"];
export type ListBranchesParams = operations["listAdminBranches"]["parameters"]["query"];
export type ListFleetAttentionParams = operations["listFleetAttention"]["parameters"]["query"];
export type ListIntegrationsParams = operations["listAdminIntegrations"]["parameters"]["query"];
export type ListProviderLifecycleParams = operations["listAdminProviderLifecycle"]["parameters"]["query"];
export type ListMembershipsParams = operations["listAdminMemberships"]["parameters"]["query"];
export type ListReferencePacksParams = operations["listAdminReferencePacks"]["parameters"]["query"];
export type ListOpsJobsParams = operations["listOpsJobs"]["parameters"]["query"];
export type ListBranchChangesParams = operations["listAdminBranchChanges"]["parameters"]["query"];
export type BranchGoLiveDecisionRequest = { reason: string };
export type BranchGoLiveWaiverRequest = { reason: string; ttl_hours: number };

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
        apiClient.post<components["schemas"]["SendMessageResponse"]>(
            `/conversations/${conversationId}/messages`,
            { content },
            idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined
        ),
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
    update: (data: components["schemas"]["SettingsUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["SettingsUpdateResponse"]>("/settings", data),
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
        apiClient.get<components["schemas"]["CompanyListResponse"]>("/admin/companies", { params }),
    listClients: (params?: ListClientsParams) =>
        apiClient.get<components["schemas"]["ClientListResponse"]>("/admin/clients", { params }),
    listBranches: (params?: ListBranchesParams) =>
        apiClient.get<components["schemas"]["BranchListResponse"]>("/admin/branches", { params }),
    listFleetAttention: (params?: ListFleetAttentionParams) =>
        apiClient.get<components["schemas"]["FleetAttentionResponse"]>("/admin/fleet/attention", { params }),
    listIncidents: (params?: { limit?: number }) =>
        apiClient.get<IncidentListResponse>("/admin/incidents", { params }),
    listIntegrations: (params?: ListIntegrationsParams) =>
        apiClient.get<components["schemas"]["IntegrationsListResponse"]>("/admin/integrations", { params }),
    listProviderLifecycle: (params?: ListProviderLifecycleParams) =>
        apiClient.get<components["schemas"]["ProviderLifecycleListResponse"]>("/admin/provider-lifecycle", { params }),
    reconcileIntegrationBranch: (branchId: string, data: IntegrationBranchActionRequest) =>
        apiClient.post<IntegrationBranchActionResponse>(`/admin/integrations/${branchId}/reconcile`, data),
    listMemberships: (params?: ListMembershipsParams) =>
        apiClient.get<components["schemas"]["MembershipListResponse"]>("/admin/memberships", { params }),
    createCompany: (data: components["schemas"]["CompanyCreateRequest"]) =>
        apiClient.post<components["schemas"]["CompanyCreateResponse"]>("/admin/companies", data),
    patchCompany: (companyId: string, data: components["schemas"]["CompanyUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["Company"]>(`/admin/companies/${companyId}`, data),
    createClient: (data: components["schemas"]["ClientCreateRequest"]) =>
        apiClient.post<components["schemas"]["ClientCreateResponse"]>("/admin/clients", data),
    patchClient: (clientId: string, data: components["schemas"]["ClientUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["Client"]>(`/admin/clients/${clientId}`, data),
    archiveClient: (clientId: string, data: components["schemas"]["ClientLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["Client"]>(`/admin/clients/${clientId}/archive`, data),
    restoreClient: (clientId: string, data: components["schemas"]["ClientLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["Client"]>(`/admin/clients/${clientId}/restore`, data),
    createBranch: (data: components["schemas"]["BranchCreateRequest"]) =>
        apiClient.post<components["schemas"]["BranchCreateResponse"]>("/admin/branches", data),
    patchBranch: (branchId: string, data: components["schemas"]["BranchUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["Branch"]>(`/admin/branches/${branchId}`, data),
    listBranchChanges: (params?: ListBranchChangesParams) =>
        apiClient.get<components["schemas"]["BranchChangeListResponse"]>("/admin/branch-changes", { params }),
    getBranchChange: (changeId: string) =>
        apiClient.get<components["schemas"]["BranchChangeResponse"]>(`/admin/branch-changes/${changeId}`),
    draftBranchChange: (data: components["schemas"]["BranchChangeDraftRequest"]) =>
        apiClient.post<components["schemas"]["BranchChangeResponse"]>("/admin/branch-changes/draft", data),
    validateBranchChange: (changeId: string) =>
        apiClient.post<components["schemas"]["BranchChangeResponse"]>(`/admin/branch-changes/${changeId}/validate`),
    publishBranchChange: (changeId: string, data: components["schemas"]["BranchChangePublishRequest"]) =>
        apiClient.post<components["schemas"]["BranchChangeResponse"]>(`/admin/branch-changes/${changeId}/publish`, data),
    rollbackBranchChange: (changeId: string, data: components["schemas"]["BranchChangeRollbackRequest"]) =>
        apiClient.post<components["schemas"]["BranchChangeResponse"]>(`/admin/branch-changes/${changeId}/rollback`, data),
    approveBranchGoLive: (branchId: string, data: BranchGoLiveDecisionRequest) =>
        apiClient.post<components["schemas"]["Branch"]>(`/admin/branches/${branchId}/go-live/approve`, data),
    rejectBranchGoLive: (branchId: string, data: BranchGoLiveDecisionRequest) =>
        apiClient.post<components["schemas"]["Branch"]>(`/admin/branches/${branchId}/go-live/reject`, data),
    waiveBranchGoLive: (branchId: string, data: BranchGoLiveWaiverRequest) =>
        apiClient.post<components["schemas"]["Branch"]>(`/admin/branches/${branchId}/go-live/waive`, data),
    createAgent: (data: components["schemas"]["AgentCreateRequest"]) =>
        apiClient.post<components["schemas"]["AgentCreateResponse"]>("/admin/agents", data),
    disableAgent: (agentId: string, data: components["schemas"]["AgentLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["Agent"]>(`/admin/agents/${agentId}/disable`, data),
    enableAgent: (agentId: string, data: components["schemas"]["AgentLifecycleActionRequest"]) =>
        apiClient.post<components["schemas"]["Agent"]>(`/admin/agents/${agentId}/enable`, data),
    rebindAgentOidc: (agentId: string, data: components["schemas"]["AgentOidcRebindRequest"]) =>
        apiClient.post<components["schemas"]["AgentOidcRebindResponse"]>(`/admin/agents/${agentId}/oidc/rebind`, data),
    createMembership: (data: components["schemas"]["MembershipCreateRequest"]) =>
        apiClient.post<components["schemas"]["AgentMembership"]>("/admin/memberships", data),
    patchMembership: (membershipId: string, data: components["schemas"]["MembershipUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["AgentMembership"]>(`/admin/memberships/${membershipId}`, data),
    getCapabilities: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["CapabilitiesResponse"]>("/admin/capabilities", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    patchCapabilities: (data: components["schemas"]["CapabilitiesPatchRequest"], clientId?: string) =>
        apiClient.patch<components["schemas"]["CapabilitiesRecord"]>("/admin/capabilities", data, {
            headers: buildClientHeader(clientId),
        }),
    getOnboardingContract: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["OnboardingContractResponse"]>("/admin/onboarding-contract", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    patchOnboardingContract: (
        data: components["schemas"]["OnboardingContractPatchRequest"],
        clientId?: string,
    ) =>
        apiClient.patch<components["schemas"]["OnboardingContractRecord"]>("/admin/onboarding-contract", data, {
            headers: buildClientHeader(clientId),
        }),
    getWebhookSecret: (params: { branch_id?: string; clientId?: string }) =>
        apiClient.get<components["schemas"]["WebhookSecretResponse"]>("/admin/webhook-secret", {
            params: params.branch_id ? { branch_id: params.branch_id } : undefined,
            headers: buildClientHeader(params.clientId),
        }),
    runOnboardingAutopilot: (
        data: components["schemas"]["OnboardingAutopilotRequest"],
        clientId?: string,
    ) =>
        apiClient.post<components["schemas"]["OnboardingAutopilotResponse"]>("/admin/onboarding/autopilot", data, {
            headers: buildClientHeader(clientId),
        }),
    listReferencePacks: (params?: ListReferencePacksParams) =>
        apiClient.get<components["schemas"]["ReferencePackListResponse"]>("/admin/reference-packs", { params }),
    upsertReferencePack: (domainSlug: string, data: components["schemas"]["ReferencePackUpsertRequest"]) =>
        apiClient.put<components["schemas"]["ReferencePack"]>(`/admin/reference-packs/${domainSlug}`, data),
};

/** Onboarding endpoints */
export const onboardingApi = {
    status: (branchId?: string) =>
        apiClient.get<components["schemas"]["OnboardingStatusResponse"]>("/onboarding/status", {
            params: branchId ? { branch_id: branchId } : undefined,
        }),
    scorecard: (branchId?: string) =>
        apiClient.get<components["schemas"]["OnboardingScorecardResponse"]>("/onboarding/scorecard", {
            params: branchId ? { branch_id: branchId } : undefined,
        }),
    advance: (data: components["schemas"]["OnboardingAdvanceRequest"]) =>
        apiClient.post<components["schemas"]["OnboardingStatusResponse"]>("/onboarding/advance", data),
};

/** Confirmation endpoints */
export const confirmationsApi = {
    create: (data: components["schemas"]["ConfirmationCreateRequest"]) =>
        apiClient.post<components["schemas"]["ConfirmationResponse"]>("/confirmations", data),
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
