import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export async function GET(request: NextRequest) {
    const origin = request.nextUrl.origin;
    const code = request.nextUrl.searchParams.get('code');
    const state = request.nextUrl.searchParams.get('state');

    if (!API_BASE_URL || !code || !state) {
        return NextResponse.redirect(new URL('/settings?google_error=true', origin));
    }

    const targetUrl = new URL(`${API_BASE_URL}/calendar/google/callback`);
    targetUrl.searchParams.set('code', code);
    targetUrl.searchParams.set('state', state);

    try {
        const response = await fetch(targetUrl.toString(), {
            method: 'GET',
            redirect: 'manual',
        });

        const location = response.headers.get('location');
        if (location) {
            const resolved = new URL(location, origin);
            return NextResponse.redirect(new URL(`${resolved.pathname}${resolved.search}`, origin));
        }

        if (!response.ok) {
            return NextResponse.redirect(new URL('/settings?google_error=true', origin));
        }

        return NextResponse.redirect(new URL('/settings?google_connected=true', origin));
    } catch {
        return NextResponse.redirect(new URL('/settings?google_error=true', origin));
    }
}
