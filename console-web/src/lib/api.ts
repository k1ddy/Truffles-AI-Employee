import axios, { AxiosInstance } from "axios";

function attachIdempotencyKey(client: AxiosInstance): AxiosInstance {
    client.interceptors.request.use((config) => {
        if (config.method && ["post", "put", "patch", "delete"].includes(config.method)) {
            if (!config.headers["Idempotency-Key"]) {
                config.headers["Idempotency-Key"] = crypto.randomUUID();
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
export function createAuthenticatedApi(accessToken: string | undefined): AxiosInstance {
    return attachIdempotencyKey(axios.create({
        baseURL: "/api/proxy",
        headers: {
            "Content-Type": "application/json",
        },
    }));
}

export default api;
