import axios, { AxiosInstance } from "axios";

// Use Next.js API proxy route to avoid CORS issues.
// All requests go through /api/proxy/* which forwards to the actual API server-side.
const api = axios.create({
    baseURL: "/api/proxy",
    headers: {
        "Content-Type": "application/json",
    },
});

// Factory function to create an authenticated axios instance
// Note: Auth is now handled server-side in the proxy route
export function createAuthenticatedApi(accessToken: string | undefined): AxiosInstance {
    return axios.create({
        baseURL: "/api/proxy",
        headers: {
            "Content-Type": "application/json",
        },
    });
}

export default api;
