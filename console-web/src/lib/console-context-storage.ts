export const CONSOLE_COMPANY_ID_STORAGE_KEY = "console:company_id";
export const CONSOLE_CLIENT_ID_STORAGE_KEY = "console:client_id";
export const CONSOLE_BRANCH_ID_STORAGE_KEY = "console:branch_id";

export type ConsoleContextScope = {
    companyId: string;
    clientId: string;
    branchId: string;
};

export type ConsoleContextSnapshot = {
    selected_company_id?: string | null;
    selected_branch_id?: string | null;
    client?: {
        id?: string | null;
        company_id?: string | null;
    } | null;
};

const EMPTY_SCOPE: ConsoleContextScope = {
    companyId: "",
    clientId: "",
    branchId: "",
};

export function normalizeConsoleContextId(value?: string | null): string {
    return (value ?? "").trim();
}

function readLocalStorageValue(key: string): string {
    if (typeof window === "undefined") {
        return "";
    }
    return normalizeConsoleContextId(window.localStorage.getItem(key));
}

function writeLocalStorageValue(key: string, value: string) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}

export function readConsoleContextScopeFromStorage(): ConsoleContextScope {
    return {
        companyId: readLocalStorageValue(CONSOLE_COMPANY_ID_STORAGE_KEY),
        clientId: readLocalStorageValue(CONSOLE_CLIENT_ID_STORAGE_KEY),
        branchId: readLocalStorageValue(CONSOLE_BRANCH_ID_STORAGE_KEY),
    };
}

export function writeConsoleContextScopeToStorage(scope: ConsoleContextScope) {
    writeLocalStorageValue(CONSOLE_COMPANY_ID_STORAGE_KEY, normalizeConsoleContextId(scope.companyId));
    writeLocalStorageValue(CONSOLE_CLIENT_ID_STORAGE_KEY, normalizeConsoleContextId(scope.clientId));
    writeLocalStorageValue(CONSOLE_BRANCH_ID_STORAGE_KEY, normalizeConsoleContextId(scope.branchId));
}

export function normalizeConsoleContextScope(
    scope: Partial<ConsoleContextScope>,
): ConsoleContextScope {
    return {
        companyId: normalizeConsoleContextId(scope.companyId),
        clientId: normalizeConsoleContextId(scope.clientId),
        branchId: normalizeConsoleContextId(scope.branchId),
    };
}

export function mergeConsoleContextScope(
    base: ConsoleContextScope,
    patch: Partial<ConsoleContextScope>,
): ConsoleContextScope {
    return {
        companyId: patch.companyId !== undefined ? normalizeConsoleContextId(patch.companyId) : base.companyId,
        clientId: patch.clientId !== undefined ? normalizeConsoleContextId(patch.clientId) : base.clientId,
        branchId: patch.branchId !== undefined ? normalizeConsoleContextId(patch.branchId) : base.branchId,
    };
}

export function clearConsoleContextScope() {
    writeConsoleContextScopeToStorage(EMPTY_SCOPE);
}

export function setConsoleContextScope(scope: Partial<ConsoleContextScope>): ConsoleContextScope {
    const normalized = normalizeConsoleContextScope(scope);
    writeConsoleContextScopeToStorage(normalized);
    return normalized;
}

export function setConsoleCompanyContext(companyId?: string | null): ConsoleContextScope {
    return setConsoleContextScope({
        companyId: normalizeConsoleContextId(companyId),
        clientId: "",
        branchId: "",
    });
}

export function setConsoleClientContext(
    clientId?: string | null,
    companyId?: string | null,
): ConsoleContextScope {
    const stored = readConsoleContextScopeFromStorage();
    return setConsoleContextScope({
        companyId: normalizeConsoleContextId(companyId) || stored.companyId,
        clientId: normalizeConsoleContextId(clientId),
        branchId: "",
    });
}

export function setConsoleBranchContext(branchId?: string | null): ConsoleContextScope {
    const stored = readConsoleContextScopeFromStorage();
    return setConsoleContextScope({
        companyId: stored.companyId,
        clientId: stored.clientId,
        branchId: normalizeConsoleContextId(branchId),
    });
}

export function resolveConsoleContextScope(
    snapshot?: ConsoleContextSnapshot | null,
    fallback?: ConsoleContextScope,
): ConsoleContextScope {
    const stored = fallback ?? readConsoleContextScopeFromStorage();
    return {
        companyId: normalizeConsoleContextId(
            snapshot?.selected_company_id ?? snapshot?.client?.company_id ?? stored.companyId,
        ),
        clientId: normalizeConsoleContextId(snapshot?.client?.id ?? stored.clientId),
        branchId: normalizeConsoleContextId(snapshot?.selected_branch_id ?? stored.branchId),
    };
}
