"use client";

import { useCallback, useEffect, useState } from "react";

import {
    mergeConsoleContextScope,
    normalizeConsoleContextId,
    readConsoleContextScopeFromStorage,
    resolveConsoleContextScope,
    type ConsoleContextScope,
    type ConsoleContextSnapshot,
    writeConsoleContextScopeToStorage,
} from "@/lib/console-context-storage";

export function useConsoleContextScope(snapshot?: ConsoleContextSnapshot | null) {
    const [scope, setScope] = useState<ConsoleContextScope>(() =>
        resolveConsoleContextScope(snapshot),
    );
    const [initialized, setInitialized] = useState(false);

    useEffect(() => {
        if (!snapshot || initialized) {
            return;
        }
        setScope(resolveConsoleContextScope(snapshot));
        setInitialized(true);
    }, [initialized, snapshot]);

    const setCompanyId = useCallback((companyId?: string | null) => {
        setScope({
            companyId: normalizeConsoleContextId(companyId),
            clientId: "",
            branchId: "",
        });
    }, []);

    const setClientId = useCallback((clientId?: string | null) => {
        setScope((previous) => ({
            companyId: previous.companyId,
            clientId: normalizeConsoleContextId(clientId),
            branchId: "",
        }));
    }, []);

    const setBranchId = useCallback((branchId?: string | null) => {
        setScope((previous) => ({
            ...previous,
            branchId: normalizeConsoleContextId(branchId),
        }));
    }, []);

    const syncFromRuntime = useCallback(() => {
        setScope(resolveConsoleContextScope(snapshot, readConsoleContextScopeFromStorage()));
    }, [snapshot]);

    const updateScope = useCallback((patch: Partial<ConsoleContextScope>) => {
        setScope((previous) => mergeConsoleContextScope(previous, patch));
    }, []);

    const persistScopeToStorage = useCallback(
        (patch?: Partial<ConsoleContextScope>): ConsoleContextScope => {
            const nextScope = patch ? mergeConsoleContextScope(scope, patch) : scope;
            writeConsoleContextScopeToStorage(nextScope);
            return nextScope;
        },
        [scope],
    );

    return {
        scope,
        initialized,
        setScope,
        setCompanyId,
        setClientId,
        setBranchId,
        updateScope,
        syncFromRuntime,
        persistScopeToStorage,
    };
}
