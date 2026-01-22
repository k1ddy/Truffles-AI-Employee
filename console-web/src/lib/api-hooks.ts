/**
 * TanStack Query Hooks for Truffles Console API
 * 
 * Type-safe React Query hooks with integrated error handling.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import {
    authApi,
    casesApi,
    messagesApi,
    opsApi,
    settingsApi,
    auditApi,
    parseApiError,
    type ListCasesParams,
    type ListAuditParams,
} from "./api-client";
import type { components } from "@/types/api.generated";

// ═══════════════════════════════════════════════════════════════════
// QUERY KEYS (for cache invalidation)
// ═══════════════════════════════════════════════════════════════════

export const queryKeys = {
    me: ["me"] as const,
    cases: {
        all: ["cases"] as const,
        list: (params?: ListCasesParams) => ["cases", "list", params] as const,
        detail: (id: string) => ["cases", "detail", id] as const,
        messages: (id: string) => ["cases", "messages", id] as const,
    },
    health: ["health"] as const,
    metrics: {
        daily: (date?: string) => ["metrics", "daily", date] as const,
    },
    settings: ["settings"] as const,
    audit: (params?: ListAuditParams) => ["audit", params] as const,
};

// ═══════════════════════════════════════════════════════════════════
// ERROR HANDLER HOOK
// ═══════════════════════════════════════════════════════════════════

export function useErrorHandler() {
    const router = useRouter();
    const queryClient = useQueryClient();

    const handleError = (error: unknown, caseId?: string) => {
        const parsed = parseApiError(error);
        const config = parsed.config;

        if (!config) {
            toast.error(parsed.message);
            return parsed;
        }

        switch (config.ui_behavior.action) {
            case "redirect_login":
                if (config.ui_behavior.toast) {
                    toast(parsed.message, { icon: "⚠️" });
                }
                router.push("/login");
                break;

            case "toast":
                if (config.ui_behavior.toast_type === "error") {
                    toast.error(parsed.message);
                } else if (config.ui_behavior.toast_type === "warning") {
                    toast(parsed.message, { icon: "⚠️" });
                } else {
                    toast(parsed.message);
                }
                break;

            case "navigate_back":
                if (config.ui_behavior.toast) {
                    toast(parsed.message, { icon: "⚠️" });
                }
                router.push("/inbox");
                break;

            case "refresh_item":
                if (config.ui_behavior.toast) {
                    toast(parsed.message, { icon: "ℹ️" });
                }
                if (caseId) {
                    queryClient.invalidateQueries({ queryKey: queryKeys.cases.detail(caseId) });
                    queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
                }
                break;

            case "prompt_take":
                toast(parsed.message, { icon: "✋" });
                break;

            case "error_modal":
                toast.error(`${parsed.message}\n\nRef: ${parsed.trace_id}`);
                break;

            case "show_pending_state":
                toast(parsed.message, { icon: "⏳" });
                break;

            case "maintenance_mode":
                toast.error("System under maintenance. Please try again later.");
                break;

            case "ignore":
                // Silent
                break;

            default:
                toast.error(parsed.message);
        }

        return parsed;
    };

    return { handleError };
}

// ═══════════════════════════════════════════════════════════════════
// AUTH HOOKS
// ═══════════════════════════════════════════════════════════════════

export function useMe() {
    return useQuery({
        queryKey: queryKeys.me,
        queryFn: async () => {
            const { data } = await authApi.getMe();
            return data;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
        retry: false, // Don't retry auth errors
    });
}

// ═══════════════════════════════════════════════════════════════════
// CASES HOOKS
// ═══════════════════════════════════════════════════════════════════

export function useCases(params?: ListCasesParams) {
    return useQuery({
        queryKey: queryKeys.cases.list(params),
        queryFn: async () => {
            const { data } = await casesApi.list(params);
            return data;
        },
    });
}

export function useCase(caseId: string) {
    return useQuery({
        queryKey: queryKeys.cases.detail(caseId),
        queryFn: async () => {
            const { data } = await casesApi.get(caseId);
            return data;
        },
        enabled: !!caseId,
    });
}

export function useCaseMessages(caseId: string) {
    return useQuery({
        queryKey: queryKeys.cases.messages(caseId),
        queryFn: async () => {
            const { data } = await casesApi.getMessages(caseId);
            return data;
        },
        enabled: !!caseId,
        refetchInterval: 5000, // Poll for new messages
    });
}

export function useTakeCase() {
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();

    return useMutation({
        mutationFn: async (caseId: string) => {
            const { data } = await casesApi.take(caseId);
            return data;
        },
        onSuccess: (data, caseId) => {
            toast.success("Case taken successfully");
            queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
            queryClient.setQueryData(queryKeys.cases.detail(caseId), data.case);
        },
        onError: (error, caseId) => {
            handleError(error, caseId);
        },
    });
}

export function useResolveCase() {
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();

    return useMutation({
        mutationFn: async (caseId: string) => {
            const { data } = await casesApi.resolve(caseId);
            return data;
        },
        onSuccess: (data, caseId) => {
            toast.success("Case resolved");
            queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
            queryClient.setQueryData(queryKeys.cases.detail(caseId), data.case);
        },
        onError: (error, caseId) => {
            handleError(error, caseId);
        },
    });
}

// ═══════════════════════════════════════════════════════════════════
// MESSAGES HOOKS
// ═══════════════════════════════════════════════════════════════════

interface SendMessageParams {
    conversationId: string;
    content: string;
    caseId: string;
}

export function useSendMessage() {
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();

    return useMutation({
        mutationFn: async ({ conversationId, content }: SendMessageParams) => {
            const { data } = await messagesApi.send(conversationId, content);
            return data;
        },
        onSuccess: (data, { caseId }) => {
            // Invalidate messages to show new message
            queryClient.invalidateQueries({ queryKey: queryKeys.cases.messages(caseId) });
        },
        onError: (error, { caseId }) => {
            handleError(error, caseId);
        },
    });
}

// ═══════════════════════════════════════════════════════════════════
// OPS HOOKS
// ═══════════════════════════════════════════════════════════════════

export function useHealth() {
    return useQuery({
        queryKey: queryKeys.health,
        queryFn: async () => {
            const { data } = await opsApi.getHealth();
            return data;
        },
        refetchInterval: 30000, // Poll every 30s
        staleTime: 10000,
    });
}

export function useMetricsDaily(date?: string) {
    return useQuery({
        queryKey: queryKeys.metrics.daily(date),
        queryFn: async () => {
            const { data } = await opsApi.getMetricsDaily(date);
            return data;
        },
        staleTime: 60000, // 1 minute cache
    });
}

// ═══════════════════════════════════════════════════════════════════
// SETTINGS HOOKS
// ═══════════════════════════════════════════════════════════════════

export function useSettings() {
    return useQuery({
        queryKey: queryKeys.settings,
        queryFn: async () => {
            const { data } = await settingsApi.get();
            return data;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}

export function useUpdateSettings() {
    const queryClient = useQueryClient();
    const { handleError } = useErrorHandler();

    return useMutation({
        mutationFn: async (data: components["schemas"]["SettingsUpdateRequest"]) => {
            const { data: response } = await settingsApi.update(data);
            return response;
        },
        onSuccess: () => {
            toast.success("Settings updated");
            queryClient.invalidateQueries({ queryKey: queryKeys.settings });
        },
        onError: (error) => {
            handleError(error);
        },
    });
}

// ═══════════════════════════════════════════════════════════════════
// AUDIT HOOKS
// ═══════════════════════════════════════════════════════════════════

export function useAuditEvents(params?: ListAuditParams) {
    return useQuery({
        queryKey: queryKeys.audit(params),
        queryFn: async () => {
            const { data } = await auditApi.list(params);
            return data;
        },
    });
}
