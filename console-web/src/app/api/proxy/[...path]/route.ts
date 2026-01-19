import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://192.168.5.27:8001/console/v1';

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

    const apiPath = path.join('/');
    const url = new URL(request.url);
    const queryString = url.search;
    const targetUrl = `${API_BASE_URL}/${apiPath}${queryString}`;

    try {
        const response = await fetch(targetUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${session.accessToken}`,
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json(
            { error: { code: 'PROXY_ERROR', message: 'Failed to reach API' } },
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

    const apiPath = path.join('/');
    const targetUrl = `${API_BASE_URL}/${apiPath}`;
    const body = await request.text();

    try {
        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${session.accessToken}`,
                'Content-Type': 'application/json',
            },
            body,
        });

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('Proxy error:', error);
        return NextResponse.json(
            { error: { code: 'PROXY_ERROR', message: 'Failed to reach API' } },
            { status: 502 }
        );
    }
}
