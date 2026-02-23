import { useEffect, useMemo, useRef, useState } from "react";

export type TenantsPageFilters = {
    companyId: string | null;
    clientId: string | null;
    branchId: string | null;
};

type RouterLike = {
    replace: (href: string, options?: { scroll?: boolean }) => void;
};

type SearchParamsLike = {
    toString: () => string;
};

type UseTenantsPageFiltersParams = {
    searchParams: SearchParamsLike;
    router: RouterLike;
    initialContext: TenantsPageFilters;
    canInitialize: boolean;
};

const TENANTS_FILTER_COMPANY_PARAM = "company_id";
const TENANTS_FILTER_CLIENT_PARAM = "client_id";
const TENANTS_FILTER_BRANCH_PARAM = "branch_id";

function normalizeFilterValue(value: string | null | undefined): string | null {
    const normalized = (value ?? "").trim();
    return normalized.length > 0 ? normalized : null;
}

function hasTenantsFilterParams(searchParams: URLSearchParams): boolean {
    return (
        searchParams.has(TENANTS_FILTER_COMPANY_PARAM)
        || searchParams.has(TENANTS_FILTER_CLIENT_PARAM)
        || searchParams.has(TENANTS_FILTER_BRANCH_PARAM)
    );
}

function readTenantsFiltersFromSearchParams(searchParams: URLSearchParams): TenantsPageFilters {
    return {
        companyId: normalizeFilterValue(searchParams.get(TENANTS_FILTER_COMPANY_PARAM)),
        clientId: normalizeFilterValue(searchParams.get(TENANTS_FILTER_CLIENT_PARAM)),
        branchId: normalizeFilterValue(searchParams.get(TENANTS_FILTER_BRANCH_PARAM)),
    };
}

function writeTenantsFilterParam(params: URLSearchParams, key: string, value: string | null) {
    if (value) {
        params.set(key, value);
        return;
    }
    params.delete(key);
}

export function useTenantsPageFilters({
    searchParams,
    router,
    initialContext,
    canInitialize,
}: UseTenantsPageFiltersParams) {
    const [pageFilters, setPageFilters] = useState<TenantsPageFilters>({
        companyId: null,
        clientId: null,
        branchId: null,
    });
    const [pageFiltersInitialized, setPageFiltersInitialized] = useState(false);
    const lastPushedQueryRef = useRef<string | null>(null);

    const pageFiltersFromSearchParams = useMemo(
        () => readTenantsFiltersFromSearchParams(new URLSearchParams(searchParams.toString())),
        [searchParams],
    );
    const hasExplicitPageFilters = useMemo(
        () => hasTenantsFilterParams(new URLSearchParams(searchParams.toString())),
        [searchParams],
    );

    const pageFilterCompanyId = pageFilters.companyId;
    const pageFilterClientId = pageFilters.clientId;
    const pageFilterBranchId = pageFilters.branchId;
    const hasPageFilters = Boolean(pageFilterCompanyId || pageFilterClientId || pageFilterBranchId);

    useEffect(() => {
        if (hasExplicitPageFilters) {
            setPageFilters(pageFiltersFromSearchParams);
            setPageFiltersInitialized(true);
            return;
        }
        if (pageFiltersInitialized || !canInitialize) {
            return;
        }
        setPageFilters({
            companyId: initialContext.companyId,
            clientId: initialContext.clientId,
            branchId: initialContext.branchId,
        });
        setPageFiltersInitialized(true);
    }, [
        hasExplicitPageFilters,
        pageFiltersFromSearchParams,
        pageFiltersInitialized,
        canInitialize,
        initialContext.companyId,
        initialContext.clientId,
        initialContext.branchId,
    ]);

    useEffect(() => {
        if (!pageFiltersInitialized) {
            return;
        }
        const nextParams = new URLSearchParams(searchParams.toString());
        writeTenantsFilterParam(nextParams, TENANTS_FILTER_COMPANY_PARAM, pageFilterCompanyId);
        writeTenantsFilterParam(nextParams, TENANTS_FILTER_CLIENT_PARAM, pageFilterClientId);
        writeTenantsFilterParam(nextParams, TENANTS_FILTER_BRANCH_PARAM, pageFilterBranchId);
        const nextQuery = nextParams.toString();
        const currentQuery = searchParams.toString();
        const hasPendingUrlMismatch = lastPushedQueryRef.current !== null && lastPushedQueryRef.current !== currentQuery;
        if (nextQuery === currentQuery && !hasPendingUrlMismatch) {
            return;
        }
        lastPushedQueryRef.current = nextQuery;
        router.replace(nextQuery ? `/tenants?${nextQuery}` : "/tenants", { scroll: false });
    }, [
        pageFiltersInitialized,
        searchParams,
        router,
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
    ]);

    const setPageFilterCompany = (companyId: string | null) => {
        setPageFilters({
            companyId,
            clientId: null,
            branchId: null,
        });
    };

    const setPageFilterClient = (clientId: string | null) => {
        setPageFilters((previous) => ({
            ...previous,
            clientId,
            branchId: null,
        }));
    };

    const setPageFilterBranch = (branchId: string | null) => {
        setPageFilters((previous) => ({
            ...previous,
            branchId,
        }));
    };

    const applyScopeToPageFilters = (scope: { companyId?: string | null; clientId?: string | null; branchId?: string | null }) => {
        setPageFilters({
            companyId: normalizeFilterValue(scope.companyId ?? null),
            clientId: normalizeFilterValue(scope.clientId ?? null),
            branchId: normalizeFilterValue(scope.branchId ?? null),
        });
    };

    const clearPageFilters = () => {
        setPageFilters({
            companyId: null,
            clientId: null,
            branchId: null,
        });
    };

    return {
        pageFilters,
        setPageFilters,
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
        hasPageFilters,
        setPageFilterCompany,
        setPageFilterClient,
        setPageFilterBranch,
        applyScopeToPageFilters,
        clearPageFilters,
    };
}
