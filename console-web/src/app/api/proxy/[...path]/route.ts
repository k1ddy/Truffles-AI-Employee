import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const MAX_UPSTREAM_PREVIEW = 500;

function missingApiBaseResponse() {
    return NextResponse.json(
        { error: { code: 'CONFIG_ERROR', message: 'NEXT_PUBLIC_API_URL is not set' } },
        { status: 500 }
    );
}

function buildForwardHeaders(
    sessionToken: string,
    request: NextRequest,
    extraHeaders?: Record<string, string>
): Record<string, string> {
    const companyId = request.headers.get('x-company-id');
    const clientId = request.headers.get('x-client-id');
    const branchId = request.headers.get('x-branch-id');

    return {
        Authorization: `Bearer ${sessionToken}`,
        ...(companyId ? { 'X-Company-Id': companyId } : {}),
        ...(clientId ? { 'X-Client-Id': clientId } : {}),
        ...(branchId ? { 'X-Branch-Id': branchId } : {}),
        ...(extraHeaders ?? {}),
    };
}

function isApiErrorPayload(value: unknown): value is { error: { code: string; message: string } } {
    if (!value || typeof value !== 'object') {
        return false;
    }
    const candidate = value as { error?: { code?: unknown; message?: unknown } };
    return Boolean(
        candidate.error
        && typeof candidate.error.code === 'string'
        && typeof candidate.error.message === 'string'
    );
}

async function parseUpstreamPayload(response: Response): Promise<unknown> {
    const raw = await response.text();
    if (!raw.trim()) {
        return {};
    }
    try {
        return JSON.parse(raw);
    } catch {
        const bodyPreview = raw.slice(0, MAX_UPSTREAM_PREVIEW);
        if (response.ok) {
            return {
                error: {
                    code: 'UPSTREAM_INVALID_RESPONSE',
                    message: `Upstream API returned non-JSON response (status ${response.status})`,
                    details: { body_preview: bodyPreview },
                },
            };
        }
        return {
            error: {
                code: 'UPSTREAM_ERROR',
                message: bodyPreview || `Upstream API error (status ${response.status})`,
            },
        };
    }
}

/**
 * Proxy API route to forward requests to the backend API.
 * This avoids CORS issues by making the API call server-side.
 * 
 * Usage: /api/proxy/cases -> http://api-server/console/v1/cases
 */
export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
) {
    const session = await getServerSession(authOptions);
    const { path } = await params;

    if (!session?.accessToken) {
        return NextResponse.json(
            { error: { code: 'AUTH_REQUIRED', message: 'Not authenticated' } },
            { status: 401 }
        );
    }

    if (!API_BASE_URL) {
        return missingApiBaseResponse();
    }

    const apiPath = path.join('/');
    const url = new URL(request.url);
    const queryString = url.search;
    const targetUrl = `${API_BASE_URL}/${apiPath}${queryString}`;

    try {
        const response = await fetch(targetUrl, {
            method: 'GET',
            headers: buildForwardHeaders(session.accessToken, request, {
                'Content-Type': 'application/json',
            }),
        });
        const data = await parseUpstreamPayload(response);
        if (
            response.ok
            && isApiErrorPayload(data)
            && data.error.code === 'UPSTREAM_INVALID_RESPONSE'
        ) {
            return NextResponse.json(data, { status: 502 });
        }
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json(
            {
                error: {
                    code: 'PROXY_ERROR',
                    message: 'Failed to reach API',
                    details: { target_url: targetUrl },
                },
            },
            { status: 502 }
        );
    }
}

export async function POST(
    request: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
) {
    const session = await getServerSession(authOptions);
    const { path } = await params;

    if (!session?.accessToken) {
        return NextResponse.json(
            { error: { code: 'AUTH_REQUIRED', message: 'Not authenticated' } },
            { status: 401 }
        );
    }

    if (!API_BASE_URL) {
        return missingApiBaseResponse();
    }

    const apiPath = path.join('/');
    const targetUrl = `${API_BASE_URL}/${apiPath}`;
    const contentType = request.headers.get('content-type') ?? '';
    const isMultipart = contentType.includes('multipart/form-data');
    const body = isMultipart ? await request.formData() : await request.text();

    try {
        const idempotencyKey =
            request.headers.get('Idempotency-Key') ?? request.headers.get('X-Idempotency-Key');
        const headers: Record<string, string> = buildForwardHeaders(session.accessToken, request, {
            ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
        });
        if (!isMultipart) {
            headers['Content-Type'] = 'application/json';
        }
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers,
            body,
        });
        const data = await parseUpstreamPayload(response);
        if (
            response.ok
            && isApiErrorPayload(data)
            && data.error.code === 'UPSTREAM_INVALID_RESPONSE'
        ) {
            return NextResponse.json(data, { status: 502 });
        }
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json(
            {
                error: {
                    code: 'PROXY_ERROR',
                    message: 'Failed to reach API',
                    details: { target_url: targetUrl },
                },
            },
            { status: 502 }
        );
    }
}
