import axios, { AxiosInstance } from "axios";

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

function attachIdempotencyKey(client: AxiosInstance): AxiosInstance {
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
        if (config.method && ["post", "put", "patch", "delete"].includes(config.method)) {
            if (!headers["Idempotency-Key"]) {
                headers["Idempotency-Key"] = crypto.randomUUID();
            }
        }
        return config;
    });

    return client;
}

// Use Next.js API proxy route to avoid CORS issues.
// All requests go through /api/proxy/* which forwards to the actual API server-side.
const api = attachIdempotencyKey(axios.create({
    baseURL: "/api/proxy",
    headers: {
        "Content-Type": "application/json",
    },
}));

// Factory function to create an authenticated axios instance
// Note: Auth is now handled server-side in the proxy route
export function createAuthenticatedApi(_accessToken: string | undefined): AxiosInstance {
    void _accessToken;
    return attachIdempotencyKey(axios.create({
        baseURL: "/api/proxy",
        headers: {
            "Content-Type": "application/json",
        },
    }));
}

export default api;
