import { NextResponse } from 'next/server';

/**
 * E2E Health Check — проверяет всю цепочку Frontend → API → DB
 * 
 * Endpoint: GET /api/health/full
 * 
 * Response:
 * {
 *   "status": "healthy" | "unhealthy",
 *   "timestamp": "...",
 *   "components": {
 *     "frontend": "ok",
 *     "api": { "status": "ok" | "unhealthy", "port": 8000, ... },
 *     "database": "connected" | "error",
 *     "qdrant": "reachable" | "error"
 *   }
 * }
 */

const API_URL = (() => {
    const envUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // Strip /console/v1 or any path suffix to get base API URL
    try {
        const url = new URL(envUrl);
        return `${url.protocol}//${url.host}`;
    } catch {
        return 'http://localhost:8000';
    }
})();

interface HealthResponse {
    status: 'healthy' | 'unhealthy';
    timestamp: string;
    latency_ms: number;
    components: {
        frontend: string;
        api: {
            status: string;
            port: number;
            version?: string;
            error?: string;
        };
        database: string;
        qdrant: string;
        outbox?: {
            pending: number;
            failed: number;
            failed_24h: number;
            failed_total: number;
            status: string;
        };
    };
}

export async function GET() {
    const startTime = Date.now();
    const response: HealthResponse = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        latency_ms: 0,
        components: {
            frontend: 'ok',
            api: {
                status: 'unknown',
                port: 8000,
            },
            database: 'unknown',
            qdrant: 'unknown',
        },
    };

    try {
        // Check API health endpoint
        const apiController = new AbortController();
        const apiTimeout = setTimeout(() => apiController.abort(), 5000);

        const apiResponse = await fetch(`${API_URL}/admin/health/check`, {
            signal: apiController.signal,
            headers: {
                'Accept': 'application/json',
            },
        });
        clearTimeout(apiTimeout);

        if (!apiResponse.ok) {
            response.status = 'unhealthy';
            response.components.api = {
                status: 'unhealthy',
                port: 8000,
                error: `HTTP ${apiResponse.status}`,
            };
        } else {
            const apiHealth = await apiResponse.json();

            // Parse API health response
            response.components.api = {
                status: apiHealth.status || 'ok',
                port: 8000,
            };

            // Database status
            if (apiHealth.checks?.database) {
                response.components.database = apiHealth.checks.database.status === 'healthy'
                    ? 'connected'
                    : 'error';
                if (apiHealth.checks.database.status !== 'healthy') {
                    response.status = 'unhealthy';
                }
            }

            // Qdrant status
            if (apiHealth.checks?.qdrant) {
                response.components.qdrant = apiHealth.checks.qdrant.status === 'healthy'
                    ? 'reachable'
                    : 'error';
            }

            // Outbox status
            if (apiHealth.checks?.outbox) {
                const pending = Number(apiHealth.checks.outbox.pending || 0);
                const failed24h = Number(
                    apiHealth.checks.outbox.failed_24h
                    ?? apiHealth.checks.outbox.failed
                    ?? 0,
                );
                const failedTotal = Number(
                    apiHealth.checks.outbox.failed_total
                    ?? apiHealth.checks.outbox.failed
                    ?? failed24h,
                );
                const outboxStatus = String(apiHealth.checks.outbox.status || 'unknown');
                response.components.outbox = {
                    pending,
                    failed: failed24h,
                    failed_24h: failed24h,
                    failed_total: failedTotal,
                    status: outboxStatus,
                };
                if (outboxStatus === 'critical' || outboxStatus === 'error') {
                    response.status = 'unhealthy';
                }
            }

            // Overall API status
            if (apiHealth.status !== 'healthy') {
                response.status = 'unhealthy';
            }
        }

        // Try to get version info
        try {
            const versionController = new AbortController();
            const versionTimeout = setTimeout(() => versionController.abort(), 2000);

            const versionResponse = await fetch(`${API_URL}/admin/version`, {
                signal: versionController.signal,
            });
            clearTimeout(versionTimeout);

            if (versionResponse.ok) {
                const version = await versionResponse.json();
                response.components.api.version = version.git_commit?.substring(0, 8) || version.version;
            }
        } catch {
            // Version endpoint is optional
        }

    } catch (error) {
        response.status = 'unhealthy';
        response.components.api = {
            status: 'unreachable',
            port: 8000,
            error: error instanceof Error ? error.message : 'Connection failed',
        };
        response.components.database = 'unknown';
        response.components.qdrant = 'unknown';
    }

    response.latency_ms = Date.now() - startTime;

    return NextResponse.json(response, {
        status: response.status === 'healthy' ? 200 : 503,
        headers: {
            'Cache-Control': 'no-store, max-age=0',
        },
    });
}
