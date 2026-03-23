import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";

const ALLOWED_EVENT_TYPES = new Set([
    "selection_gate_shown",
    "selection_gate_confirmed",
    "auth_session_expired_signout",
    "scope_cleared_explicit_logout",
]);
const ALLOWED_SURFACES = new Set(["console_shell", "login_button"]);
const ALLOWED_GATE_KINDS = new Set(["company", "client", "branch", "none"]);

interface ConsoleClientScopePresence {
    company_id_present: boolean;
    client_id_present: boolean;
    branch_id_present: boolean;
}

interface ConsoleClientEventEnvelope {
    event_id: string;
    emitted_at: string;
    event_type: string;
    surface: string;
    gate_kind: string;
    reason_code: string | null;
    session_error: string | null;
    api_error_code: string | null;
    company_selection_required: boolean;
    selection_required: boolean;
    branch_selection_required: boolean;
    path: string;
    scope_presence: ConsoleClientScopePresence;
}

function normalizeOptionalString(value: unknown, maxLength: number): string | null {
    if (typeof value !== "string") {
        return null;
    }
    const normalized = value.trim();
    if (!normalized) {
        return null;
    }
    return normalized.slice(0, maxLength);
}

function parseBoolean(value: unknown): boolean {
    return value === true;
}

function parseScopePresence(value: unknown): ConsoleClientScopePresence | null {
    if (!value || typeof value !== "object") {
        return null;
    }
    const payload = value as Partial<ConsoleClientScopePresence>;
    return {
        company_id_present: payload.company_id_present === true,
        client_id_present: payload.client_id_present === true,
        branch_id_present: payload.branch_id_present === true,
    };
}

async function parseEventEnvelope(request: NextRequest): Promise<ConsoleClientEventEnvelope | null> {
    let body: unknown;
    try {
        body = await request.json();
    } catch {
        return null;
    }
    if (!body || typeof body !== "object") {
        return null;
    }

    const payload = body as Record<string, unknown>;
    const eventType = normalizeOptionalString(payload.event_type, 80);
    const surface = normalizeOptionalString(payload.surface, 80);
    const gateKind = normalizeOptionalString(payload.gate_kind, 32) ?? "none";
    const eventId = normalizeOptionalString(payload.event_id, 120);
    const emittedAt = normalizeOptionalString(payload.emitted_at, 80);
    const path = normalizeOptionalString(payload.path, 160);
    const scopePresence = parseScopePresence(payload.scope_presence);

    if (
        !eventId
        || !emittedAt
        || !eventType
        || !ALLOWED_EVENT_TYPES.has(eventType)
        || !surface
        || !ALLOWED_SURFACES.has(surface)
        || !ALLOWED_GATE_KINDS.has(gateKind)
        || !path
        || !scopePresence
    ) {
        return null;
    }

    return {
        event_id: eventId,
        emitted_at: emittedAt,
        event_type: eventType,
        surface,
        gate_kind: gateKind,
        reason_code: normalizeOptionalString(payload.reason_code, 80),
        session_error: normalizeOptionalString(payload.session_error, 120),
        api_error_code: normalizeOptionalString(payload.api_error_code, 120),
        company_selection_required: parseBoolean(payload.company_selection_required),
        selection_required: parseBoolean(payload.selection_required),
        branch_selection_required: parseBoolean(payload.branch_selection_required),
        path,
        scope_presence: scopePresence,
    };
}

export async function POST(request: NextRequest) {
    const event = await parseEventEnvelope(request);
    if (!event) {
        return NextResponse.json(
            {
                error: {
                    code: "INVALID_CONSOLE_CLIENT_EVENT",
                    message: "Invalid console client event payload",
                },
            },
            { status: 400 },
        );
    }

    const session = await getServerSession(authOptions);
    const userAgent = normalizeOptionalString(request.headers.get("user-agent"), 240);
    const referer = normalizeOptionalString(request.headers.get("referer"), 240);
    const forwardedFor = normalizeOptionalString(request.headers.get("x-forwarded-for"), 120);

    console.info(
        JSON.stringify({
            message: "console_client_event",
            received_at: new Date().toISOString(),
            event,
            session: {
                has_session: Boolean(session),
                has_access_token: Boolean(session?.accessToken),
                session_error: normalizeOptionalString(session?.error, 120),
                user_email_present: Boolean(session?.user?.email),
                user_name_present: Boolean(session?.user?.name),
            },
            request: {
                user_agent: userAgent,
                referer,
                forwarded_for: forwardedFor,
            },
        }),
    );

    return NextResponse.json({ success: true }, { status: 202 });
}
