"use client";

import { useMemo } from "react";
import { useSession } from "next-auth/react";
import { createAuthenticatedApi } from "@/lib/api";

// Extend Session type to include accessToken
interface ExtendedSession {
    accessToken?: string;
    user?: {
        name?: string | null;
        email?: string | null;
        image?: string | null;
    };
}

/**
 * Hook to get an authenticated axios instance using the current session token.
 */
export function useAuthenticatedApi() {
    const { data: session } = useSession();

    const authenticatedApi = useMemo(() => {
        const extendedSession = session as ExtendedSession | null;
        const token = extendedSession?.accessToken;
        return createAuthenticatedApi(token);
    }, [session]);

    return authenticatedApi;
}

/**
 * Returns true if user has a valid access token
 */
export function useHasAuth() {
    const { data: session } = useSession();
    const extendedSession = session as ExtendedSession | null;
    return !!extendedSession?.accessToken;
}
