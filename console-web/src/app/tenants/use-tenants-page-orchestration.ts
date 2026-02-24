"use client";

import { useCallback } from "react";
import toast from "react-hot-toast";
import type { QueryClient } from "@tanstack/react-query";
import type { TenantsSensitiveAction } from "@/components/TenantsSensitiveIdCell";
import { adminApi } from "@/lib/api-client";

type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";

type InlineErrorReporter = (input: { code?: string; message: string; scope?: string }) => void;
type ApiErrorReporter = (
    error: unknown,
    options?: {
        includeProvisioningGuidance?: boolean;
        operation?: string;
        endpoint?: string;
        scope?: string;
    },
) => void;

type UseTenantsPageOrchestrationParams = {
    controlTowerEnabled: boolean;
    workspaceMode: TenantsWorkspaceMode;
    queryClient: QueryClient;
    reportInlineError: InlineErrorReporter;
    reportError: ApiErrorReporter;
    resolveErrorScopeFromWorkspace: (workspaceMode: TenantsWorkspaceMode) => string;
};

export function useTenantsPageOrchestration({
    controlTowerEnabled,
    workspaceMode,
    queryClient,
    reportInlineError,
    reportError,
    resolveErrorScopeFromWorkspace,
}: UseTenantsPageOrchestrationParams) {
    const activeErrorScope = resolveErrorScopeFromWorkspace(controlTowerEnabled ? workspaceMode : "portfolio");

    const reportValidationError = useCallback((message: string, code = "VALIDATION_ERROR", scope?: string) => {
        const resolvedScope = scope ?? activeErrorScope;
        reportInlineError({ code, message, scope: resolvedScope });
        toast.error(message);
    }, [activeErrorScope, reportInlineError]);

    const reportProvisioningError = useCallback((error: unknown, operation: string, endpoint: string) => {
        reportError(error, {
            includeProvisioningGuidance: true,
            operation,
            endpoint,
            scope: activeErrorScope,
        });
    }, [activeErrorScope, reportError]);

    const refreshContext = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: ["console-me"] });
    }, [queryClient]);

    const refreshTenants = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: ["tenants-companies"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-clients"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branches"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-fleet-attention"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branch-changes-recent-kpi"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-client-lifecycle-audit-api"] });
    }, [queryClient]);

    const auditSensitiveAccess = useCallback(async (input: {
        branchId: string;
        field: "instance_id";
        action: TenantsSensitiveAction;
        contextScope?: string;
    }) => {
        try {
            await adminApi.auditTenantsSensitiveAccess({
                branch_id: input.branchId,
                field: input.field,
                action: input.action,
                context: input.contextScope,
            });
        } catch (error) {
            reportError(error, { scope: "changes" });
            throw error;
        }
    }, [reportError]);

    return {
        activeErrorScope,
        reportValidationError,
        reportProvisioningError,
        refreshContext,
        refreshTenants,
        auditSensitiveAccess,
    };
}
