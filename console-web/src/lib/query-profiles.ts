export const QUERY_PROFILE_CONTEXT = {
    staleTime: 15000,
    refetchOnWindowFocus: false,
} as const;

export const QUERY_PROFILE_DASHBOARD = {
    staleTime: 10000,
    refetchOnWindowFocus: false,
} as const;

export function keepPreviousData<T>(previousData: T | undefined): T | undefined {
    return previousData;
}
