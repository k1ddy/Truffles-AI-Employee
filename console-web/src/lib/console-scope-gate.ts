import type { QueryClient } from "@tanstack/react-query";

import { writeConsoleContextScopeToStorage } from "@/lib/console-context-storage";

export type ConsoleScopeQueryKey = readonly unknown[];

function uniqueQueryKeys(keys: ConsoleScopeQueryKey[]): ConsoleScopeQueryKey[] {
    const seen = new Set<string>();
    return keys.filter((key) => {
        const fingerprint = JSON.stringify(key);
        if (seen.has(fingerprint)) {
            return false;
        }
        seen.add(fingerprint);
        return true;
    });
}

async function invalidateQueryKeys(queryClient: QueryClient, keys: ConsoleScopeQueryKey[]): Promise<void> {
    await Promise.all(uniqueQueryKeys(keys).map((queryKey) => queryClient.invalidateQueries({ queryKey, exact: true })));
}

async function refetchQueryKeys(queryClient: QueryClient, keys: ConsoleScopeQueryKey[]): Promise<void> {
    await Promise.all(uniqueQueryKeys(keys).map((queryKey) => queryClient.refetchQueries({ queryKey, exact: true })));
}

export async function applyConsoleScopeContext({
    queryClient,
    companyId,
    clientId,
    branchId,
    invalidateKeys = [],
    refetchKeys = [],
}: {
    queryClient: QueryClient;
    companyId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
    invalidateKeys?: ConsoleScopeQueryKey[];
    refetchKeys?: ConsoleScopeQueryKey[];
}): Promise<void> {
    writeConsoleContextScopeToStorage({
        companyId: companyId ?? "",
        clientId: clientId ?? "",
        branchId: branchId ?? "",
    });

    await invalidateQueryKeys(queryClient, [["console-me"], ...invalidateKeys]);
    await refetchQueryKeys(queryClient, [["console-me"], ...refetchKeys]);
}
