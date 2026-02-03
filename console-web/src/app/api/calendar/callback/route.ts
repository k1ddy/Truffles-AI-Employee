import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

function resolveOrigin(request: NextRequest) {
    const forwardedHost = request.headers.get('x-forwarded-host') ?? request.headers.get('host');
    const forwardedProto =
        request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '');
    let origin = forwardedHost ? `${forwardedProto}://${forwardedHost}` : request.nextUrl.origin;
    if (origin.includes('0.0.0.0') || origin.includes('[::]')) {
        const fallback = process.env.NEXTAUTH_URL ?? process.env.NEXT_PUBLIC_CONSOLE_URL;
        if (fallback) {
            try {
                origin = new URL(fallback).origin;
            } catch {
                origin = origin.replace('0.0.0.0', 'localhost').replace('[::]', 'localhost');
            }
        } else {
            origin = origin.replace('0.0.0.0', 'localhost').replace('[::]', 'localhost');
        }
    }
    return origin;
}

export async function GET(request: NextRequest) {
    const origin = resolveOrigin(request);
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
