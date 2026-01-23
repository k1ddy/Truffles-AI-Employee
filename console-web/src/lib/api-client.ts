/**
 * Truffles Console API Client
 * 
 * Type-safe API client with error handling based on contracts.
 * Generated types from OpenAPI spec with runtime error handling from errors.v1.json.
 */

import axios, { AxiosError, AxiosInstance } from "axios";
import type { components, operations } from "@/types/api.generated";

const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";

function getSelectedClientId(): string | undefined {
    if (typeof window === "undefined") {
        return undefined;
    }
    const stored = window.localStorage.getItem(CLIENT_ID_STORAGE_KEY);
    return stored || undefined;
}

function getSelectedBranchId(): string | undefined {
    if (typeof window === "undefined") {
        return undefined;
    }
    const stored = window.localStorage.getItem(BRANCH_ID_STORAGE_KEY);
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
    BRANCH_SELECTION_REQUIRED: "BRANCH_SELECTION_REQUIRED",
    TENANT_MISMATCH: "TENANT_MISMATCH",
    BRANCH_ACCESS_DENIED: "BRANCH_ACCESS_DENIED",
    NOT_FOUND: "NOT_FOUND",
    CASE_ALREADY_TAKEN: "CASE_ALREADY_TAKEN",
    CASE_ALREADY_RESOLVED: "CASE_ALREADY_RESOLVED",
    NOT_ASSIGNED: "NOT_ASSIGNED",
    CASE_NOT_ACTIVE: "CASE_NOT_ACTIVE",
    VALIDATION_ERROR: "VALIDATION_ERROR",
    MESSAGE_TOO_LONG: "MESSAGE_TOO_LONG",
    OUTBOX_FAILED: "OUTBOX_FAILED",
    INTEGRATION_UNAVAILABLE: "INTEGRATION_UNAVAILABLE",
    TELEGRAM_CONFIG_MISSING: "TELEGRAM_CONFIG_MISSING",
    RATE_LIMITED: "RATE_LIMITED",
    SERVER_ERROR: "SERVER_ERROR",
    DATABASE_ERROR: "DATABASE_ERROR",
    IDEMPOTENCY_CONFLICT: "IDEMPOTENCY_CONFLICT",
    OIDC_NOT_CONFIGURED: "OIDC_NOT_CONFIGURED",
    IDENTITY_NOT_LINKED: "IDENTITY_NOT_LINKED",
} as const;

export type ErrorCode = keyof typeof ErrorCodes;

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
    details?: Record<string, unknown>;
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
                details: apiError.details,
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
export type Client = components["schemas"]["Client"];
export type MeResponse = components["schemas"]["MeResponse"];
export type Agent = components["schemas"]["Agent"];
export type Branch = components["schemas"]["Branch"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type MetricsDailyResponse = components["schemas"]["MetricsDailyResponse"];
export type SettingsResponse = components["schemas"]["SettingsResponse"];
export type AuditEvent = components["schemas"]["AuditEvent"];
export type AuditListResponse = components["schemas"]["AuditListResponse"];
export type TelegramVerifyRequest = components["schemas"]["TelegramVerifyRequest"];
export type TelegramVerifyResponse = components["schemas"]["TelegramVerifyResponse"];
export type TelegramTestRequest = components["schemas"]["TelegramTestRequest"];
export type TelegramTestResponse = components["schemas"]["TelegramTestResponse"];

// Query params
export type ListCasesParams = operations["listCases"]["parameters"]["query"];
export type ListAuditParams = operations["listAuditEvents"]["parameters"]["query"];

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

    getMessages: (caseId: string, params?: { cursor?: string; limit?: number }) =>
        apiClient.get<MessageListResponse>(`/cases/${caseId}/messages`, { params }),
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
};

/** Telegram connector endpoints */
export const telegramApi = {
    verify: (data: TelegramVerifyRequest) =>
        apiClient.post<TelegramVerifyResponse>("/telegram/verify", data),
    test: (data: TelegramTestRequest) =>
        apiClient.post<TelegramTestResponse>("/telegram/test", data),
};

/** Settings endpoints */
export const settingsApi = {
    get: () => apiClient.get<SettingsResponse>("/settings"),
    update: (data: components["schemas"]["SettingsUpdateRequest"]) =>
        apiClient.patch<components["schemas"]["SettingsUpdateResponse"]>("/settings", data),
};

/** Audit endpoints */
export const auditApi = {
    list: (params?: ListAuditParams) =>
        apiClient.get<AuditListResponse>("/audit", { params }),
};

// Export default client
export default apiClient;
