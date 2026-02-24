"use client";

import { useCallback } from "react";
import {
    readConsoleContextScopeFromStorage,
    setConsoleContextScope,
} from "@/lib/console-context-storage";

type ScopeValue = {
    companyId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
};

type UseTenantsActionsParams = {
    clientCompanyIdById: Map<string, string>;
    branchClientIdById: Map<string, string>;
    branchCompanyIdById: Map<string, string>;
    pageFilterCompanyId: string | null;
    pageFilterClientId: string | null;
    applyScopeToPageFilters: (scope: ScopeValue) => void;
    refreshContext: () => void;
    reportValidationError: (message: string, code?: string, scope?: string) => void;
};

function normalizeOptionalId(value: string | null | undefined): string | null {
    const normalized = value?.trim();
    return normalized ? normalized : null;
}

export function useTenantsActions({
    clientCompanyIdById,
    branchClientIdById,
    branchCompanyIdById,
    pageFilterCompanyId,
    pageFilterClientId,
    applyScopeToPageFilters,
    refreshContext,
    reportValidationError,
}: UseTenantsActionsParams) {
    const completeContextScope = useCallback((scope: ScopeValue) => {
        const normalizedBranchId = normalizeOptionalId(scope.branchId);
        let normalizedClientId = normalizeOptionalId(scope.clientId);
        let normalizedCompanyId = normalizeOptionalId(scope.companyId);
        if (normalizedBranchId) {
            const branchClientId = branchClientIdById.get(normalizedBranchId);
            if (!normalizedClientId && branchClientId) {
                normalizedClientId = branchClientId;
            }
            if (!normalizedCompanyId) {
                const branchCompanyId = branchCompanyIdById.get(normalizedBranchId);
                if (branchCompanyId) {
                    normalizedCompanyId = branchCompanyId;
                }
            }
        }
        if (!normalizedCompanyId && normalizedClientId) {
            normalizedCompanyId = clientCompanyIdById.get(normalizedClientId) ?? null;
        }
        return {
            companyId: normalizedCompanyId,
            clientId: normalizedClientId,
            branchId: normalizedBranchId,
        };
    }, [branchClientIdById, branchCompanyIdById, clientCompanyIdById]);

    const validateScopeForBranchActions = useCallback((
        scope: ScopeValue,
        actionLabel: string,
    ) => {
        const normalized = completeContextScope(scope);
        if (normalized.branchId && (!normalized.clientId || !normalized.companyId)) {
            reportValidationError(
                `Нельзя выполнить "${actionLabel}": для филиала требуется связка company + client.`,
                "TENANTS_SCOPE_INVALID",
                "filters",
            );
            return null;
        }
        return normalized;
    }, [completeContextScope, reportValidationError]);

    const writeContextScope = useCallback((scope: ScopeValue) => {
        const normalized = completeContextScope(scope);
        setConsoleContextScope({
            companyId: normalized.companyId ?? "",
            clientId: normalized.clientId ?? "",
            branchId: normalized.branchId ?? "",
        });
        refreshContext();
        return normalized;
    }, [completeContextScope, refreshContext]);

    const setCompanyContext = useCallback((companyId?: string | null) => {
        writeContextScope({
            companyId,
            clientId: null,
            branchId: null,
        });
    }, [writeContextScope]);

    const setClientContext = useCallback((clientId?: string | null, companyId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: companyId ?? storedScope.companyId,
            clientId,
            branchId: null,
        });
    }, [writeContextScope]);

    const setBranchContext = useCallback((branchId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: storedScope.companyId,
            clientId: storedScope.clientId,
            branchId,
        });
    }, [writeContextScope]);

    const clearContextLens = useCallback(() => {
        setCompanyContext(null);
    }, [setCompanyContext]);

    const setClientContextAndPageFilters = useCallback((clientId?: string | null, companyId?: string | null) => {
        const nextScope = writeContextScope({
            companyId,
            clientId,
            branchId: null,
        });
        applyScopeToPageFilters(nextScope);
    }, [applyScopeToPageFilters, writeContextScope]);

    const setBranchContextAndPageFilters = useCallback((
        input?: string | ScopeValue | null,
    ) => {
        const branchPatch = typeof input === "string" || input == null ? { branchId: input ?? null } : input;
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScopeCandidate = validateScopeForBranchActions(
            {
                companyId: branchPatch.companyId ?? pageFilterCompanyId ?? storedScope.companyId,
                clientId: branchPatch.clientId ?? pageFilterClientId ?? storedScope.clientId,
                branchId: branchPatch.branchId ?? null,
            },
            "В контекст филиала",
        );
        if (!nextScopeCandidate) {
            return;
        }
        const nextScope = writeContextScope({
            companyId: nextScopeCandidate.companyId,
            clientId: nextScopeCandidate.clientId,
            branchId: nextScopeCandidate.branchId,
        });
        applyScopeToPageFilters(nextScope);
    }, [
        applyScopeToPageFilters,
        pageFilterCompanyId,
        pageFilterClientId,
        validateScopeForBranchActions,
        writeContextScope,
    ]);

    const applyContextToPageFilters = useCallback(() => {
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScope = validateScopeForBranchActions(storedScope, "Взять из рабочего контура");
        if (!nextScope) {
            return;
        }
        applyScopeToPageFilters(nextScope);
        if (
            (nextScope.companyId ?? "") !== storedScope.companyId
            || (nextScope.clientId ?? "") !== storedScope.clientId
            || (nextScope.branchId ?? "") !== storedScope.branchId
        ) {
            setConsoleContextScope({
                companyId: nextScope.companyId ?? "",
                clientId: nextScope.clientId ?? "",
                branchId: nextScope.branchId ?? "",
            });
            refreshContext();
        }
    }, [applyScopeToPageFilters, refreshContext, validateScopeForBranchActions]);

    return {
        setCompanyContext,
        setClientContext,
        setBranchContext,
        clearContextLens,
        setClientContextAndPageFilters,
        setBranchContextAndPageFilters,
        applyContextToPageFilters,
    };
}
